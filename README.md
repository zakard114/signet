# Signet

One checkout screen. Six steps. The stop sentence stays on the same panel.

**Live app:** (paste the Render URL here after deploy)

## Local

docker compose -f docker-compose.yaml up -d --build

Open http://127.0.0.1:8001/

## Deploy

Render web service, Docker, branch main, free instance, plus Render Postgres.

Set DATABASE_URL to the Render Postgres connection string.

main auto-deploys to the development service. Production is a manual deploy the human starts in the Render dashboard.

The image listens on Render's PORT:

uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}

## Rollback

Keep the previous deploy in Render. To go back, open the service, Events or Deploys, select the earlier successful deploy, Rollback. The previous image serves again. Do not delete that older deploy until the new one is confirmed.
