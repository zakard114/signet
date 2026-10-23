import csv
import io
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse
from opentelemetry import trace
from pydantic import BaseModel

from app.telemetry import board_snapshot, count_request, log_line, remember_request, setup_otel

app = FastAPI(title="Signet", version="0.1.0", docs_url=None, redoc_url=None)
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


class LogEntry(BaseModel):
    id: int
    stop_step: Optional[int] = None
    sentence: str
    http_status: int
    log_field: str
    retry: str
    amount: Optional[float] = None
    created_at: datetime


class RuleFile(BaseModel):
    filename: str
    text: str


class RuleView(BaseModel):
    filename: str
    code: str
    sentence: str
    http_status: int
    log_field: str
    retry: Literal["retryable", "not_retryable"]
    amount_limit: float = LIMIT


def digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def has_pan(text: str) -> bool:
    run = 0
    for ch in text:
        if ch.isdigit():
            run += 1
            if run >= 13:
                return True
        else:
            run = 0
    return False


def assert_no_pan(*parts: str) -> None:
    for part in parts:
        if has_pan(part):
            raise HTTPException(status_code=400, detail="rejected: 13 or more consecutive digits")


def bare_name(value: str) -> str:
    cleaned = value.replace("\\", "/").split("/")[-1].strip()
    return (cleaned or "rule.txt")[:180]


def read_amount_limit(row: dict) -> float:
    raw = row.get("amount_limit") or row.get("limit") or ""
    if raw == "":
        return float(LIMIT)
    try:
        value = float(raw)
    except ValueError:
        return float(LIMIT)
    if value <= 0 or value > 100000:
        return float(LIMIT)
    return value


