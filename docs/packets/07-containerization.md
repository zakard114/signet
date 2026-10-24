# 7/11 Containerization

`docker-compose.yaml` starts Postgres, the app, and the local telemetry stack. The app image copies `requirements.txt`, `app/`, and `preview/`. It listens on port 8001 locally and on `PORT` in production. Postgres data is bind-mounted on E:.

Grafana is in Compose for this PC only.
