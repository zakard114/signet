# 8/11 Deployment

Public app: https://signet-3oz8.onrender.com

Render runs the Docker image from branch `main`. `main` auto-deploys the development service. Production is a manual deploy in the Render dashboard. `DATABASE_URL` is the Render Postgres connection string. The image includes the checkout and the Ops Grafana tab. That tab reads `GET /ops/board` on the Render app.

The Grafana server and the agent pack stay on this PC. To roll back, select the previous successful deploy in Render. Do not delete it until the new deploy is confirmed.
