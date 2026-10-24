# Agent team

These are the roles in this repository and the handoff between them. They run on this PC. They are not deployed to Render.

## Checkout and backend

Owns the shopper screen in `preview/index.html` and the six steps in `app/main.py`: Intake, amount ceiling, card length, authorization request, decision, next action. The decision runs in this service. A completed payment hands the ops console a receipt: amount, masked card, trace id, and time. The full card number is not stored.

## Ops console

Owns the Ops window in the same page. The tabs are Inspector, Log, API, and Grafana. Inspector shows the transaction statement, the payment detail, and Amount limit USD with Set limit. This role does not add a Rule tab and does not upload a file.

## Observability

Owns `app/telemetry.py` and `observability/`. A request carries one trace id on the span, the metric, and the structured log line. The card number and the CVC are not telemetry attributes. Grafana is http://127.0.0.1:3001 on this PC. It is not a Render service.

## On-call responder

Wakes when `observability/oncall/responder.py` is given the shopper HTTP 5xx alert payload. It restarts the local `app` container and checks http://127.0.0.1:8001/. It does not POST `/plates`. It does not start a production deploy. It does not run on Render.

## Handoff

Checkout and backend write the authorization. The ops console reads that payment and the amount limit. Observability attaches the trace id and raises the shopper 5xx rule. The on-call responder acts only when that alert payload is firing.
