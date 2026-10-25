# Signet

## Problem

A shopper enters an amount and a card number and must see which of six steps stopped, the sentence, and the next action. An operator uses the same theme to inspect that payment and to set the amount ceiling. The full card number is never stored.

The app is one checkout. The first screen is the payment. Ops replaces that screen in the same window. Ops tabs are Inspector, Log, API, and Grafana. One tab is open at a time. There is no tab row on the customer screen.

## Customer screen

Dark field, one panel. Six steps on the left, payment on the right.

1. Intake.
2. Amount check. Greater than 0 and at most the stored ceiling. The default is 500.00 USD.
3. Card check. 13 to 19 digits.
4. Authorization request. Only a payment that passed the earlier checks is sent.
5. Authorization decision.
6. Next action. Completed, or the edit the decision allows.

Authorize walks the steps. A pass shows `Payment completed.` above the buttons. Statement appears on the right of that line only after HTTP status 200 in this page session. Opening it shifts the payment left and shows a receipt titled `Receipt`. The kicker is Completed or Declined. The fields are amount, masked card, trace id, and time. Actions are Print and Close. Close hides the panel and unlocks the fields. Statement stays. End sits beside AC and can be pressed only when a statement exists. End closes the panel, unlocks the fields, and retires Statement. AC, or clearing the fields, does not remove Statement or close an open receipt. Short notices such as `Payment completed.` and `Amount limit saved.` fade out after 5 seconds. While the receipt is open, the amount, card, and CVC are locked and dimmed. Opening the receipt does not add a horizontal scrollbar. Print does not include the full card number.

The card field and the CVC field are masked. The character just typed stays visible briefly, then masks. An eye on the right of each field reveals that field.

Empty amount, card, or CVC does not start authorization. Only then does that field get a red border and a red star. A card number outside 13 to 19 digits does the same, and `The card number length is not valid.` appears above Authorize.

The designated approval card, under the ceiling, completes. The designated decline card stops at step 5. Its sentence, HTTP status, log field, and retry come from the one stored decline plate. Any other card of valid length uses the stored institution sentence when one exists, and otherwise says there is no decline rule. The customer has no file upload.

## Ops

Ops is one button at the top right of the checkout. It is disabled while the payment animation runs.

- Inspector. A statement only when the latest transaction HTTP status is 200. Otherwise the statement is empty. HTTP 200 is green. Payment detail shows the recorded sentence, HTTP status, log field, and retry. After Payment detail ends, the amount ceiling sits at the bottom. The stored value is the institution `amount_limit`. The default is 500. This tab does not edit the decline plate or the institution sentence.
- Log. `GET /logs` returns id, stop_step, sentence, http_status, log_field, retry, amount, and created_at from `authorization_log`. There is no card column.
- API. Live OpenAPI routes. Local docs are `/docs`. The contract file is `openapi.yaml`.
- Grafana. The tab draws request count, HTTP error rate, average latency, request rate by status, P95 and P99, and an audit log with trace ids from `GET /ops/board` on the same app. That tab is on the local page and on the public page. Success is green. An HTTP decline is red. The Grafana server, with the same log in Loki, is http://127.0.0.1:3001 on this PC. It is not a Render service.

## Out of scope

No shared editing, refunds, ledgers, loan advice, lab uploads, or supplement checks. No product tab row on the customer screen. No AWS.

## Files

The preview is `preview/index.html`. The customer flow has no demo buttons. The amount ceiling is edited in Inspector. There is no Ops screen for the institution sentence. Postgres and the telemetry stack run locally with Compose.
