# Permissions

Allowed:

- Read the local decline plate at http://127.0.0.1:8001/plates
- Read `openapi.yaml` and `app/main.py`
- Run `agent-hooks/block_pan.py` and `custom-agent/agent.py` on this PC

Not allowed:

- POST `/plates`, or any other write to the decline plate
- Put a full card number in a file, a log, or telemetry
- Deploy Grafana or this pack to Render
- Copy the Fault Plate pack
- Use AWS
