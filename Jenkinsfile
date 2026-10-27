pipeline {
  agent any

  environment {
    IMAGE       = "DOCKERHUB_USER/attendance-tracker"   // <-- your Docker Hub user
    TAG         = "${env.BUILD_NUMBER}"
    DOCKER_CRED = "dockerhub-creds"   // Jenkins: Username with password
    KUBE_CRED   = "kubeconfig"        // Jenkins: Secret file
  }

  triggers {
    githubPush()   // fires on the GitHub webhook; pollSCM('H/2 * * * *') is a fallback
  }

  options { timestamps(); disableConcurrentBuilds() }

  stages {
    stage('Checkout') {
      steps { checkout scm }
    }

    stage('Test') {
      steps {
        sh '''
          python3 -m venv .venv
          . .venv/bin/activate
          pip install -q -r requirements.txt
          pytest -q tests
        '''
      }
    }

    stage('Build image') {
      steps { sh 'docker build -t $IMAGE:$TAG -t $IMAGE:latest .' }
    }

    stage('Push image') {
      steps {
        withCredentials([usernamePassword(credentialsId: env.DOCKER_CRED,
                         usernameVariable: 'DH_USER', passwordVariable: 'DH_PASS')]) {
          sh '''
            echo "$DH_PASS" | docker login -u "$DH_USER" --password-stdin
            docker push $IMAGE:$TAG
            docker push $IMAGE:latest
          '''
        }
      }
    }

    stage('Deploy to Kubernetes') {
      steps {
        withCredentials([file(credentialsId: env.KUBE_CRED, variable: 'KUBECONFIG')]) {
          sh '''
            sed -i "s|image: .*attendance-tracker:.*|image: $IMAGE:$TAG|" k8s/deployment.yaml
            kubectl apply -f k8s/pvc.yaml -f k8s/deployment.yaml -f k8s/service.yaml
            kubectl rollout status deployment/attendance-tracker --timeout=120s
          '''
        }
      }
    }
  }

  post {
    always  { sh 'docker logout || true' }
    success { echo "Deployed $IMAGE:$TAG" }
    failure { echo 'Pipeline failed, check the stage logs above.' }
  }
}
