# On-call responder

This is a local check, not a rotation and not a pager.

When the Grafana rule `signet_shopper_5xx` is firing, or when a shopper cannot finish because the service itself failed:

```text
python observability/oncall/responder.py
```

The script reads http://127.0.0.1:8001/ops/board on this PC. It counts HTTP 5xx lines. A normal decline is HTTP 200 from `POST /authorizations` and is not this alert.

There is no phone, no chat webhook, and no on-call calendar. Grafana on Render is not part of this check. Do not start a production deploy from the script. Production stays a manual deploy in the Render dashboard.
