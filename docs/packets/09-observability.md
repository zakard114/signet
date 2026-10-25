# 9/11 Observability

Local Compose runs the OpenTelemetry collector, Prometheus, Loki, Tempo, and the Grafana server. The server is http://127.0.0.1:3001 . The payment board is http://127.0.0.1:3001/d/signetpay/signet . Traces are http://127.0.0.1:3001/d/signettrace/signet-trace . Host port 3001 is container port 3000.

The Ops tab named Grafana is separate. The payment page draws it from `GET /ops/board` on the same app, including on Render.

Each request log line carries the trace id. The full card number is not an attribute. The Grafana server is not a Render service.
