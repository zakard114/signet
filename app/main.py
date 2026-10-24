import csv
import io
import logging
import os
import secrets
import time
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

import psycopg
from fastapi import FastAPI, HTTPException, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse
from opentelemetry import trace
from pydantic import BaseModel

from app.telemetry import board_snapshot, count_request, log_line, remember_request, setup_otel

app = FastAPI(title="Signet", version="0.1.0", docs_url=None, redoc_url=None)
LIMIT = 500
REQUEST_TRACE: ContextVar[str] = ContextVar("signet_trace_id", default="")
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


class Receipt(BaseModel):
    status: Literal["SUCCESS", "DECLINED"]
    amount: Optional[float] = None
    masked_card: str = ""
    trace_id: str = ""
    created_at: datetime
    http_status: int
    sentence: str = ""
    log_field: str = ""
    retry: str = ""


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


class RuleDocumentEdit(BaseModel):
    code: str
    sentence: str
    http_status: int
    log_field: str
    retry: Literal["retryable", "not_retryable"]


class AmountLimitUpdate(BaseModel):
    amount_limit: float


class RuleDocument(BaseModel):
    id: int
    filename: str
    code: str
    sentence: str
    http_status: int
    log_field: str
    retry: Literal["retryable", "not_retryable"]
    amount_limit: float
    active: bool
    created_at: datetime


def digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def mask_pan(pan: str) -> str:
    if len(pan) < 10:
        return ""
    masked = f"{pan[:6]}****{pan[-4:]}"
    if has_pan(masked):
        return ""
    return masked


def current_trace_id() -> str:
    pinned = REQUEST_TRACE.get()
    if pinned:
        return pinned
    span_context = trace.get_current_span().get_span_context()
    if span_context is not None and span_context.is_valid and span_context.trace_id:
        return format(span_context.trace_id, "032x")
    return secrets.token_hex(16)


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
        conn.execute(
            """
            ALTER TABLE authorization_log
            ADD COLUMN IF NOT EXISTS masked_card text NOT NULL DEFAULT ''
            """
        )
        conn.execute(
            """
            ALTER TABLE authorization_log
            ADD COLUMN IF NOT EXISTS trace_id text NOT NULL DEFAULT ''
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rule_document (
                id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                filename text NOT NULL,
                code text NOT NULL,
                sentence text NOT NULL,
                http_status integer NOT NULL,
                log_field text NOT NULL,
                retry text NOT NULL,
                amount_limit double precision NOT NULL DEFAULT 500,
                active boolean NOT NULL DEFAULT false,
                created_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )


def save_log(row: AuthorizationResponse, masked_card: str, trace_id: str) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            """
            INSERT INTO authorization_log
                (stop_step, sentence, http_status, log_field, retry, amount, masked_card, trace_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                row.stop_step,
                row.sentence,
                row.http_status,
                row.log_field,
                row.retry,
                row.amount,
                masked_card,
                trace_id,
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
    seed_rule_documents()


@app.middleware("http")
async def trace_request(request, call_next):
    started = time.perf_counter()
    tracer = trace.get_tracer("signet")
    with tracer.start_as_current_span(f"{request.method} {request.url.path}") as span:
        span_context = span.get_span_context()
        if span_context is not None and span_context.is_valid and span_context.trace_id:
            trace_id = format(span_context.trace_id, "032x")
        else:
            trace_id = secrets.token_hex(16)
        request.state.trace_id = trace_id
        token = REQUEST_TRACE.set(trace_id)
        try:
            response = await call_next(request)
        finally:
            REQUEST_TRACE.reset(token)
        duration_ms = int((time.perf_counter() - started) * 1000)
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


ROOT = Path(__file__).resolve().parent.parent
PREVIEW = ROOT / "preview"
SAMPLES = ROOT / "samples"


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
            FROM rule_document
            WHERE active
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        if found is None:
            found = conn.execute(
            """
            SELECT filename, code, sentence, http_status, log_field, retry, amount_limit
            FROM institution_rule
            WHERE id = 1
            """
        ).fetchone()
    if found is None or not str(found[2] or "").strip():
        return None
    return RuleView(
        filename=found[0],
        code=found[1],
        sentence=found[2],
        http_status=found[3],
        log_field=found[4],
        retry=found[5],
        amount_limit=read_amount_ceiling(),
    )


def read_amount_ceiling() -> float:
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute("SELECT amount_limit FROM institution_rule WHERE id = 1").fetchone()
    if row is None or row[0] is None:
        return float(LIMIT)
    value = float(row[0])
    if value <= 0 or value > 100000:
        return float(LIMIT)
    return value


def set_amount_ceiling(amount: float) -> RuleView:
    if amount <= 0 or amount > 100000:
        raise HTTPException(status_code=400, detail="rejected limit")
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            """
            INSERT INTO institution_rule (
                id, filename, code, sentence, http_status, log_field, retry, amount_limit
            )
            VALUES (1, '', '', '', 400, 'amount', 'not_retryable', %s)
            ON CONFLICT (id) DO UPDATE SET
                amount_limit = EXCLUDED.amount_limit,
                updated_at = now()
            """,
            (amount,),
        )
    found = read_institution_rule()
    ceiling = read_amount_ceiling()
    if found is None:
        return RuleView(
            filename="",
            code="",
            sentence="",
            http_status=400,
            log_field="amount",
            retry="not_retryable",
            amount_limit=ceiling,
        )
    found.amount_limit = ceiling
    return found


def stored_csv_name(filename: str) -> str:
    name = bare_name(filename)
    if not name.lower().endswith(".csv"):
        stem = name.rsplit(".", 1)[0] if "." in name else name
        name = f"{stem or 'rule'}.csv"
    return name


def write_rule_csv(view: RuleView) -> str:
    name = stored_csv_name(view.filename)
    folder = SAMPLES.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    target = (folder / name).resolve()
    if target.parent != folder:
        raise HTTPException(status_code=400, detail="rejected file name")
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["code", "sentence", "http_status", "log_field", "retry", "amount_limit"])
    writer.writerow(
        [
            view.code,
            view.sentence,
            view.http_status,
            view.log_field,
            view.retry,
            f"{view.amount_limit:.2f}",
        ]
    )
    text = buffer.getvalue()
    assert_no_pan(name, text)
    target.write_text(text, encoding="utf-8", newline="\n")
    return name


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


