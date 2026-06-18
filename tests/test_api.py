"""Tests for the REST API."""

import os
import asyncio
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    """Set up a temp database and initialize it."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("MALRT_DB_PATH", db_path)
    # Initialize the database synchronously
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS submissions (
            id TEXT PRIMARY KEY,
            indicator_type TEXT NOT NULL,
            indicator_value TEXT NOT NULL,
            raw_value TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS submission_results (
            id TEXT PRIMARY KEY,
            submission_id TEXT NOT NULL REFERENCES submissions(id),
            provider TEXT NOT NULL,
            status TEXT NOT NULL,
            submitted_at TEXT,
            response_data TEXT,
            error TEXT
        );
    """)
    conn.close()
    yield db_path


@pytest.fixture
def client(setup_db):
    """Create a test client."""
    from malrt.api.app import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_health(client):
    """App starts and serves the dashboard."""
    resp = client.get("/")
    assert resp.status_code == 200


def test_list_submissions_empty(client):
    resp = client.get("/api/submissions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_submit_indicator(client):
    resp = client.post("/api/submit", json={"indicator": "https://evil.com/phish"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["indicator"]["type"] == "url"
    assert data["indicator"]["value"] == "https://evil.com/phish"


def test_submit_and_list(client):
    client.post("/api/submit", json={"indicator": "evil.com"})
    resp = client.get("/api/submissions")
    subs = resp.json()
    assert len(subs) == 1
    assert subs[0]["indicator"]["type"] == "domain"


def test_get_submission_detail(client):
    post_resp = client.post("/api/submit", json={"indicator": "1.2.3.4"})
    sub_id = post_resp.json()["id"]

    resp = client.get(f"/api/submissions/{sub_id}")
    assert resp.status_code == 200
    assert resp.json()["indicator"]["value"] == "1.2.3.4"


def test_get_submission_not_found(client):
    resp = client.get("/api/submissions/nonexistent")
    assert resp.status_code == 404


def test_providers_endpoint(client):
    resp = client.get("/api/providers")
    assert resp.status_code == 200
    providers = resp.json()
    assert any(p["name"] == "virustotal" for p in providers)


def test_submit_with_notes(client):
    resp = client.post("/api/submit", json={
        "indicator": "evil.com",
        "notes": "Found in phishing email to accounting dept",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["notes"] == "Found in phishing email to accounting dept"


def test_update_notes(client):
    post_resp = client.post("/api/submit", json={"indicator": "bad.com"})
    sub_id = post_resp.json()["id"]

    # Update notes
    patch_resp = client.patch(f"/api/submissions/{sub_id}/notes", json={
        "notes": "Confirmed malicious via manual analysis"
    })
    assert patch_resp.status_code == 200
    assert patch_resp.json()["ok"] is True

    # Verify notes persisted
    get_resp = client.get(f"/api/submissions/{sub_id}")
    assert get_resp.json()["notes"] == "Confirmed malicious via manual analysis"
