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
                    dockerImage = docker.build("${ECR_REGISTRY}/team3-polybot-ecr:${IMAGE_TAG}")
                    dockerImage.push()
                }
            }
        }
        stage('Update Deployment and Push to GitHub') {
            steps {
                script {
                    withCredentials([usernamePassword(credentialsId: 'GIT_CREDENTIALS_ID', passwordVariable: 'GIT_PASSWORD', usernameVariable: 'GIT_USERNAME')]) {
                        def repoDir = 'polybot-k8s'

                        if (!fileExists('${repoDir}/.git')) {
                            sh 'git clone --branch argo-releases https://github.com/kinanhino/polybot-k8s.git .'
                        } else {
                            dir(repoDir) {
                                sh 'git reset --hard'
                                sh 'git checkout argo-releases'
                                sh 'git pull'
                            }
                        }
                        dir(repoDir) {
                            
                            sh "sed -i 's|image: .*|image: ${ECR_REGISTRY}/team3-polybot-ecr:${IMAGE_TAG}|' polybot-deployment.yaml"
                            sh 'git config user.email "kinanhino24@gmail.com"'
                            sh 'git config user.name "kinanhino"'
                            
                            sh 'git add polybot-deployment.yaml'
                            sh 'git commit -m "Update image tag to ${IMAGE_TAG}"'
                            sh 'git push https://$GIT_USERNAME:$GIT_PASSWORD@github.com/kinanhino/polybot-k8s.git argo-releases'
                        }
                    }
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








