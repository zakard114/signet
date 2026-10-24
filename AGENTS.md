# Signet agent instructions

Signet is an e-commerce payment gateway. The shopper sees six steps. The full card number is never stored and never returned.

## Local

- App: http://127.0.0.1:8001
- Read the one decline card: GET http://127.0.0.1:8001/plates
- Postgres host port: 5433
- Grafana stays on this PC at http://127.0.0.1:3001

## Public

- https://signet-3oz8.onrender.com
- Do not deploy Grafana or this agent pack to Render.
- Do not start a Render deploy from this pack.

## Allowed in this pack

- Read the local decline card.
- Read openapi.yaml and app/main.py.
- Run agent-hooks/block_pan.py and custom-agent/agent.py on this PC.

## Not allowed

- POST /plates, or any other write to the decline card.
- Copy the Fault Plate agent pack.
- Put a full card number in a file, log, or telemetry.
- Edit the Ops card, rule, log, or API tabs.
- Edit app/main.py, requirements.txt, Dockerfile, or docker-compose.yaml for this pack.
- Write the security review.
- Use AWS.

