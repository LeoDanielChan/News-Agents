# News-Agents — README

This repository contains a FastAPI-based service that can be run locally with Docker Compose for development and deployed to Google Cloud Run for production. The instructions below explain how to run the project locally, build and push the container image, deploy to Cloud Run, and connect Cloud Run to Google Secret Manager to protect sensitive API keys and secrets.

This README is written to help you run the app locally, understand how it was deployed to Cloud Run, and evaluate it according to common judging criteria.

## Requirements

- Docker (20.10+)
- Docker Compose (or use `docker compose` integrated in Docker)
- Google Cloud SDK (`gcloud`) with authentication and project configured
- Optional: VS Code with the "Dev Containers" extension

If you need to run the app locally without containers, Python 3.11 and the packages in `requirements.txt` are required.

## Repository layout (important files)

- `Dockerfile` — image used for both dev/prod containers
- `docker-compose.dev.yml` — development compose file (mounts code and runs uvicorn with reload)
- `docker-compose.prod.yml` — production compose file
- `app/` — application code (FastAPI `main.py`)
- `requirements.txt` — Python dependencies
- `.devcontainer/devcontainer.json` — configuration for VS Code Dev Containers

## Environment variables and secrets

For local development a simple `.env` file is convenient. For production on Cloud Run you should use Google Secret Manager to store sensitive values (API keys, credentials) and attach them to the Cloud Run service.

Example `.env` (local development):

```
GOOGLE_GENAI_USE_VERTEXAI=1 or 0
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=location
GOOGLE_API_KEY=your-secret-key
WORLDNEWSAPI_API_KEY=your-secret-api-key
```

## Run locally — development

This project includes `docker-compose.dev.yml` configured to mount the `app/` directory into the container and start uvicorn with `--reload` so changes are applied immediately.

From the repo root:

```bash
docker compose -f docker-compose.dev.yml up --build
```

Run in detached mode:

```bash
docker compose -f docker-compose.dev.yml up --build -d
```

Follow logs:

```bash
docker compose -f docker-compose.dev.yml logs -f fastapi_agent
```

Stop and remove containers:

```bash
docker compose -f docker-compose.dev.yml down
```

Open the API at: http://localhost:8080

Note: If your container lacks `bash`, use `sh` when entering the container shell.

## Build & Deploy to Google Cloud Run (exact commands used)

The following sections include the exact commands used to build the container and deploy to Cloud Run in this project. Use them as-is or replace the placeholder variables where needed.

1) Authenticate and set your project (if not already done):

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

2) Build the container image using Cloud Build and push it to Artifact Registry (example used for this project).

You should export the image URI (or any variables you prefer) before running the build. Example:

```bash
# Example exports you can use in your shell
export IMAGE_URI=us-central1-docker.pkg.dev/news-agents-475801/news-agent-repo/news-agent:latest
export SERVICE_NAME=news-agents

# Build and push using Cloud Build
gcloud builds submit --tag "$IMAGE_URI" .
```

3) Deploy to Cloud Run using the exact command used for this project

The command below shows the exact `gcloud run deploy` invocation used. It sets an environment variable that points to a service account JSON inside the container and maps multiple secrets from Secret Manager — some mapped to environment variables and others mounted as files at specified container paths.

Replace `$SERVICE_NAME` and `$IMAGE_URI` with your values (or export them as above).

```bash
gcloud run deploy $SERVICE_NAME --image=$IMAGE_URI --platform=managed --region=us-central1 --port=8080 --allow-unauthenticated --set-env-vars="GOOGLE_APPLICATION_CREDENTIALS=/app/secrets_auth/adc.json" --set-secrets=WORLDNEWSAPI_API_KEY=WORLDNEWSAPI_API_KEY:latest,GOOGLE_API_KEY=GOOGLE_API_KEY:latest,GOOGLE_GENAI_USE_VERTEXAI=GOOGLE_GENAI_USE_VERTEXAI:latest,GOOGLE_CLOUD_PROJECT=GOOGLE_CLOUD_PROJECT:latest,GOOGLE_CLOUD_LOCATION=GOOGLE_CLOUD_LOCATION:latest,/app/secrets_db/news-agent.json=news-agent-json-file:latest,/app/secrets_auth/adc.json=adc-json-file:latest
```

4) Verify the deployed service

```bash
gcloud run services describe $SERVICE_NAME --platform=managed --region=us-central1
gcloud run services list --platform=managed --region=us-central1
```

You can tail logs using:

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" --limit 50 --project=YOUR_PROJECT_ID --format="json"
```

## Storing and using secrets with Google Secret Manager

1) Create a secret and add a value (locally or via Cloud Shell):

```bash
echo -n "MY_SUPER_SECRET" | gcloud secrets create API_KEY --data-file=- --project=YOUR_PROJECT_ID
```

2) Grant access to the Cloud Run runtime service account (replace SERVICE_ACCOUNT_EMAIL):

```bash
gcloud secrets add-iam-policy-binding API_KEY \
	--member=serviceAccount:SERVICE_ACCOUNT_EMAIL \
	--role=roles/secretmanager.secretAccessor \
	--project=YOUR_PROJECT_ID
```

3) Attach the secret to Cloud Run (as shown above) so the secret value becomes available as an environment variable inside the container (no secret stored in plain text in environment files or source control).

Notes and alternatives:
- You may use Artifact Registry instead of GCR; update `IMAGE_NAME` accordingly.
- For more advanced setups, use Workload Identity, and avoid long-lived keys.

## Accessing secrets inside your app

When you attach a secret to Cloud Run as an environment variable (via `--update-secrets`), the secret value is available to the process as a normal environment variable (for example `os.getenv('API_KEY')` in Python). If you prefer direct Secret Manager access from code (for dynamic retrieval), use the Google Cloud Secret Manager client and authenticate with the Cloud Run service account.

Example (Python snippet to access environment variable):

```py
import os

API_KEY = os.getenv('API_KEY')
```

Or use Secret Manager client to fetch secrets at runtime (requires the secret accessor role):

```py
from google.cloud import secretmanager

client = secretmanager.SecretManagerServiceClient()
name = f"projects/{PROJECT_ID}/secrets/{SECRET_NAME}/versions/latest"
payload = client.access_secret_version(request={"name": name}).payload.data.decode('UTF-8')
```

## Dev Container (VS Code) — connect directly for development

This repo includes `.devcontainer/devcontainer.json` that references `docker-compose.dev.yml`. To open the project in the container:

1. Install the "Dev Containers" extension in VS Code.
2. Open the project folder in VS Code.
3. Use the command palette (F1) -> "Dev Containers: Reopen in Container" or click the lower-left green button and choose "Reopen in Container".

VS Code will use the compose file and start the `fastapi_agent` service as your development container. The recommended VS Code extensions (Python, Pylance, Docker) will be installed in the container automatically via the `customizations.vscode` setting.

---
