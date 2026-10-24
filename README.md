# Signet

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white) ![Postgres](https://img.shields.io/badge/Postgres-4169E1?logo=postgresql&logoColor=white) ![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-425CC7?logo=opentelemetry&logoColor=white) ![Grafana](https://img.shields.io/badge/Grafana-F46800?logo=grafana&logoColor=white)

![Signet gateway](docs/signet-gateway.jpg)

**An e-commerce payment gateway, with the operations console beside it.**

**Public service:** https://signet-3oz8.onrender.com  
**Local app:** http://127.0.0.1:8001/

## Table of contents

- [Overview](#overview)
- [Tech stack and architecture](#tech-stack-and-architecture)
- [Core features](#core-features)
- [Quick start](#quick-start)
- [Deployment](#deployment)

---

## Overview

A shopper enters an amount and a card number. Signet runs that payment through a six-step pipeline: Intake, amount ceiling, card length, authorization request, decision, and next action. A successful payment issues a receipt with a trace id. The full card number is never stored and never returned. The decision runs inside this service.

The amount must be greater than 0 and at most the stored ceiling. The default ceiling is 500.00 USD. The card number must be 13 to 19 digits. CVC is collected on the form and is not sent, stored, logged, or printed.

One card is accepted. One card is declined from a stored plate. Every other valid card receives one stored institution sentence, or a plain "no rule" sentence when none is stored. The shopper sees that sentence and the next action on the same screen.

[↑ Contents](#table-of-contents)

---

## Tech stack and architecture

| Piece | Role |
| --- | --- |
| FastAPI | Checkout, the six-step pipeline, and the operations routes |
| Postgres | Payments, the amount ceiling, and the stored plate |
| OpenTelemetry | Request traces and metrics |
| Grafana | Local dashboards for request rate and latency |
| Docker | The app, Postgres, and the local observability stack |

Grafana runs on this PC only, at http://127.0.0.1:3001. It is not part of the public service.

Intake takes the amount and the card number. The ceiling and length steps stop a payment that cannot proceed. Authorization request and decision run in this service. Next action is completed, or the edit the decision allows.

[↑ Contents](#table-of-contents)

---

## Core features

Ops sits beside the checkout. The tabs are Inspector, Log, API, and Grafana.

| Tab | What it shows |
| --- | --- |
| Inspector | The latest statement, the payment detail, and the amount ceiling at the bottom. Set limit writes the ceiling used by the amount step. There is no screen for editing institution sentences. |
| Log | Authorization rows. No card column. |
| API | Live routes and `/docs`. |
| Grafana | Local only, at http://127.0.0.1:3001. It is not part of the public service. |

A completed payment can be opened as a receipt. The receipt shows the amount, a masked card, the trace id, and the time. Print and Close are the only receipt actions. Close does not discard the statement. End, beside AC, does.

[↑ Contents](#table-of-contents)

---

## Quick start

```bash
docker compose -f docker-compose.yaml up -d --build
```

Open http://127.0.0.1:8001/

Postgres is on host port 5433. The app listens on 8001.

| | |
| --- | --- |
| App | http://127.0.0.1:8001/ |
| Postgres | host port 5433 |
| Grafana | http://127.0.0.1:3001 (this PC only) |

[↑ Contents](#table-of-contents)

---

## Deployment

Public service: https://signet-3oz8.onrender.com

`main` auto-deploys the Render development service. Production is a manual deploy in the Render dashboard. The service is a Render web service on Docker, branch `main`, plus Render Postgres. Set `DATABASE_URL` to the Render Postgres connection string.

The image listens on Render's `PORT`:

```text
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}
```

Grafana and the local agent pack are not deployed there.

To roll back, keep the previous deploy. In the Render service, open Events or Deploys, choose the earlier successful deploy, and roll back. The previous image serves again. Do not delete that older deploy until the new one is confirmed.

[↑ Contents](#table-of-contents)
