"""Synthetic token-auth regression; no production tokens or company identities."""
import hashlib
import json
import os
from unittest.mock import patch

from fastapi.testclient import TestClient
from forgevault.main import app


def test_digest_config_allows_only_the_right_token():
    token = "synthetic-test-token-0123456789abcdef"
    digest = hashlib.sha256(token.encode()).hexdigest()
    config = json.dumps({digest: {"actor": "sample-editor", "role": "editor"}})
    with patch.dict(os.environ, {
        "FORGEVAULT_AUTH_PRINCIPALS": "",
        "FORGEVAULT_AUTH_TOKEN_HASHES": config,
    }):
        with TestClient(app) as client:
            # A non-existent API route returns 404 only once middleware permits access.
            assert client.get("/api/v1/__auth_probe__",
                              headers={"Authorization": "Bearer " + token}).status_code == 404
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
