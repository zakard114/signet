# Signet roadmap

Do not write the next gate's build notes before the current gate is finished.

| # | Name | On this screen | Done when |
|---|------|----------------|-----------|
| 1/11 | Problem Statement | The shopper sees six payment steps. The operator sees Ops. | The problem and the exclusions are fixed in SPEC. Done. |
| 2/11 | UI Prototyping | Checkout, and Ops in the same theme, with no server required for the first preview. | Both screens exist. The result is not a modal. Done. |
| 3/11 | API Contract | Authorization POST and the decline-plate GET are the contract. | Those calls are in `openapi.yaml`. Done. |
| 4/11 | Backend Implementation | Authorize, or return the stopped step and sentence. | Ceiling, length, approval card, and decline card each return their own response. Done. |
| 5/11 | Data Persistence | The authorization log and one decline plate stay in Postgres. | They survive a restart. One Signet deploy. Done. |
| 6/11 | Automated Testing | One approval and one decline, checked in code. | Unit, integration, and screen tests pass both paths. Done. |
| 7/11 | Containerization | App and preview in one image. Compose starts Postgres. | Local Compose opens the checkout. Done. |
| 8/11 | Deployment | `main` deploys the development URL. Production is started by a person. | The public URL responds. Rollback is written down. Done. |
| 9/11 | Observability | One payment's metrics, logs, and spans share a trace id in local Grafana. | Collector, Prometheus, Loki, and Tempo run locally. The card number is not in the signals. Done. |
| 10/11 | Agentic Extension | Skill, subagent, MCP, hook, and a permissions note live in this repo. | The pack is not a copy of Fault Plate. Done. |
| 11/11 | Security Review | Confirm the full card number is absent from storage, logs, and telemetry. | The review note records the result and its limits. Done. |

Not in this project: Kestra, AWS, joining policy-refund, a second Fault Plate deploy, a product tab row on the checkout, neon, a customer file upload, skipping a gate.

Ops tabs are Inspector, Log, API, and Grafana. The Grafana tab is part of the payment page. The Grafana server stays on this PC.
