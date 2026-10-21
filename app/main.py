import os
from pathlib import Path
from typing import Literal, Optional

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Signet", version="0.1.0")
LIMIT = 500
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://signet:signet@127.0.0.1:5433/signet",
)


class AuthorizationRequest(BaseModel):
    amount: float
    card: str


class AuthorizationResponse(BaseModel):
    stop_step: Optional[int] = None
    sentence: str
    http_status: int
    log_field: str
    retry: Literal["retryable", "not_retryable"]
    amount: Optional[float] = None


class Plate(BaseModel):
    name: str
    user_facing_message: str
    http_status: int
    log_fields: str
    retry_allowed: Literal["retryable", "not_retryable"]


def digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def init_db() -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS authorization_log (
                id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                stop_step integer,
                sentence text NOT NULL,
                http_status integer NOT NULL,
                log_field text NOT NULL,
                retry text NOT NULL,
                amount double precision,
                created_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS plate (
                id integer PRIMARY KEY CHECK (id = 1),
                name text NOT NULL,
                user_facing_message text NOT NULL,
                http_status integer NOT NULL,
                log_fields text NOT NULL,
                retry_allowed text NOT NULL
            )
            """
        )


def save_log(row: AuthorizationResponse) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            """
            INSERT INTO authorization_log
                (stop_step, sentence, http_status, log_field, retry, amount)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                row.stop_step,
                row.sentence,
                row.http_status,
                row.log_field,
                row.retry,
                row.amount,
            ),
        )


def plate_decline() -> AuthorizationResponse:
    with psycopg.connect(DATABASE_URL) as conn:
        found = conn.execute(
            """
            SELECT user_facing_message, http_status, log_fields, retry_allowed
            FROM plate
            WHERE id = 1
            """
        ).fetchone()
    if found is None:
        return AuthorizationResponse(
            stop_step=5,
            sentence="We could not complete your payment.",
            http_status=400,
            log_field="amount",
            retry="not_retryable",
        )
    return AuthorizationResponse(
        stop_step=5,
        sentence=found[0],
        http_status=found[1],
        log_field=found[2],
        retry=found[3],
    )


@app.on_event("startup")
def startup() -> None:
    init_db()


PREVIEW = Path(__file__).resolve().parent.parent / "preview"


@app.get("/")
def home():
    return FileResponse(PREVIEW / "index.html")


@app.post("/plates", status_code=201)
def create_plate(plate: Plate) -> Plate:
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            """
            INSERT INTO plate (
                id, name, user_facing_message, http_status, log_fields, retry_allowed
            )
            VALUES (1, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                user_facing_message = EXCLUDED.user_facing_message,
                http_status = EXCLUDED.http_status,
                log_fields = EXCLUDED.log_fields,
                retry_allowed = EXCLUDED.retry_allowed
            """,
            (
                plate.name,
                plate.user_facing_message,
                plate.http_status,
                plate.log_fields,
                plate.retry_allowed,
            ),
        )
    return plate


@app.get("/plates")
def read_plate() -> Plate:
    with psycopg.connect(DATABASE_URL) as conn:
        found = conn.execute(
            """
            SELECT name, user_facing_message, http_status, log_fields, retry_allowed
            FROM plate
            WHERE id = 1
            """
        ).fetchone()
    if found is None:
        raise HTTPException(status_code=404, detail="no plate")
    return Plate(
        name=found[0],
        user_facing_message=found[1],
        http_status=found[2],
        log_fields=found[3],
        retry_allowed=found[4],
    )


@app.post("/authorizations")
def authorize(body: AuthorizationRequest) -> AuthorizationResponse:
    pan = digits(body.card)
    if body.amount <= 0 or body.amount > LIMIT:
        row = AuthorizationResponse(
            stop_step=2,
            sentence="This amount is above the limit.",
            http_status=400,
            log_field="amount",
            retry="retryable",
        )
    elif not 13 <= len(pan) <= 19:
        row = AuthorizationResponse(
            stop_step=3,
            sentence="The card number length is not valid.",
            http_status=400,
            log_field="card",
            retry="retryable",
        )
    elif pan == "4000000000000002":
        row = plate_decline()
    elif pan == "4242424242424242":
        row = AuthorizationResponse(
            sentence="Payment completed.",
            http_status=200,
            log_field="amount",
            retry="not_retryable",
            amount=body.amount,
        )
    else:
        row = AuthorizationResponse(
            stop_step=5,
            sentence="There is no decline rule for this card.",
            http_status=400,
            log_field="card",
            retry="not_retryable",
        )
    save_log(row)
    return row
