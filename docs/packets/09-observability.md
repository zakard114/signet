# 9/11 Observability

Local Compose runs the OpenTelemetry collector, Prometheus, Loki, Tempo, and Grafana. Grafana is http://127.0.0.1:3001 . The payment board is http://127.0.0.1:3001/d/signetpay/signet . Traces are http://127.0.0.1:3001/d/signettrace/signet-trace .

Each request log line carries the trace id. The full card number is not an attribute. Grafana is not deployed to Render.
