# On-call responder

Local only. There is no pager and no rotation. This does not run on Render.

The Grafana rule `signet_shopper_5xx` is the shopper HTTP 5xx alert in `observability/grafana/provisioning/alerting/user-impact.yaml`. A normal decline is HTTP 200 from `POST /authorizations` and does not match that rule.

When that alert is firing, run:

```text
python observability/oncall/responder.py --alert observability/oncall/sample-alert.json
```

`sample-alert.json` is a firing payload with no card number. The command restarts the local `app` container and then requests http://127.0.0.1:8001/. It does not POST `/plates` and it does not start a production deploy.
