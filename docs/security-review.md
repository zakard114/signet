# Security review

## Result

The full card number is not stored, not returned, and not written to logs or telemetry. This was checked on the local app at http://127.0.0.1:8001.

## What was checked

- GET /plates returns the one decline card: name declined, user-facing message "This card was declined.", HTTP status 400, log field amount, retry not_retryable. The body has no run of 13 digits.
- POST /authorizations for an in-limit approval returns sentence "Payment completed." The response fields are sentence, http_status, log_field, retry, and amount. The card number is not a response field. The response header X-Trace-Id matches trace_id in the app log.
- Postgres tables authorization_log and plate have no card column. A search for 13 consecutive digits in stored text returned no rows. The plate row is the decline card above.
- The app log object has trace_id, method, path, status, and duration_ms. The approval line does not contain the card number.
- Local Grafana Explore, Loki, query {service_name="signet"}, shows that same line. The card number is not in the line.
- The existing hook blocks a file that contains 13 consecutive digits and allows a sentence with none. Both temp files were deleted. The request file that held the test number was deleted before this memo was saved.
- Read-only: authorization_log insert columns are stop_step, sentence, http_status, log_field, retry, and amount. The log line and the span attributes do not include the card number. No product file was edited.

## Limits

- This is a point-in-time human review. Semgrep was not installed. No package was added. No scanner folder was created.
- Grafana alert rules were not added. No on-call agent runs, and nothing in this review edits the decline card.
- The course operations report also asks a reader to reconstruct an alert, a model action, a policy decision, and a recovery command. Those parts were not built. This file records that limit instead of inventing them.
- Grafana and the agent pack were not deployed. No new deploy was started. The public app at https://signet-3oz8.onrender.com was not called and was not changed.
- AWS was not used.
- The hook only blocks 13 or more consecutive digits. It does not judge spaces or dashes. A field name may be the word card. That word is not the full number.
- Ops tabs exist locally. The full card number is still absent. Grafana is still not deployed.

## Later, after this review

The local Grafana server now loads [`observability/grafana/provisioning/alerting/user-impact.yaml`](../observability/grafana/provisioning/alerting/user-impact.yaml). The on-call responder is [`observability/oncall/responder.py`](../observability/oncall/responder.py). Those pieces were not part of the check above. The card-number findings in that check are unchanged.

## Disposition

Keep the current tables, log line, and span attributes. Do not add the full card number to a column, a log field, or a span attribute. Do not commit a file that still contains the test number.

