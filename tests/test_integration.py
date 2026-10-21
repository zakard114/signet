import os

import psycopg
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://signet:signet@127.0.0.1:5433/signet",
)

from app import main


@pytest.fixture()
def client():
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_tables():
    with psycopg.connect(main.DATABASE_URL) as conn:
        conn.execute("TRUNCATE authorization_log RESTART IDENTITY")
        conn.execute("TRUNCATE plate")
    yield


def test_approve_once(client):
    response = client.post(
        "/authorizations",
        json={"amount": 128, "card": "4242424242424242"},
    )
    body = response.json()
    assert response.status_code == 200
    assert body["sentence"] == "Payment completed."
    assert body["amount"] == 128
    assert body.get("stop_step") is None
    assert "4242424242424242" not in response.text
    with psycopg.connect(main.DATABASE_URL) as conn:
        row = conn.execute(
            "SELECT sentence, amount FROM authorization_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert row == ("Payment completed.", 128.0)


def test_decline_once(client):
    plate = {
        "name": "declined",
        "user_facing_message": "This card was declined.",
        "http_status": 400,
        "log_fields": "amount",
        "retry_allowed": "not_retryable",
    }
    saved = client.post("/plates", json=plate)
    assert saved.status_code == 201
    response = client.post(
        "/authorizations",
        json={"amount": 128, "card": "4000000000000002"},
    )
    body = response.json()
    assert response.status_code == 200
    assert body["stop_step"] == 5
    assert body["sentence"] == "This card was declined."
    assert "4000000000000002" not in response.text
