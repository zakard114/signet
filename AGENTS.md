# Signet agent instructions

Signet is an e-commerce payment gateway and ops console. The shopper sees six steps. The decision runs inside this service. The full card number is never stored and never returned.

## Docs

- Spec: [SPEC.md](SPEC.md)
- Process: [docs/process.md](docs/process.md)
- Team: [docs/team.md](docs/team.md)
- Permissions: [docs/permissions.md](docs/permissions.md)
- Packets: [docs/packets/](docs/packets/)
- Task tracker: https://github.com/zakard114/signet/issues

## Local

- App: http://127.0.0.1:8001
- Read the one decline card: GET http://127.0.0.1:8001/plates
- Postgres host port: 5433
- Grafana stays on this PC at http://127.0.0.1:3001. That is the Grafana server. The Ops tab on the app draws `GET /ops/board` and is part of the public page.

## Public

- https://signet-3oz8.onrender.com
- Do not deploy the Grafana server or this agent pack to Render.
- Do not start a Render deploy from this pack.

## Allowed in this pack

- Read the local decline card.
- Read openapi.yaml and app/main.py.
- Run agent-hooks/block_pan.py and custom-agent/agent.py on this PC.
- Run observability/oncall/responder.py on this PC with a local alert file.

## Not allowed

- POST /plates, or any other write to the decline card.
- Copy the Fault Plate agent pack.
- Put a full card number in a file, log, or telemetry.
- Edit the Ops card, rule, log, or API tabs.
- Edit app/main.py, requirements.txt, Dockerfile, or docker-compose.yaml for this pack.
- Write the security review.
- Use AWS.

