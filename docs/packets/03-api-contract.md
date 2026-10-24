# 3/11 API contract

The checkout calls `POST /authorizations`. The decline plate is `GET /plates`. The latest receipt is `GET /authorizations/latest`. The log is `GET /logs`. The amount ceiling is read with the institution rule and written with `PUT /rules/limit`.

The contract file is `openapi.yaml`. Test card numbers are not written in that file.
