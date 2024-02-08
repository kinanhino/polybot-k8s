import boto3
import telebot
from loguru import logger
import os
import time
from telebot.types import InputFile
from botocore.exceptions import ClientError
from collections import Counter
import json
import emoji
from emojies import emojies

class Bot:

    def __init__(self, token, telegram_chat_url):
        region_name = os.getenv('REGION')
        self.session = boto3.Session(region_name=region_name)
        # create a new instance of the TeleBot class.
        # all communication with Telegram servers are done using self.telegram_bot_client
        self.telegram_bot_client = telebot.TeleBot(token)

        # remove any existing webhooks configured in Telegram servers
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)

        # set the webhook URL
        self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/', timeout=60, certificate=open(
            'server.crt', 'r'))

        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text)

    def send_animation(self, chat_id, gif):
        return self.telegram_bot_client.send_animation(chat_id=chat_id, animation=gif)

    def send_video(self, chat_id, video):
        return self.telegram_bot_client.send_video(chat_id=chat_id, video=video)
    
    def delete_message(self, chat_id, msg_id):
        self.telegram_bot_client.delete_message(chat_id=chat_id, message_id=msg_id)

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def download_user_photo(self, msg):
        """
        Downloads the photos that sent to the Bot to `photos` directory (should be existed)
        :return:
        """
        if not self.is_current_msg_photo(msg):
            raise RuntimeError(f'Message content of type \'photo\' expected')

        file_info = self.telegram_bot_client.get_file(msg['photo'][-1]['file_id'])
        data = self.telegram_bot_client.download_file(file_info.file_path)
        folder_name = file_info.file_path.split('/')[0]

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        with open(file_info.file_path, 'wb') as photo:
            photo.write(data)

        return file_info.file_path

    def send_photo(self, chat_id, img_path):
        if not os.path.exists(img_path):
            raise RuntimeError("Image path doesn't exist")

        self.telegram_bot_client.send_photo(
            chat_id,
            InputFile(img_path)
        )

    def handle_message(self, msg):
        """Bot Main message handler"""
        logger.info(f'Incoming message: {msg}')
        self.send_text(msg['chat']['id'], f'Your original message: {msg["text"]}')


class ObjectDetectionBot(Bot):

    def handle_dynamo_message(self, dynamo_message):
        logger.info("handling dynamo..")
        class_names = [label['M']['class']['S'] for label in dynamo_message['labels']]
        class_counts = Counter(class_names)
        json_string = json.dumps(class_counts)
        counts_dict = json.loads(json_string)
        return self.get_formatted_string(counts_dict)

    def get_formatted_string(self,objects_dict):
        formatted_string = f'Objects Detected:\n'
        for key,value in objects_dict.items():
            emojie = emoji.emojize(f'{emojies[key]}') if key in emojies.keys() else emoji.emojize(':full_moon_face:')
            formatted_string += f'{key}{emojie}: {value}\n'
        return formatted_string

    def get_item_by_prediction_id(self, prediction_id):
        dynamodb_client = self.session.client('dynamodb')
        dynamo_tbl = os.getenv('DYNAMO_TBL')
        try:
            response = dynamodb_client.get_item(
                TableName=dynamo_tbl,
                Key={'prediction_id': {'S': prediction_id}}
             )
            pred_summary = response.get('Item', None)
            if pred_summary:
                pred_summary = {k: list(v.values())[0] for k, v in pred_summary.items()}
                return pred_summary
            else:
                print(f"No item found with prediction_id: {prediction_id}")
                return None
        except Exception as e:
            print(f"Error fetching item from DynamoDB: {e}")
            return None

    def send_message_to_sqs(self, msg_body):
        logger.info("send to sqs..")
        sqs_client = self.session.client('sqs')
        queue_url = os.getenv('QUEUE_URL')
        try:
            response = sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=msg_body
            )
            logger.info(response)
        except ClientError as e:
            print(f"An error occurred: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def upload_to_s3(self, file_path, bucket_name, object_name=None):
        logger.info("upload to s3...")
        if object_name is None:
            object_name = os.path.basename(file_path)

        s3_client = self.session.client('s3')
        try:
            s3_client.upload_file(file_path, bucket_name, object_name)
        except ClientError as e:
            logger.error(e)
            return False
        return True

    def download_from_s3(self, bucket_name, object_name, local_path):
        logger.info("download from s3..")
        s3_client = self.session.client('s3')
        try:
            s3_client.download_file(bucket_name, object_name, local_path)
        except ClientError as e:
            logger.error(e)
            return False
        return True

    def send_photo(self, chat_id, img_path):
        if not os.path.exists(img_path):
            raise RuntimeError("Image path doesn't exist")

        self.telegram_bot_client.send_photo(
            chat_id,
            InputFile(img_path)
        )

    def handle_message(self, msg):
        
        logger.info(f'Incoming message: {msg}')
        if self.is_current_msg_photo(msg):
            with open('loading.mp4', 'rb') as gif:
                # send message to the Telegram end-user
                loading_msg = self.send_video(chat_id=msg['chat']['id'], video=gif)
        
            photo_path = self.download_user_photo(msg)
            bucket_name = os.environ['BUCKET_NAME']
            # upload the photo to S3
            self.upload_to_s3(photo_path, bucket_name, photo_path)
            # send a job to the SQS queue
            self.send_message_to_sqs(f"{photo_path},{msg['chat']['id']},{loading_msg.message_id}")

        elif "text" in msg:
            self.send_text(msg['chat']['id'], 'Hint:Im at linkedin and its sooo funn!!')
        else:
            self.send_text(msg['chat']['id'], 'Unsupported message type. Please send Photos')