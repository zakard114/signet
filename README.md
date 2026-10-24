# Signet

![Signet — a hand holding a card in sunlight](docs/signet-gateway.jpg)

**An e-commerce payment gateway, with the operations console beside the checkout.** The shopper pays in this service. The operator inspects the same payment and sets the amount ceiling. The full card number is never stored and never returned.

**Public service:** https://signet-3oz8.onrender.com  
**Local app:** http://127.0.0.1:8001/  
**Local Grafana (this PC only):** http://127.0.0.1:3001  
**API docs:** http://127.0.0.1:8001/docs · contract in [`openapi.yaml`](openapi.yaml)

The decision runs inside this service. It does not call out to finish the authorization.

Hub on the local app: **Checkout · Inspector · Log · API · Grafana**. Grafana and the agent pack stay on this PC. They are not part of the public Render service.

## Mission

**Signet — one checkout, one decision, one receipt.**  
A shopper needs a clear stop, a sentence, and a next action. An operator needs the same payment, without a second product and without the full card number.

- Six steps run in this service: Intake, amount ceiling, card length, authorization request, decision, next action.
- A completed payment opens a receipt: amount, masked card, trace id, and time.
- Ops uses the same window. The tabs are Inspector, Log, API, and Grafana.
- The full card number is not stored, not returned, and not written to logs or telemetry.

The stack stays behind that screen. That is what this gateway is for.

## Table of contents