def parse_institution_rule(text: str) -> dict:
    stripped = text.strip()
    if not stripped:
        raise HTTPException(status_code=400, detail="empty file")
    first = stripped.splitlines()[0]
    header = [part.strip().lower() for part in next(csv.reader([first]))]
    if "sentence" in header and "code" in header:
        reader = csv.DictReader(io.StringIO(stripped))
        for raw in reader:
            row = {(key or "").strip().lower(): (value or "").strip() for key, value in raw.items()}
            sentence = row.get("sentence", "")
            if not sentence:
                continue
            code = row.get("code") or "institution"
            raw_status = row.get("http_status") or "400"
            try:
                http_status = int(raw_status)
            except ValueError:
                http_status = 400
            if not 100 <= http_status <= 599:
                http_status = 400
            log_field = row.get("log_fields") or row.get("log_field") or "card"
            retry = row.get("retry") or "not_retryable"
            if retry not in ("retryable", "not_retryable"):
                retry = "not_retryable"
            return {
                "code": code[:80],
                "sentence": sentence[:400],
                "http_status": http_status,
                "log_field": log_field[:80] or "card",
                "retry": retry,
                "amount_limit": read_amount_limit(row),
            }
        raise HTTPException(status_code=400, detail="rule file has no sentence")
    sentence = stripped.splitlines()[0].strip()[:400]
    if not sentence:
        raise HTTPException(status_code=400, detail="empty file")
    return {
        "code": "institution",
        "sentence": sentence,
        "http_status": 400,
        "log_field": "card",
        "retry": "not_retryable",
        "amount_limit": float(LIMIT),
    }


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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS institution_rule (
                id integer PRIMARY KEY CHECK (id = 1),
                filename text NOT NULL,
                code text NOT NULL,
                sentence text NOT NULL,
                http_status integer NOT NULL,
                log_field text NOT NULL,
                retry text NOT NULL,
                updated_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            """
            ALTER TABLE institution_rule
            ADD COLUMN IF NOT EXISTS amount_limit double precision NOT NULL DEFAULT 500
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
    setup_otel()
    init_db()


@app.middleware("http")
async def trace_request(request, call_next):
    started = time.perf_counter()
    tracer = trace.get_tracer("signet")
    with tracer.start_as_current_span(f"{request.method} {request.url.path}") as span:
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - started) * 1000)
        span_context = span.get_span_context()
        trace_id = format(span_context.trace_id, "032x")
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.target", request.url.path)
        span.set_attribute("http.status_code", response.status_code)
        line = log_line(trace_id, request.method, request.url.path, response.status_code, duration_ms)
        print(line, flush=True)
        emit = logging.getLogger("signet")
        if response.status_code >= 400:
            emit.error(line)
        else:
            emit.info(line)
        count_request(request.method, request.url.path, response.status_code)
        remember_request(request.method, request.url.path, response.status_code, duration_ms, trace_id)
        response.headers["X-Trace-Id"] = trace_id
        return response


PREVIEW = Path(__file__).resolve().parent.parent / "preview"


@app.get("/")
def home():
    return FileResponse(PREVIEW / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/swagger.css", include_in_schema=False)
def swagger_css():
    return FileResponse(PREVIEW / "swagger.css", media_type="text/css", headers={"Cache-Control": "no-store"})


@app.get("/docs", include_in_schema=False)
def swagger_ui():
    page = get_swagger_ui_html(openapi_url="/openapi.json", title="Signet")
    html = page.body.decode("utf-8").replace(
        "</head>",
        '<link type="text/css" rel="stylesheet" href="/swagger.css">\n</head>',
        1,
    )
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


@app.post("/plates", status_code=201, summary="Overwrite the one decline card")
def create_plate(plate: Plate) -> Plate:
    assert_no_pan(plate.name, plate.user_facing_message, plate.log_fields, str(plate.http_status))
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


@app.get("/plates", summary="Read the one decline card")
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


def read_institution_rule() -> Optional[RuleView]:
    with psycopg.connect(DATABASE_URL) as conn:
        found = conn.execute(
            """
            SELECT filename, code, sentence, http_status, log_field, retry, amount_limit
            FROM institution_rule
            WHERE id = 1
            """
        ).fetchone()
    if found is None:
        return None
    return RuleView(
        filename=found[0],
        code=found[1],
        sentence=found[2],
        http_status=found[3],
        log_field=found[4],
        retry=found[5],
        amount_limit=float(found[6] if found[6] is not None else LIMIT),
    )


def save_institution_rule(view: RuleView) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            """
            INSERT INTO institution_rule (
                id, filename, code, sentence, http_status, log_field, retry, amount_limit
            )
            VALUES (1, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                filename = EXCLUDED.filename,
                code = EXCLUDED.code,
                sentence = EXCLUDED.sentence,
                http_status = EXCLUDED.http_status,
                log_field = EXCLUDED.log_field,
                retry = EXCLUDED.retry,
                amount_limit = EXCLUDED.amount_limit,
                updated_at = now()
            """,
            (
                view.filename,
                view.code,
                view.sentence,
                view.http_status,
                view.log_field,
                view.retry,
                view.amount_limit,
            ),
        )


@app.get("/logs", summary="Read authorization log rows")
def read_logs() -> list[LogEntry]:
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute(
            """
            SELECT id, stop_step, sentence, http_status, log_field, retry, amount, created_at
            FROM authorization_log
            ORDER BY id DESC
            LIMIT 100
            """
        ).fetchall()
    return [
        LogEntry(
            id=row[0],
            stop_step=row[1],
            sentence=row[2],
            http_status=row[3],
            log_field=row[4],
            retry=row[5],
            amount=row[6],
            created_at=row[7],
        )
        for row in rows
    ]


@app.get("/ops/board", summary="Read the live request board")
def read_board() -> dict:
    return board_snapshot()


@app.get("/rules", summary="Read the institution rule")
def read_rule() -> RuleView:
    found = read_institution_rule()
    if found is None:
        raise HTTPException(status_code=404, detail="no institution rule")
    return found


@app.post("/rules", status_code=201, summary="Set the institution rule from a text file")
def write_rule(body: RuleFile) -> RuleView:
    if len(body.text) > 20000:
        raise HTTPException(status_code=400, detail="file too large")
    assert_no_pan(body.filename, body.text)
    parsed = parse_institution_rule(body.text)
    assert_no_pan(parsed["code"], parsed["sentence"], parsed["log_field"], str(parsed["http_status"]))
    view = RuleView(filename=bare_name(body.filename), **parsed)
    save_institution_rule(view)
    return view


@app.post("/authorizations", summary="Request authorization")
def authorize(body: AuthorizationRequest) -> AuthorizationResponse:
    pan = digits(body.card)
    rule = read_institution_rule()
    limit = rule.amount_limit if rule is not None else float(LIMIT)
    if body.amount <= 0 or body.amount > limit:
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
        if rule is None:
            row = AuthorizationResponse(
                stop_step=5,
                sentence="There is no decline rule for this card.",
                http_status=400,
                log_field="card",
                retry="not_retryable",
            )
        else:
            row = AuthorizationResponse(
                stop_step=5,
                sentence=rule.sentence,
                http_status=rule.http_status,
                log_field=rule.log_field,
                retry=rule.retry,
            )
    row.amount = body.amount
    save_log(row)
    return row
