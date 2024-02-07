import flask
from flask import request
import os
from bot import ObjectDetectionBot, Bot
import boto3
from botocore.exceptions import ClientError
from loguru import logger
import json

def get_secret():

    secret_name = "kinan-aws-key"
    region_name = os.getenv('REGION')
    # Create a Secrets Manager client
    session = boto3.session.Session(region_name=region_name)
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        secret = get_secret_value_response['SecretString']
        secret_dict = json.loads(secret)

        tele_token = secret_dict["TELEGRAM_TOKEN"]

    except ClientError as e:
        logger.error(e)
        return False
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON: {e}")
        return False
    except KeyError:
        logger.error("Key 'TELEGRAM_TOKEN' not found in the JSON data")
        return False
    
    return tele_token


app = flask.Flask(__name__)

# load TELEGRAM_TOKEN value from Secret Manager
TELEGRAM_TOKEN = get_secret()

TELEGRAM_APP_URL = os.environ['TELEGRAM_APP_URL']

s3_bucket = os.environ['BUCKET_NAME']
@app.route('/', methods=['GET'])
def index():
    return 'Ok'

@app.route('/team3polybot/', methods=['GET'])
def index2():
    return 'hello from team3poly!'

@app.route(f'/team3polybot/{TELEGRAM_TOKEN}/', methods=['POST'])
def webhook():
    req = request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'

@app.route(f'/noresults/', methods=['GET'])
def noresults():
    prediction_id = request.args.get('predictionId')

    # use the prediction_id to retrieve results from DynamoDB and send to the end-user
    prediction_summary = bot.get_item_by_prediction_id(prediction_id)
    chat_id = prediction_summary['chat_id']
    gif_message_id = prediction_summary['gif_message_id']
    bot.delete_message(chat_id, gif_message_id)
    logger.info(f'chat id: {chat_id}')
    text_results = "No Objects Detected.\nTry sending detailed photo!"
    bot.send_text(chat_id, text_results)
    return 'Ok'

@app.route(f'/results/', methods=['GET'])
def results():
    prediction_id = request.args.get('predictionId')

    # use the prediction_id to retrieve results from DynamoDB and send to the end-user
    prediction_summary = bot.get_item_by_prediction_id(prediction_id)
    logger.info(f'prediction_summary in results: {prediction_summary}')
    logger.info(f'type: {type(prediction_summary)}')
    chat_id = prediction_summary['chat_id']
    photo_path = prediction_summary['original_img_path']
    gif_message_id = prediction_summary['gif_message_id']
    bot.delete_message(chat_id, gif_message_id)
    logger.info(f'chat id: {chat_id}')
    text_results = bot.handle_dynamo_message(prediction_summary)
    s3_path = "predicted/" + os.path.basename(photo_path)
    bot.download_from_s3(s3_bucket, s3_path, photo_path)
    bot.send_photo(chat_id, photo_path)
    bot.send_text(chat_id, text_results)
    return 'Ok'


@app.route(f'/loadTest/', methods=['POST'])
def load_test():
    req = request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'

@app.route('/health')
def health_check():
    return 'OK', 200


if __name__ == "__main__":

    logger.info(f"token: {TELEGRAM_TOKEN}, url: {TELEGRAM_APP_URL}")
    bot = ObjectDetectionBot(TELEGRAM_TOKEN, TELEGRAM_APP_URL)

    app.run(host='0.0.0.0', port=8443)
