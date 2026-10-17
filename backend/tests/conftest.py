import copy
import os

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql

from db import run_migrations
from helpers import FAKE_RECEIPT, TEST_URL

TEST_DB_NAME = "splitty_test"
ADMIN_URL = os.environ.get(
    "ADMIN_DATABASE_URL", "postgresql://splitty:splitty@127.0.0.1:5432/postgres"
)


@pytest.fixture(scope="session", autouse=True)
def test_database():
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        exists = conn.execute(
            "select 1 from pg_database where datname = %s", (TEST_DB_NAME,)
        ).fetchone()
        if not exists:
            conn.execute(sql.SQL("create database {}").format(sql.Identifier(TEST_DB_NAME)))
    run_migrations(TEST_URL)
    os.environ["DATABASE_URL"] = TEST_URL
    yield


@pytest.fixture
def clean_db(test_database):
    with psycopg.connect(TEST_URL, autocommit=True) as conn:
        conn.execute("truncate sessions cascade")
    yield TEST_URL


@pytest.fixture
def client(clean_db):
    # Imported here so DATABASE_URL is set before the app starts.
    from main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def fake_ocr(monkeypatch):
    """Replace the OCR call. Returns the list of calls, so tests can check what was sent."""
    calls = []

    def fake_parse(ocr_url, filename, content_type, data, note):
        calls.append({"note": note, "size": len(data)})
        return copy.deepcopy(FAKE_RECEIPT)

    monkeypatch.setattr("main.parse_receipt", fake_parse)
    return calls
