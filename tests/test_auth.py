import json

from fastapi.testclient import TestClient
from forgevault.main import app

client = TestClient(app, raise_server_exceptions=False)
PATH = "/api/v1/runtime/config"
WRITE = "/api/v1/source-folders"
KEY = "a" * 32


def test_api_denies_anonymous_read_and_write(monkeypatch):
    monkeypatch.delenv("FORGEVAULT_AUTH_PRINCIPALS", raising=False)
    assert client.get(PATH).status_code == 401
    assert client.post(WRITE, json={"actor": "admin"}).status_code == 401


def test_rejects_forged_actor_even_with_valid_editor_token(monkeypatch):
    monkeypatch.setenv("FORGEVAULT_AUTH_PRINCIPALS", json.dumps({KEY: {"actor": "alice", "role": "editor"}}))
    headers = {"Authorization": "Bearer " + KEY}
    assert client.get(PATH, headers=headers).status_code == 200
    response = client.post(WRITE, json={"actor": "bob"}, headers=headers)
    assert response.status_code == 403
    assert "identity" in response.json()["detail"].lower()


def test_reader_cannot_mutate_and_editor_cannot_approve(monkeypatch):
    monkeypatch.setenv("FORGEVAULT_AUTH_PRINCIPALS", json.dumps({KEY: {"actor": "alice", "role": "reader"}}))
    headers = {"Authorization": "Bearer " + KEY}
    assert client.post(WRITE, json={"actor": "alice"}, headers=headers).status_code == 403
    monkeypatch.setenv("FORGEVAULT_AUTH_PRINCIPALS", json.dumps({KEY: {"actor": "alice", "role": "editor"}}))
    assert client.post("/api/v1/reviews/00000000-0000-0000-0000-000000000001/decision",
                       json={"reviewer": "alice", "decision": "approve"}, headers=headers).status_code == 403


def test_short_token_is_invalid(monkeypatch):
    monkeypatch.setenv("FORGEVAULT_AUTH_PRINCIPALS", json.dumps({"123": {"actor": "alice", "role": "admin"}}))
    assert client.get(PATH, headers={"Authorization": "Bearer 123"}).status_code == 401
