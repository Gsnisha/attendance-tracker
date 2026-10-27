# Attendance Tracker: Flask + Docker + Kubernetes + Jenkins

Pages: Today (dashboard), Mark attendance, Students, Report. Health check at `/health`.

## 1. Run locally
    pip install -r requirements.txt
    DATABASE=./attendance.db python app.py        # http://localhost:5000
    pytest -q tests

## 2. Docker
    docker build -t DOCKERHUB_USER/attendance-tracker:latest .
    docker run -p 5000:5000 -v attdata:/data DOCKERHUB_USER/attendance-tracker:latest

## 3. Git
    git init && git add . && git commit -m "Initial commit"
    git branch -M main
    git remote add origin https://github.com/<you>/attendance-tracker.git
    git push -u origin main

## 4. Kubernetes (minikube / Docker Desktop / kind)
    # replace DOCKERHUB_USER in k8s/deployment.yaml first
    kubectl apply -f k8s/
    kubectl get pods,svc
    minikube service attendance-tracker --url     # or http://localhost:30080 on Docker Desktop

## 5. Jenkins setup
1. Jenkins host needs: docker, kubectl, python3-venv; add the `jenkins` user to the `docker` group.
2. Plugins: Git, GitHub, Pipeline, Credentials Binding.
3. Credentials (Manage Jenkins > Credentials):
   - `dockerhub-creds`: Username with password (use a Docker Hub access token)
   - `kubeconfig`: Secret file (your cluster kubeconfig)
4. New Item > Pipeline > "Pipeline script from SCM" > Git URL > branch `main` > script path `Jenkinsfile`.
   Tick "GitHub hook trigger for GITScm polling".
5. GitHub repo > Settings > Webhooks > `http://<jenkins-host>:8080/github-webhook/`, content type
   `application/json`, event: push. If Jenkins is on your laptop, expose it with `ngrok http 8080`.
   No public URL? Change the trigger to `pollSCM('H/2 * * * *')`.

## 6. Demo
Edit a template (e.g. the heading in `dashboard.html`), `git commit` and `git push`.
Jenkins starts on its own: test > build > push > deploy. Refresh the NodePort URL to see the change.
`kubectl rollout history deployment/attendance-tracker` shows each build's rollout.

## Notes
- SQLite lives on a PVC, so data survives redeploys. Use one replica; for more, move to Postgres.
- Replace `SECRET_KEY` with a Kubernetes Secret for real use.