- [Mission](#mission)
- [Problem](#problem)
- [Status](#status)
- [Recent updates](#recent-updates)
- [Configuration](#configuration)
- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [Architecture](#architecture)
- [Decisions and trade-offs](#decisions-and-trade-offs)
- [Project structure](#project-structure)
- [Screenshots](#screenshots)
- [Evaluation criteria](#evaluation-criteria)
- [Cloud deployment](#cloud-deployment)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Problem

A shopper enters an amount and a card number and must see which of the six steps stopped, the sentence, and the next action. An operator uses the same theme to inspect that payment and to set the amount ceiling. The full card number is never stored.

The app is one checkout. The first screen is the payment. Ops replaces that screen in the same window. One tab is open at a time. There is no tab row on the customer screen. There is no Rule tab and no CSV upload.

The amount must be greater than 0 and at most the stored ceiling. The default ceiling is 500.00 USD. The card number must be 13 to 19 digits. CVC is collected on the form and is not sent, stored, logged, or printed.

1. **Intake** takes the amount and the card number.
2. **Amount ceiling** stops a payment at or below 0, or above the stored ceiling.
3. **Card length** stops a number outside 13 to 19 digits.
4. **Authorization request** continues only when the earlier checks passed.
5. **Decision** runs inside this service. One designated card completes. One designated card stops on the stored decline plate. Every other valid card receives the stored institution sentence, or the sentence that there is no decline rule.
6. **Next action** is completed, or the edit the decision allows.

`POST /authorizations` returns HTTP 200. The decision status is the `http_status` field in the body. The card number is not a response field. A successful payment can be opened as a receipt. Print and Close are the only receipt actions. Close does not discard the statement. End, beside AC, does.

Statement of the problem and the exclusions: [`SPEC.md`](SPEC.md), [`docs/packets/01-problem-statement.md`](docs/packets/01-problem-statement.md).

### Stored records

Postgres holds the authorization log, a masked card, a trace id, the amount ceiling, and the one decline plate. The full card number is not a column.

| Record | Detail |
|--------|--------|
| `authorization_log` | `stop_step`, `sentence`, `http_status`, `log_field`, `retry`, `amount`, `created_at`, `masked_card`, `trace_id` |
| `plate` | One row. Name, shopper sentence, HTTP status, log field, and retry. No card number |
| `institution_rule` | One row. The amount ceiling is `amount_limit`. Default 500. Also the sentence used when the card is neither the approval card nor the decline plate |
| `rule_document` | Copies of that institution row for the API. The Ops console does not edit them and does not upload a file |

The Log tab reads `GET /logs`. That response has no card column. The receipt reads `GET /authorizations/latest`, which returns the masked card and the trace id.

Gate note: [`docs/packets/05-data-persistence.md`](docs/packets/05-data-persistence.md).

### Operations console

| Tab | What it shows |
| --- | --- |
| Inspector | The latest statement when that payment's HTTP status is 200, otherwise an empty statement. Payment detail shows the recorded sentence, HTTP status, log field, and retry. The amount ceiling sits at the bottom. Set limit writes the ceiling used by the amount step. This tab does not edit the decline plate or the institution sentence. |
| Log | Authorization rows from `GET /logs`. No card column. |
| API | Live routes and `/docs`. The contract file is [`openapi.yaml`](openapi.yaml). |
| Grafana | Local only, at http://127.0.0.1:3001. It is not part of the public service. |

[↑ Contents](#table-of-contents)

---

## Status

**The public service is the Render web app.** Local Compose adds Postgres and the telemetry stack on this PC. Grafana is not deployed. The agent pack is not deployed. See [Evaluation criteria](#evaluation-criteria) and [Cloud deployment](#cloud-deployment).

**Public service:** https://signet-3oz8.onrender.com  
`main` auto-deploys the Render **development** service. **Production** is a manual deploy in the Render dashboard.

### Paths (read this first)

Commands below assume you are in the **repository root** after cloning.

| | |
|--|--|
| **Your machine** | Whatever path you cloned into |
| **Example used in this README** | `E:\IT_SPACES\AI\Projects\aidt\signet` (author's Windows layout — **not required**) |

Replace the example `cd` with your own clone path. Relative paths such as `app/`, `preview/`, and `docker compose -f docker-compose.yaml` are the same everywhere.

[↑ Contents](#table-of-contents)

---

## Recent updates

**The service described on this page is the service in the repository.** There is no separate changelog file.

- Checkout, the six steps, Postgres, and the receipt are one FastAPI app. The decision runs in `app/main.py`.
- Ops tabs are Inspector, Log, API, and Grafana. There is no Rule tab and no CSV upload.
- Grafana stays at http://127.0.0.1:3001 on this PC. The agent pack stays in this repo and is not deployed to Render.
- `main` auto-deploys the Render development service. Production is started by a person in the Render dashboard.

[↑ Contents](#table-of-contents)

---

## Configuration

| Role | Where it runs | Variables |
|------|----------------|-----------|
| App | Local Compose and the Render web service | `DATABASE_URL`. Local default is Postgres on the host port **5433**. On Render, set `DATABASE_URL` to the Render Postgres connection string. |
| Listen port | Container | `PORT`. Local Compose publishes **8001**. The image uses `${PORT:-8001}`. |
| Traces, metrics, logs | Local Compose only | `OTEL_EXPORTER_OTLP_ENDPOINT` (Compose sets `http://otel-collector:4318`). |
| Grafana | This PC only | User and password are the Grafana environment values in [`docker-compose.yaml`](docker-compose.yaml). Anonymous viewing is enabled as Viewer. **Not** set on Render. |
| Agent pack | This PC only | No Render environment. It reads `http://127.0.0.1:8001/plates`. |

This repo does not ship a `.env.example`. Local values live in [`docker-compose.yaml`](docker-compose.yaml). Public database settings live in the Render dashboard.

```powershell
# Example path (replace with your clone root):
cd E:\IT_SPACES\AI\Projects\aidt\signet
docker compose -f docker-compose.yaml up -d --build
```

[↑ Contents](#table-of-contents)

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/)
- Python 3.12+ when you run `pytest` on the host (the image is `python:3.12-slim`)

No model key. The decision does not call an LLM.

[↑ Contents](#table-of-contents)

---

## Quick start

**Recommended:** app, Postgres, and the local telemetry stack via Compose.

```powershell
# Example path (replace with your clone root):
cd E:\IT_SPACES\AI\Projects\aidt\signet
docker compose -f docker-compose.yaml up -d --build
docker compose -f docker-compose.yaml ps
# App http://127.0.0.1:8001/ · Grafana http://127.0.0.1:3001 · Postgres host :5433
```

Open http://127.0.0.1:8001/

| Service | Host port | Notes |
|---------|-----------|--------|
| `app` | **8001** | Checkout, Ops, and the API. Image from [`Dockerfile`](Dockerfile) |
| `postgres` | **5433** | Postgres 16. Data bind-mount is local and is not part of the Git history |
| `grafana` | **3001** | This PC only. Dashboards `signetpay` and `signettrace` |
| `otel-collector` | none | OpenTelemetry collector. App exports to it inside Compose |
| `prometheus` | none | Metrics for the Grafana boards |
| `loki` | none | Log lines. The line has a trace id and no card number |
| `tempo` | none | Traces for the same request |

### Tests on this machine

Integration tests expect Postgres from Compose (host port 5433). The default `DATABASE_URL` in `app/main.py` points at that port.

```powershell
# Example path (replace with your clone root):
cd E:\IT_SPACES\AI\Projects\aidt\signet
docker compose -f docker-compose.yaml up -d postgres
pytest
```

| File | What it checks |
|------|----------------|
| [`tests/test_unit.py`](tests/test_unit.py) | `digits` keeps numbers only |
| [`tests/test_integration.py`](tests/test_integration.py) | One approval and one decline. The response text does not contain the card number. The newest log row is read back |
| [`tests/test_screen.py`](tests/test_screen.py) | `preview/index.html` contains the checkout and Ops labels used by those paths |

Gate note: [`docs/packets/06-automated-testing.md`](docs/packets/06-automated-testing.md).

GitHub Actions runs the same `pytest` on every push and pull request. The workflow is [`.github/workflows/tests.yml`](.github/workflows/tests.yml). It starts Postgres 16 and sets `DATABASE_URL` to `postgresql://signet:signet@127.0.0.1:5433/signet`. This page does not call that run green until Actions shows a successful job. There is no status badge.

### Local agent pack

The pack reads the local decline plate. It does not deploy itself, and it does not deploy Grafana.

```powershell
python agent-hooks/block_pan.py SOME_FILE
python custom-agent/agent.py
python mcp-server/server.py --once
```

`custom-agent/agent.py` and `mcp-server/server.py` call `GET http://127.0.0.1:8001/plates` on this PC. If the body contains a full card number, the custom agent prints nothing and stops. There is no POST. Permissions: [`docs/permissions.md`](docs/permissions.md) and [`AGENTS.md`](AGENTS.md).

[↑ Contents](#table-of-contents)

---

## Architecture

![Signet live path — checkout, six FastAPI steps, Postgres, receipt, local Grafana](docs/signet-architecture.jpg)

**Live path:** Shopper checkout → FastAPI six steps (Intake, amount ceiling, card length, authorization request, decision, next action) → Postgres (authorization log, masked card, trace id, amount ceiling, decline plate) → receipt. OpenTelemetry and Grafana stay on this PC at http://127.0.0.1:3001. The agent pack stays off Render.

Technical graph (same system, code-oriented):

```mermaid
flowchart TD
    Shopper["Shopper checkout"] --> UI["Checkout UI<br/>preview/index.html"]
    UI --> API["FastAPI<br/>app/main.py"]
    API --> S1["1 Intake"]
    S1 --> S2["2 Amount ceiling"]
    S2 --> S3["3 Card length"]
    S3 --> S4["4 Authorization request"]
    S4 --> S5["5 Decision<br/>inside this service"]
    S5 --> S6["6 Next action"]
    S6 --> PG[("Postgres<br/>authorization_log · masked card<br/>trace id · amount ceiling · plate")]
    S6 --> Receipt["Receipt"]
    API --> OTEL["OpenTelemetry<br/>local collector"]
    OTEL --> GF["Grafana<br/>127.0.0.1:3001<br/>this PC only"]
    Public["Render web service<br/>signet-3oz8.onrender.com"] --> API
    Agent["Agent pack<br/>not on Render"] -.-> API

    linkStyle default stroke:#d4a24a,stroke-width:1.5px

    style Shopper fill:#1c1a16,color:#e8e2d6,stroke:#d4a24a
    style UI fill:#1c1a16,color:#e8e2d6,stroke:#d4a24a
    style API fill:#3d3424,color:#e8e2d6,stroke:#d4a24a
    style S1 fill:#1c1a16,color:#e8e2d6,stroke:#d4a24a
    style S2 fill:#1c1a16,color:#e8e2d6,stroke:#d4a24a
    style S3 fill:#1c1a16,color:#e8e2d6,stroke:#d4a24a
    style S4 fill:#1c1a16,color:#e8e2d6,stroke:#d4a24a
    style S5 fill:#3d3424,color:#e8e2d6,stroke:#d4a24a
    style S6 fill:#1c1a16,color:#e8e2d6,stroke:#d4a24a
    style PG fill:#1e3a5f,color:#e8e2d6,stroke:#60a5fa
    style Receipt fill:#1a3328,color:#e8e2d6,stroke:#6ee7b7
    style OTEL fill:#1c1a16,color:#e8e2d6,stroke:#64748b
    style GF fill:#c2410c,color:#e8e2d6,stroke:#fb923c
    style Public fill:#1c1a16,color:#e8e2d6,stroke:#d4a24a
    style Agent fill:#1c1a16,color:#e8e2d6,stroke:#64748b
```

**Request path (short):** amount and card → checkout UI → `POST /authorizations` → ceiling, then length, then the in-service decision → log row (masked card, trace id) → receipt. Local requests also export through the OpenTelemetry collector to Grafana. The public Render service is the web app and Render Postgres. Grafana and the agent pack are not on that service.

### Tech stack

| Piece | Role |
| --- | --- |
| FastAPI | Checkout, the six-step pipeline, and the operations routes. `app/main.py` |
| Preview | Shopper screen and Ops, one dark theme. `preview/index.html` |
| Postgres 16 | Authorization log, masked card, trace id, amount ceiling, decline plate |
| OpenTelemetry | Spans, metrics, and log export from `app/telemetry.py` |
| Prometheus, Loki, Tempo | Local backends for the Grafana boards |
| Grafana 11 | Local dashboards only. http://127.0.0.1:3001 |
| Docker | App image plus the Compose stack in `docker-compose.yaml` |

### API surface

Contract: [`openapi.yaml`](openapi.yaml). Interactive docs: `/docs` on the running app.

| Method | Path | Role |
|--------|------|------|
| `GET` | `/` | Checkout and Ops UI |
| `POST` | `/authorizations` | Run the six steps. Body: `amount`, `card`. Response fields do not include the card number |
| `GET` | `/authorizations/latest` | Newest receipt: status, amount, masked card, trace id, time, sentence |
| `GET` | `/logs` | Authorization rows. No card column |
| `GET` | `/plates` | Read the one decline plate |
| `POST` | `/plates` | Replace that plate. The agent pack does not call this |
| `GET` | `/rules` | Read the institution row, including `amount_limit` |
| `PUT` | `/rules/limit` | Set the amount ceiling used by the amount step |
| `GET` | `/ops/board` | Request rate, latency, and the audit stream for the last 15 minutes |
| `GET` | `/docs` | Swagger UI |

`/rules` and `/rules/documents` exist on the API. The Ops console has no Rule tab and no CSV upload. Inspector writes the ceiling only.

Gate notes: [`docs/packets/03-api-contract.md`](docs/packets/03-api-contract.md), [`docs/packets/04-backend.md`](docs/packets/04-backend.md).

[↑ Contents](#table-of-contents)

---

## Decisions and trade-offs

- **Decision inside this service.** Ceiling, length, the approval card, the decline plate, and the institution sentence are applied in `app/main.py`. Trade-off: there is no external authorizer to swap in. The behavior is the code and the stored plate.
- **One HTTP 200 from `POST /authorizations`.** The shopper-facing outcome is `http_status` in the JSON body, plus `sentence`, `log_field`, and `retry`. Trade-off: a client that only looks at the transport status will treat a decline as success unless it reads the body.
- **Masked card on the log, no full number.** `authorization_log.masked_card` is stored. The plate table has no card column. `GET /logs` does not return a card. Trade-off: a receipt can show a mask; it cannot show or recover the full number.
- **CVC stays on the form.** The field is masked in the browser. It is not sent, stored, logged, or printed. Trade-off: the API cannot echo it, because it never receives it.
- **Grafana on this PC only.** Compose runs the collector, Prometheus, Loki, Tempo, and Grafana. Render runs the web service and Render Postgres. Trade-off: the public URL has no metrics UI. Operators use http://127.0.0.1:3001.
- **Agent pack off Render.** Skill, subagent note, MCP server, digit-run hook, and the custom agent stay in the repo and talk to the local app. Trade-off: the public site does not expose those tools.
- **Development follows `main`. Production does not.** A push to `main` auto-deploys the Render development service. Production is a manual deploy in the Render dashboard. Trade-off: two Render actions, so a development deploy is not a production deploy.
- **No second public UI.** There is no separate hosted prototype. The same `preview/index.html` is what Compose and Render serve.

### Security notes

The review memo is [`docs/security-review.md`](docs/security-review.md). It records a point-in-time check on the local app: the full card number was not in `GET /plates`, not in the authorization response, not in `authorization_log` or `plate` as a full number, and not in the app log line or local Loki. The hook `agent-hooks/block_pan.py` blocks a file that contains 13 or more consecutive digits.

Limits recorded in that memo, not extra controls: Semgrep was not installed, Grafana alert rules were not added, and the public app was not called for that review. The hook does not treat spaces or dashes as a digit run. AWS is not used.

[↑ Contents](#table-of-contents)

---

## Project structure

```text
app/                  # FastAPI app, six steps, Postgres access, OpenTelemetry
  main.py             # Routes, tables, decision
  telemetry.py        # OTLP export and the in-process request board
preview/              # Checkout and Ops UI (index.html) plus Swagger CSS
tests/                # Unit, integration, and screen tests
observability/        # Collector, Prometheus, Loki, Tempo, Grafana provisioning
agent-hooks/          # block_pan.py — blocks a long digit run in a file
custom-agent/         # Reads GET /plates on this PC
mcp-server/           # Local MCP read of the same plate
agent-capabilities/   # Local skill and authorization-reviewer note
docs/                 # Gate packets, security review, hero and architecture images
  packets/            # 01 problem through 11 security review
  security-review.md
  signet-gateway.jpg  # Campaign still. Not a picture of the UI
  signet-architecture.jpg
observability/oncall/ # Local responder. No pager
.github/workflows/    # tests.yml — pytest with a Postgres service
openapi.yaml          # API contract
Dockerfile            # python:3.12-slim, uvicorn, PORT
docker-compose.yaml   # app, Postgres, local telemetry
requirements.txt
SPEC.md               # Problem, screens, exclusions
AGENTS.md             # What the local agent pack may do
```

[`samples/`](samples) is present for local files the app can read. It is not an Ops screen, and this README does not ask anyone to upload a CSV.

[↑ Contents](#table-of-contents)

---

## Screenshots

No capture of this app is in the repository. The picture at the top of the page is an editorial photo collage, not a screenshot. [`docs/signet-architecture.jpg`](docs/signet-architecture.jpg) is the architecture diagram. Neither file is a capture of the checkout, and this section does not use them as one.

Searched, and none of these held a capture of the checkout, the receipt, Inspector, Log, API, or Grafana:

- `C:\Users\HP EliteBook\.cursor\projects\e-IT-SPACES-AI-Projects-aidt-signet\assets\` — only generated files (`signet-architecture.jpg`, `signet-gateway-hero.jpg`, `signet-gateway.jpg`)
- `C:\Users\HP EliteBook\.cursor\projects\e-IT-SPACES-AI-Projects-aidt-signet\agent-transcripts\` — the name `ISSUE_3.png` appears as text in a pasted note. No image file with that name is stored there
- `E:\IT_SPACES\AI\Projects\aidt\signet\docs\` — `signet-gateway.jpg` and `signet-architecture.jpg` only
- Names matching `ISSUE`, `screenshot`, `screen`, or `capture` under `E:\IT_SPACES\AI\Projects\aidt\signet` — no app capture
- Filename `ISSUE_3.png` under `C:\Users\HP EliteBook\Downloads`, `Desktop`, `Pictures`, and `E:\IT_SPACES\AI` — no file by that name was found before this page was written

The labels below are the ones in [`preview/index.html`](preview/index.html). The running page is http://127.0.0.1:8001/ and https://signet-3oz8.onrender.com.

### Checkout

The rail steps are Intake, Amount check, Card check, Authorization request, Authorization decision, and Next action. The payment block is labeled Payment. The amount label is `Amount USD · Limit 500.00`. The other fields are Card number and CVC. The buttons are Authorize, AC, End, and Statement. Statement stays hidden until a payment has been issued. Ops sits at the top right.

### Receipt

Statement opens the slip. Its title is Receipt. The kicker is Completed or Declined. The rows are Amount, Card, Trace ID, and Timestamp. The actions are Print and Close.

### Ops

The tabs are Inspector, Log, API, and Grafana. Payment leaves Ops and returns to the checkout.

| Tab | Labels on the page |
| --- | --- |
| Inspector | Transaction statement, Payment detail, Amount limit USD, Set limit |
| Log | Authorization log |
| API | Local API, Open local docs |
| Grafana | Payment control. The figures are Requests, HTTP error rate, and Average latency. The charts are Request rate by status and Latency P95 and P99. The table is Audit log. |

UI note: [`docs/packets/02-ui-prototyping.md`](docs/packets/02-ui-prototyping.md).

### Monitoring

Grafana is local only.

| Board | URL |
|-------|-----|
| Signet | http://127.0.0.1:3001/d/signetpay/signet |
| Signet trace | http://127.0.0.1:3001/d/signettrace/signet-trace |

Panels on the Signet board: request count, HTTP error rate, average latency, request rate by status, P95 and P99, and the payment and decline log with trace ids. Success is green. An HTTP decline is red. The same log line is in local Loki. The card number is not an attribute.

No screenshot file of those boards is stored in this repo. Open the URLs above after Compose is up. They are not on https://signet-3oz8.onrender.com.

A user-impact rule is provisioned for local Grafana only: [`observability/grafana/provisioning/alerting/user-impact.yaml`](observability/grafana/provisioning/alerting/user-impact.yaml). It watches HTTP 5xx on `signet_requests_total`. A normal decline is HTTP 200 from `POST /authorizations` and does not raise it. The running Grafana process loads that file when it next reads provisioning. This page does not claim the rule has fired.

The on-call command is `python observability/oncall/responder.py --alert observability/oncall/sample-alert.json`. Given that firing payload, it restarts the local app container and requests http://127.0.0.1:8001/. There is no pager and no rotation. See [`observability/oncall/responder.md`](observability/oncall/responder.md). It stays on this PC.

Gate note: [`docs/packets/09-observability.md`](docs/packets/09-observability.md). The security review memo still says alert rules were not added. That memo was not rewritten when this rule file was added.

### Docker Compose

`docker compose -f docker-compose.yaml up -d --build` starts the app on **8001**, Postgres on **5433**, and Grafana on **3001**, plus the collector, Prometheus, Loki, and Tempo without published host ports.

The picture of that path is [`docs/signet-architecture.jpg`](docs/signet-architecture.jpg). Container note: [`docs/packets/07-containerization.md`](docs/packets/07-containerization.md).

### Ops on the same window

Ops opens in the same window. The tab labels are the ones in the table above. The Grafana tab reads `/ops/board` and draws that board in the page. It does not embed the Grafana process. Grafana itself stays at http://127.0.0.1:3001 on this PC.

There is no Rule tab and no file upload on this screen.

### Not a second public app

There is no second hosted UI, no public Grafana, and no public agent endpoint. Peer review of the running product uses https://signet-3oz8.onrender.com. Metrics and the agent pack stay on the machine that runs Compose.

[↑ Contents](#table-of-contents)

---

## Evaluation criteria

Course final-project rubric for this gateway. The score is what this repo can claim now. Max is the course maximum. A lower score means the missing piece is named in the evidence.

| # | Criterion | Max | Score | What Signet has |
|---|-----------|----:|------:|-----------------|
| 1 | **Problem description** | 2 | 2 | [Problem](#problem) and [`SPEC.md`](SPEC.md). E-commerce payment gateway and ops console. Six steps: Intake, amount ceiling, card length, authorization request, decision, next action. A success issues a receipt with a trace id. The full card number is never stored. The decision runs inside this service. |
| 2 | **Product specification** | 2 | 2 | Written spec: [`SPEC.md`](SPEC.md). Task tracker: https://github.com/zakard114/signet/issues. Acceptance criteria and implementation comments are on [#4](https://github.com/zakard114/signet/issues/4), [#5](https://github.com/zakard114/signet/issues/5), [#6](https://github.com/zakard114/signet/issues/6), and [#7](https://github.com/zakard114/signet/issues/7). |
| 3 | **Agent team specification** | 2 | 2 | [`docs/team.md`](docs/team.md), linked from [`AGENTS.md`](AGENTS.md). Roles: checkout and backend, ops console, observability, on-call responder. |
| 4 | **Context management** | 2 | 2 | [`AGENTS.md`](AGENTS.md) states the project and links [`docs/process.md`](docs/process.md), [`docs/team.md`](docs/team.md), [`docs/permissions.md`](docs/permissions.md), and [`docs/packets/`](docs/packets/). Grafana and the agent pack stay off Render. No full card number in files, logs, or telemetry. No POST `/plates` from the pack. |
| 5 | **Application** | 2 | 2 | [`preview/index.html`](preview/index.html), [`app/main.py`](app/main.py), Postgres. One command: `docker compose -f docker-compose.yaml up -d --build`. Screen labels are the ones in that HTML file. |
| 6 | **Testing** | 2 | 2 | Unit: [`tests/test_unit.py`](tests/test_unit.py). Integration: [`tests/test_integration.py`](tests/test_integration.py). Also [`tests/test_screen.py`](tests/test_screen.py). Command: `.venv\Scripts\python.exe -m pytest -q --tb=line` with `DATABASE_URL=postgresql://signet:signet@127.0.0.1:5433/signet`. Result this session: 4 passed. |
| 7 | **Containerization** | 2 | 2 | [`docker-compose.yaml`](docker-compose.yaml) starts the app and Postgres with the command in row 5. [`Dockerfile`](Dockerfile). |
| 8 | **Deployment** | 2 | 2 | https://signet-3oz8.onrender.com. `main` auto-deploys development. Production is a manual Render dashboard deploy. Rollback is [Rollback](#rollback). This repo does not start that production deploy. |
| 9 | **CI/CD** | 3 | 2 | [`.github/workflows/tests.yml`](.github/workflows/tests.yml) runs `pytest` on pull requests with a Postgres 16 service. No badge. A completed green Actions run is not claimed on this page. Development CD is the Render auto-deploy from `main`. Production stays manual. |
| 10 | **Observability** | 2 | 2 | [`app/telemetry.py`](app/telemetry.py) and [`observability/`](observability/). Metrics, traces, and the structured log share a trace id. The log line has no card number and no CVC. Grafana: http://127.0.0.1:3001. Not on Render. |
| 11 | **Alerting on user impact** | 1 | 1 | [`observability/grafana/provisioning/alerting/user-impact.yaml`](observability/grafana/provisioning/alerting/user-impact.yaml). Trigger: the 5-minute rate of HTTP 5xx on `signet_requests_total` stays above 0 for 5 minutes. A normal decline is HTTP 200 and does not raise it. Local Grafana only. This page does not claim the rule has fired. |
| 12 | **On-call agent** | 2 | 1 | [`observability/oncall/responder.py`](observability/oncall/responder.py) read [`observability/oncall/sample-alert.json`](observability/oncall/sample-alert.json) and found the local app already answering HTTP 200, so it did not repair an outage. An earlier `docker compose restart app` timed out after 180 seconds. Not on Render. No POST `/plates`. |

### Quick verification commands

```powershell
# Example path (replace with your clone root):
cd E:\IT_SPACES\AI\Projects\aidt\signet
docker compose -f docker-compose.yaml up -d --build
# http://127.0.0.1:8001/  ·  http://127.0.0.1:3001
pytest
python agent-hooks/block_pan.py README.md
python custom-agent/agent.py
python mcp-server/server.py --once
```

`pytest` needs Postgres on host port 5433. The agent commands need the local app. They do not target the public URL.

[↑ Contents](#table-of-contents)

---

## Cloud deployment

### Render

Primary public face: https://signet-3oz8.onrender.com

This repo has no `render.yaml`. The service is a Render **web service** built from [`Dockerfile`](Dockerfile), branch `main`, plus **Render Postgres**.

1. The development service tracks `main`. A push to `main` auto-deploys **development**.
2. **Production** is a manual deploy in the Render dashboard. It does not follow that push by itself.
3. On the web service, set `DATABASE_URL` to the Render Postgres connection string. Do not point it at the laptop's port 5433.
4. The image listens on Render's `PORT`:

```text
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}
```

5. Do not add Grafana, the OpenTelemetry collector, Prometheus, Loki, Tempo, or the agent pack to that service.
6. Smoke the public URL at `/` after the deploy is live. `/docs` is the API UI on that same host.

Deploy note: [`docs/packets/08-deployment.md`](docs/packets/08-deployment.md).

### What stays on this PC

| Piece | Where |
|-------|--------|
| Grafana http://127.0.0.1:3001 | Compose on this PC. Not a Render service |
| Prometheus, Loki, Tempo, collector | Compose on this PC |
| Agent pack (`AGENTS.md`, `agent-hooks`, `custom-agent`, `mcp-server`) | This repo, this PC. Not deployed |
| Postgres host port 5433 | Local Compose only. Render uses its own Postgres |

There is no second public prototype and no hosted metrics site.

### Postgres

| Place | Database |
|-------|----------|
| This PC | Compose Postgres 16, host port **5433**, database `signet`. The URL is `DATABASE_URL` in [`docker-compose.yaml`](docker-compose.yaml). |
| Public service | Render Postgres. The web service `DATABASE_URL` is that connection string. |

Local data is a bind mount on this machine. It is not committed. Restarting the app keeps the log, the plate, and the ceiling. The public database is separate from that volume.

### Rollback

Keep the previous deploy. In the Render service, open **Events** or **Deploys**, choose the earlier successful deploy, and roll back. The previous image serves again. Do not delete that older deploy until the new one is confirmed.

Rolling back the web service does not change Grafana, because Grafana was not deployed. It does not roll back the local Postgres volume.

[↑ Contents](#table-of-contents)

---

## Troubleshooting

1. **The public site has no Grafana.** That is expected. Open http://127.0.0.1:3001 on the machine running Compose. Port **3000** is not this project's Grafana. Signet uses **3001**.
2. **Port already in use.** This stack needs **8001** (app), **5433** (Postgres), and **3001** (Grafana). Stop the other process or the other Compose project that holds the port, then start again:

```powershell
# Example path (replace with your clone root):
cd E:\IT_SPACES\AI\Projects\aidt\signet
docker compose -f docker-compose.yaml up -d --build
docker compose -f docker-compose.yaml ps
```

3. **`pytest` cannot connect.** Start Postgres first. The tests use host port 5433. The app container uses the hostname `postgres`, not `127.0.0.1`.
4. **Agent commands fail.** `custom-agent/agent.py` and `mcp-server/server.py` read http://127.0.0.1:8001/plates. The local app must be up. They are not aimed at the Render URL.
5. **A file is blocked by the hook.** `agent-hooks/block_pan.py` exits with a block when it sees 13 or more consecutive digits. That is the intended check. Do not commit a full card number to get past it.
6. **Development changed and production did not.** `main` auto-deploys development only. Production is a manual deploy in the Render dashboard. Use [Rollback](#rollback) if the new image should not stay.

This repo does not include a separate Docker troubleshooting guide.

[↑ Contents](#table-of-contents)

---

## License

This repository does not include a `LICENSE` file.

[↑ Contents](#table-of-contents)