def rule_slug(code: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in code).strip("-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned[:40] or "rule"


def write_rule_markdown(doc_id: int, view: RuleView) -> str:
    folder = (SAMPLES / "rules").resolve()
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{doc_id:04d}-{rule_slug(view.code)}.md"
    target = (folder / name).resolve()
    if target.parent != folder:
        raise HTTPException(status_code=400, detail="rejected file name")
    text = "\n".join(
        [
            f"# {view.code}",
            "",
            f"Customer sentence: {view.sentence}",
            f"HTTP status: {view.http_status}",
            f"Log field: {view.log_field}",
            f"Retry: {view.retry}",
            "",
        ]
    )
    assert_no_pan(name, text)
    target.write_text(text, encoding="utf-8", newline="\n")
    return f"rules/{name}"


def remove_rule_markdown(filename: str) -> None:
    if not filename.startswith("rules/") or ".." in filename:
        return
    folder = (SAMPLES / "rules").resolve()
    target = (SAMPLES / filename).resolve()
    if target.parent == folder and target.is_file():
        target.unlink()


def rule_document_from_row(row) -> RuleDocument:
    return RuleDocument(
        id=row[0],
        filename=row[1],
        code=row[2],
        sentence=row[3],
        http_status=row[4],
        log_field=row[5],
        retry=row[6],
        amount_limit=float(row[7] if row[7] is not None else LIMIT),
        active=bool(row[8]),
        created_at=row[9],
    )


def mirror_active_rule(view: RuleView) -> None:
    save_institution_rule(view)


def clear_active_rule() -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("DELETE FROM institution_rule WHERE id = 1")


def seed_rule_documents() -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        count = conn.execute("SELECT COUNT(*) FROM rule_document").fetchone()[0]
        if count:
            return
        found = conn.execute(
            """
            SELECT filename, code, sentence, http_status, log_field, retry, amount_limit
            FROM institution_rule
            WHERE id = 1
            """
        ).fetchone()
        if found is None:
            return
        inserted = conn.execute(
            """
            INSERT INTO rule_document
                (filename, code, sentence, http_status, log_field, retry, amount_limit, active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, true)
            RETURNING id
            """,
            found,
        ).fetchone()
        doc_id = inserted[0]
    view = RuleView(
        filename=found[0],
        code=found[1],
        sentence=found[2],
        http_status=found[3],
        log_field=found[4],
        retry=found[5],
        amount_limit=float(found[6] if found[6] is not None else LIMIT),
    )
    markdown = write_rule_markdown(doc_id, view)
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("UPDATE rule_document SET filename = %s WHERE id = %s", (markdown, doc_id))


def append_rule_document(view: RuleView) -> RuleDocument:
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("UPDATE rule_document SET active = false WHERE active")
        inserted = conn.execute(
            """
            INSERT INTO rule_document
                (filename, code, sentence, http_status, log_field, retry, amount_limit, active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, true)
            RETURNING id, created_at
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
        ).fetchone()
    markdown = write_rule_markdown(inserted[0], view)
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            """
            UPDATE rule_document
            SET filename = %s
            WHERE id = %s
            RETURNING id, filename, code, sentence, http_status, log_field, retry, amount_limit, active, created_at
            """,
            (markdown, inserted[0]),
        ).fetchone()
    mirror_active_rule(view)
    return rule_document_from_row(row)


def list_rule_documents() -> list[RuleDocument]:
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute(
            """
            SELECT id, filename, code, sentence, http_status, log_field, retry, amount_limit, active, created_at
            FROM rule_document
            ORDER BY id DESC
            """
        ).fetchall()
    return [rule_document_from_row(row) for row in rows]


def activate_rule_document(doc_id: int) -> RuleDocument:
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("UPDATE rule_document SET active = false WHERE active")
        row = conn.execute(
            """
            UPDATE rule_document
            SET active = true
            WHERE id = %s
            RETURNING id, filename, code, sentence, http_status, log_field, retry, amount_limit, active, created_at
            """,
            (doc_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="no institution rule")
    document = rule_document_from_row(row)
    mirror_active_rule(
        RuleView(
            filename=document.filename,
            code=document.code,
            sentence=document.sentence,
            http_status=document.http_status,
            log_field=document.log_field,
            retry=document.retry,
            amount_limit=document.amount_limit,
        )
    )
    return document


def update_rule_document(doc_id: int, edit: RuleDocumentEdit) -> RuleDocument:
    assert_no_pan(edit.code, edit.sentence, edit.log_field, str(edit.http_status))
    if not edit.code.strip() or not edit.sentence.strip():
        raise HTTPException(status_code=400, detail="rule file has no sentence")
    if not 100 <= edit.http_status <= 599:
        raise HTTPException(status_code=400, detail="rejected status")
    with psycopg.connect(DATABASE_URL) as conn:
        current = conn.execute(
            "SELECT filename, active, amount_limit FROM rule_document WHERE id = %s",
            (doc_id,),
        ).fetchone()
    if current is None:
        raise HTTPException(status_code=404, detail="no institution rule")
    view = RuleView(
        filename=current[0],
        code=edit.code.strip()[:80],
        sentence=edit.sentence.strip()[:400],
        http_status=edit.http_status,
        log_field=(edit.log_field or "card").strip()[:80] or "card",
        retry=edit.retry,
        amount_limit=float(current[2] if current[2] is not None else LIMIT),
    )
    markdown = write_rule_markdown(doc_id, view)
    view.filename = markdown
    if current[0] != markdown:
        remove_rule_markdown(current[0])
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            """
            UPDATE rule_document
            SET filename = %s, code = %s, sentence = %s, http_status = %s,
                log_field = %s, retry = %s, amount_limit = %s
            WHERE id = %s
            RETURNING id, filename, code, sentence, http_status, log_field, retry, amount_limit, active, created_at
            """,
            (
                markdown,
                view.code,
                view.sentence,
                view.http_status,
                view.log_field,
                view.retry,
                view.amount_limit,
                doc_id,
            ),
        ).fetchone()
    document = rule_document_from_row(row)
    if current[1]:
        mirror_active_rule(view)
    return document


def delete_rule_document(doc_id: int) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "SELECT filename, active FROM rule_document WHERE id = %s",
            (doc_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="no institution rule")
        conn.execute("DELETE FROM rule_document WHERE id = %s", (doc_id,))
        nxt = None
        if row[1]:
            nxt = conn.execute(
                """
                SELECT id, filename, code, sentence, http_status, log_field, retry, amount_limit, active, created_at
                FROM rule_document
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            if nxt is not None:
                conn.execute("UPDATE rule_document SET active = true WHERE id = %s", (nxt[0],))
                nxt = conn.execute(
                    """
                    SELECT id, filename, code, sentence, http_status, log_field, retry, amount_limit, active, created_at
                    FROM rule_document
                    WHERE id = %s
                    """,
                    (nxt[0],),
                ).fetchone()
    remove_rule_markdown(row[0])
    if not row[1]:
        return
    if nxt is None:
        clear_active_rule()
        return
    document = rule_document_from_row(nxt)
    mirror_active_rule(
        RuleView(
            filename=document.filename,
            code=document.code,
            sentence=document.sentence,
            http_status=document.http_status,
            log_field=document.log_field,
            retry=document.retry,
            amount_limit=document.amount_limit,
        )
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
    ceiling = read_amount_ceiling()
    if found is None:
        return RuleView(
            filename="",
            code="",
            sentence="",
            http_status=400,
            log_field="amount",
            retry="not_retryable",
            amount_limit=ceiling,
        )
    found.amount_limit = ceiling
    return found


@app.post("/rules", status_code=201, summary="Set the institution rule from a text file")
def write_rule(body: RuleFile) -> RuleDocument:
    if len(body.text) > 20000:
        raise HTTPException(status_code=400, detail="file too large")
    assert_no_pan(body.filename, body.text)
    parsed = parse_institution_rule(body.text)
    assert_no_pan(parsed["code"], parsed["sentence"], parsed["log_field"], str(parsed["http_status"]))
    view = RuleView(filename=bare_name(body.filename), **parsed)
    view.amount_limit = read_amount_ceiling()
    return append_rule_document(view)


@app.put("/rules/limit", summary="Set the payment amount ceiling")
def write_amount_ceiling(body: AmountLimitUpdate) -> RuleView:
    return set_amount_ceiling(body.amount_limit)


@app.get("/rules/documents", summary="Read saved institution rule documents")
def read_rule_documents() -> list[RuleDocument]:
    return list_rule_documents()


@app.post("/rules/documents/{doc_id}/use", summary="Reference one saved institution rule")
def use_saved_rule(doc_id: int) -> RuleDocument:
    return activate_rule_document(doc_id)


@app.delete("/rules/documents/{doc_id}", status_code=204, summary="Delete one saved institution rule")
def remove_saved_rule(doc_id: int) -> None:
    delete_rule_document(doc_id)


@app.put("/rules/documents/{doc_id}", summary="Edit one saved institution rule")
def edit_saved_rule(doc_id: int, body: RuleDocumentEdit) -> RuleDocument:
    return update_rule_document(doc_id, body)


@app.post("/authorizations", summary="Request authorization")
def authorize(body: AuthorizationRequest, request: Request) -> AuthorizationResponse:
    pan = digits(body.card)
    rule = read_institution_rule()
    limit = read_amount_ceiling()
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
    trace_id = getattr(request.state, "trace_id", "") or current_trace_id()
    save_log(row, mask_pan(pan), trace_id)
    return row


@app.get("/authorizations/latest", summary="Read the latest transaction receipt")
def latest_authorization() -> Receipt:
    with psycopg.connect(DATABASE_URL) as conn:
        found = conn.execute(
            """
            SELECT stop_step, http_status, amount, masked_card, trace_id, created_at, sentence, log_field, retry
            FROM authorization_log
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if found is None:
        raise HTTPException(status_code=404, detail="no authorization")
    return Receipt(
        status="SUCCESS" if found[0] is None else "DECLINED",
        http_status=found[1],
        amount=found[2],
        masked_card=found[3] or "",
        trace_id=found[4] or "",
        created_at=found[5],
        sentence=found[6] or "",
        log_field=found[7] or "",
        retry=found[8] or "",
    )
