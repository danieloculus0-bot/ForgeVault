"""Synthetic token-auth regression; no production tokens or company identities."""
import hashlib
import json
import os
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from forgevault.api.auth import authorize_api_request

app = FastAPI()
app.middleware("http")(authorize_api_request)

@app.get("/api/v1/__auth_probe__")
def probe():
    return {"ok": True}


def test_digest_config_allows_only_the_right_token():
    token = "synthetic-test-token-0123456789abcdef"
    digest = hashlib.sha256(token.encode()).hexdigest()
    config = json.dumps({digest: {"actor": "sample-editor", "role": "editor"}})
    with patch.dict(os.environ, {
        "FORGEVAULT_AUTH_PRINCIPALS": "",
        "FORGEVAULT_AUTH_TOKEN_HASHES": config,
    }):
        with TestClient(app) as client:
            # A synthetic probe exercises middleware without touching any production database.
            assert client.get("/api/v1/__auth_probe__",
                              headers={"Authorization": "Bearer " + token}).status_code == 200
            assert client.get("/api/v1/__auth_probe__",
                              headers={"Authorization": "Bearer bad-token"}).status_code == 401


def test_digest_config_fails_closed_on_invalid_schema_or_bad_role():
    token = "synthetic-test-token-0123456789abcdef"
    digest = hashlib.sha256(token.encode()).hexdigest()
    for value in ("not-json", json.dumps({digest: {"actor": "tester", "role": "superuser"}}),
                  json.dumps({"bad-hash": {"actor": "tester", "role": "admin"}})):
        with patch.dict(os.environ, {
            "FORGEVAULT_AUTH_PRINCIPALS": "",
            "FORGEVAULT_AUTH_TOKEN_HASHES": value,
        }):
            with TestClient(app) as client:
                assert client.get("/api/v1/__auth_probe__",
                                  headers={"Authorization": "Bearer " + token}).status_code == 401


def test_digest_config_keeps_role_enforcement():
    token = "synthetic-test-token-0123456789abcdef"
    digest = hashlib.sha256(token.encode()).hexdigest()
    config = json.dumps({digest: {"actor": "synthetic-reader", "role": "reader"}})
    with patch.dict(os.environ, {
        "FORGEVAULT_AUTH_PRINCIPALS": "",
        "FORGEVAULT_AUTH_TOKEN_HASHES": config,
    }):
        with TestClient(app) as client:
            assert client.post("/api/v1/__auth_probe__", json={},
                               headers={"Authorization": "Bearer " + token}).status_code == 403
