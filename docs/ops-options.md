# Operations

Two ways to see the same payment. Neither one contains the full card number.

## 1. Open the address

While the local app is up:

- Decline plate: http://127.0.0.1:8001/plates
- Authorization log: http://127.0.0.1:8001/logs
- API docs: http://127.0.0.1:8001/docs
- Grafana: http://127.0.0.1:3001 with the Loki query `{service_name="signet"}`

Grafana stays on this PC. It is not on the public server.

## 2. Press Ops

1. Open http://127.0.0.1:8001
2. Press Ops at the top right. The button is off during the payment animation.
3. Open one tab at a time.

- Inspector. The latest statement is titled Transaction statement. Fields are status, amount, masked card, trace id, and time. Payment detail is the developer record of that payment: customer sentence, HTTP status, log field, and retry. After Payment detail, at the bottom of Inspector, is the amount ceiling. The stored value is the institution `amount_limit`. The default is 500. An institution decline uses the stored institution sentence. An approval is HTTP 200.
- Log. Each payment shows the time, then the sentence and the amount. Approval is pale green. A decline is red. Older rows with no amount leave the amount blank.
- API. Live routes and local docs.
- Grafana. Request count, HTTP error rate, average latency, request rate by status, P95 and P99, and the audit table. Columns are time, status, method, path, latency, and trace id. Browser static requests such as `/favicon.ico` are omitted. Choosing a status or a trace id filters the table. No card number. The full Grafana screen on this PC is http://127.0.0.1:3001/d/signetpay/signet and the trace screen is http://127.0.0.1:3001/d/signettrace/signet-trace . The Grafana server is not published.

The amount ceiling applies to every payment. The institution sentence is used only at step 5, for a card that is under the ceiling, has a valid length, and is neither the approval card nor the decline plate. There is no Ops control for that sentence. The ceiling is changed at the bottom of Inspector. Accepted values are greater than 0 and at most 100000.
