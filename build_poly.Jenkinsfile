pipeline {
    agent any
    environment {
        ECR_REGISTRY = "933060838752.dkr.ecr.eu-central-1.amazonaws.com"
        TIMESTAMP = new Date().format('yyyyMMdd_HHmmss')
        IMAGE_TAG = "${env.BUILD_NUMBER}_${TIMESTAMP}"
        ECR_REGION = "eu-central-1"
        AWS_CREDENTIALS_ID = 'AWS credentials'
        KUBE_CONFIG_CRED = 'KUBE_CONFIG_CRED'
        CLUSTER_NAME = "k8s-main"
        CLUSTER_REGION = "us-east-1"
    }
    stages {
        stage('Login to AWS ECR') {
            steps {
                script {
                    withCredentials([aws(credentialsId: AWS_CREDENTIALS_ID, accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY')]) {
                        sh 'aws ecr get-login-password --region ${ECR_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}'
                    }
                }
            }
        }
        stage('Build and Push') {
            steps {
                script {
                    echo "IMAGE_TAG: ${IMAGE_TAG}"
                    dockerImage = docker.build("${ECR_REGISTRY}/team3-polybot-ecr:${IMAGE_TAG}") // , "--no-cache .")
                    dockerImage.push()
                }
            }
        }
        stage('Deploy') {
            steps {
                script {
                    withCredentials([aws(credentialsId: AWS_CREDENTIALS_ID, accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY')]) {
                        sh 'aws eks update-kubeconfig --region ${CLUSTER_REGION} --name ${CLUSTER_NAME}'
                        withCredentials([file(credentialsId: 'KUBE_CONFIG_CRED', variable: 'KUBECONFIG')]) {
                            // sh 'aws eks --region us-east-1 update-kubeconfig --name k8s-main'
                            // sh 'kubectl config set-context --current --namespace=lanabot-dev-ns'
                            sh "sed -i 's|image: .*|image: ${ECR_REGISTRY}/team3-polybot-ecr:${IMAGE_TAG}|' polybot-deployment.yaml"
                            // sh "cat lana-bot-deployment.yaml"
                            sh 'kubectl apply -f polybot-deployment.yaml' //--validate=false'
                        }
                    }
                    // withCredentials([file(credentialsId: 'kubeconfig-credentials', variable: 'KUBECONFIG_FILE')]) {
                    //    sh "aws eks update-kubeconfig --region us-east-1 --name k8s-main --kubeconfig \$KUBECONFIG_FILE"
                    // }
                }
            }
        }
    }
    post {
        always {
            sh 'docker rmi $(docker images -q) -f || true'
        }
    }
}








