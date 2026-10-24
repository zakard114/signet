# Signet

![Signet payment gateway](docs/signet-gateway.jpg)

Signet is an e-commerce payment gateway and the operations console beside it.

A shopper enters an amount and a card number. Signet walks that payment through six steps, decides, and on success issues a receipt with a trace id. The full card number is never stored and never returned. The decision runs in this service. Signet does not forward the payment to a card network.

## What it is for

A checkout has to stop in a definite place. The amount can be over the ceiling. The card number can be the wrong length. One card is accepted. One card is declined from a stored plate. Every other valid card receives one stored institution sentence, or a plain “no rule” sentence when none is stored. The shopper sees the sentence and the next action on the same screen.

Operators watch the same payment. Inspector shows the latest statement, the payment detail, and the amount ceiling. Log shows the authorization rows. API shows the live routes. Grafana, on this PC only, shows request rate and latency. Those four views are the console for this gateway, not a second product.

## Six steps

1. Intake. Amount and card number.
2. Amount check. Greater than 0 and at most the stored ceiling. The default ceiling is 500.00 USD.
3. Card check. 13 to 19 digits.
4. Authorization request.
5. Authorization decision.
6. Next action. Completed, or the edit the decision allows.

CVC is collected on the form and is not sent, stored, logged, or printed.

A completed payment can be opened as a receipt. The receipt shows the amount, a masked card, the trace id, and the time. Print and Close are the only receipt actions. Close does not discard the statement. End, beside AC, does.

## Operations console

Open Ops on the checkout. The tabs are Inspector, Log, API, and Grafana.

- Inspector. The latest statement, then the payment detail, then the amount ceiling at the bottom. Set limit writes the ceiling used by step 2. There is no screen for editing institution sentences.
- Log. Authorization rows. No card column.
- API. Live routes and `/docs`.
- Grafana. Local only, at http://127.0.0.1:3001. It is not part of the public service.

## Run locally

```
docker compose -f docker-compose.yaml up -d --build
```

Open http://127.0.0.1:8001/

Postgres is on host port 5433. The app image listens on 8001.

## Public service

https://signet-3oz8.onrender.com

Render web service, Docker, branch `main`, plus Render Postgres. Set `DATABASE_URL` to the Render Postgres connection string. `main` auto-deploys the development service. Production is a manual deploy in the Render dashboard.

The image listens on Render's `PORT`:

```
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}
```

Grafana and the local agent pack are not deployed there.

## Rollback

Keep the previous deploy. In the Render service, open Events or Deploys, choose the earlier successful deploy, and roll back. The previous image serves again. Do not delete that older deploy until the new one is confirmed.
