# Process

Work starts from [`SPEC.md`](../SPEC.md) and a GitHub issue on https://github.com/zakard114/signet/issues. The issue states the acceptance criteria. The change lands in this repo, then:

1. Local stack: `docker compose -f docker-compose.yaml up -d --build`
2. Tests: `pytest` against Postgres on host port 5433
3. `main` auto-deploys the Render **development** service at https://signet-3oz8.onrender.com
4. **Production** is a manual deploy in the Render dashboard. This process does not start it.

Grafana and the agent pack stay on this PC. A shopper HTTP 5xx alert is handled by the on-call responder locally. It is not a Render job.

Rollback of the web service is the previous successful Render deploy. Do not delete that deploy until the newer one is confirmed.
