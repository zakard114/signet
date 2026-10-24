# 8/11 Deployment

Public app: https://signet-3oz8.onrender.com

Render runs the Docker image from branch `main`. `main` auto-deploys the development service. Production is a manual deploy in the Render dashboard. `DATABASE_URL` is the Render Postgres connection string.

Grafana and the agent pack are not deployed. To roll back, select the previous successful deploy in Render. Do not delete it until the new deploy is confirmed.
