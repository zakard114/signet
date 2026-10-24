---
name: signet-local-check
description: Read the one local Signet decline plate and confirm the body has no full card number. Do not edit the repo or deploy.
---

# Signet local check

## When

`signet local check` or a local plate read.

## Steps

1. Confirm the local app is http://127.0.0.1:8001
2. Call only `GET http://127.0.0.1:8001/plates`
3. Confirm the body has `name`, `user_facing_message`, `http_status`, `log_fields`, and `retry_allowed`
4. If the body contains 13 or more digits in a row, report failure and do not copy the body again
5. Stop. Do not POST. Do not edit files. Do not open Render.
