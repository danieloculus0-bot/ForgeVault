import base64
import os
from pathlib import Path

os.environ["FORGEVAULT_DATABASE_URL"] = "sqlite+pysqlite:///./test_forgevault.db"
os.environ["FORGEVAULT_LOCAL_VAULT_ROOT"] = "./test-vault"
os.environ["FORGEVAULT_JOBBOSS2_OUTBOX_ROOT"] = "./test-jobboss-outbox"

import hashlib
import json

# Credential fixtures for legacy functional tests. Security tests below deliberately
# use the raw TestClient to verify that forged/anonymous requests are denied.
AUTH_TOKENS = {user: "fixture-token-" + user for user in ("alice", "bob", "carol", "desktop", "system")}
os.environ["FORGEVAULT_API_TOKENS_JSON"] = json.dumps({
    hashlib.sha256(token.encode()).hexdigest(): {"user": user, "role": "admin"}
    for user, token in AUTH_TOKENS.items()
})

from fastapi.testclient import TestClient
from sqlalchemy import select

from forgevault.database import Base, SessionLocal, engine
from forgevault.main import app
from forgevault.models import Dependency, IntegrationEvent, MetadataFieldDefinition, PluginExecution, ReleasePackage


class AuthenticatedTestClient(TestClient):
    def request(self, method, url, **kwargs):
        payload = kwargs.get("json") or {}
        actor = next((payload[k] for k in ("actor", "reviewer", "submitted_by") if k in payload), "alice")
        if actor not in AUTH_TOKENS:
            raise AssertionError(f"Unknown legacy test actor: {actor}")
        headers = dict(kwargs.pop("headers", {}) or {})
        headers["Authorization"] = "Bearer " + AUTH_TOKENS[actor]
        return super().request(method, url, headers=headers, **kwargs)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_function():
    Base.metadata.drop_all(bind=engine)


def ingest_payload(filename="bracket.step", content=b"ISO-10303-21; FILE_NAME='child-bearing.step';", **overrides):
    payload = {
        "filename": filename,
        "original_source_path": f"legacy/junk drawer/customer A/{filename}",
        "content_base64": base64.b64encode(content).decode(),
        "customer_part_number": "CUST-42",
        "customer_revision": "A",
        "internal_revision": "001",
        "metadata": {"material": "6061-T6", "source": "staging"},
        "actor": "alice",
        "mime_type": "application/step",
    }
    payload.update(overrides)
    return payload


def test_ingest_search_checkout_and_release_flow():
    client = AuthenticatedTestClient(app)
    ingest = client.post("/api/v1/ingest", json=ingest_payload(content=b"plain arbitrary bytes"))
    assert ingest.status_code == 201, ingest.text
    assert ingest.json()["version_number"] == 1
    assert ingest.json()["version_metadata"]["file"]["classification"] == "cad"

    search = client.get("/api/v1/search", params={"q": "CUST-42"})
    assert search.status_code == 200
    record = search.json()[0]["record"]
    assert record["customer_part_number"] == "CUST-42"
    assert record["internal_revision"] == "001"

    checkout = client.post(f"/api/v1/records/{record['internal_record_id']}/checkout", json={"actor": "bob"})
    assert checkout.status_code == 201
    second_checkout = client.post(f"/api/v1/records/{record['internal_record_id']}/checkout", json={"actor": "carol"})
    assert second_checkout.status_code == 409

    blocked_version = client.post("/api/v1/ingest", json=ingest_payload(content=b"new bytes", internal_revision="001", actor="alice"))
    assert blocked_version.status_code == 422
    second_version = client.post("/api/v1/ingest", json=ingest_payload(content=b"new bytes", internal_revision="001", actor="bob"))
    assert second_version.status_code == 201, second_version.text
    assert second_version.json()["version_number"] == 2

    review = client.post(f"/api/v1/records/{record['internal_record_id']}/lifecycle", json={"to_state": "Review", "actor": "alice"})
    assert review.status_code == 200
    released = client.post(f"/api/v1/records/{record['internal_record_id']}/lifecycle", json={"to_state": "Released", "actor": "alice"})
    assert released.status_code == 200
    assert released.json()["release_package_id"]

    with SessionLocal() as session:
        package = session.scalar(select(ReleasePackage))
        assert package is not None
        assert len(package.manifest["file_versions"]) == 2
        assert all(item["sha256"] for item in package.manifest["file_versions"])
        assert session.scalar(select(MetadataFieldDefinition).where(MetadataFieldDefinition.field_key == "material")) is not None
        plugin_names = {name for (name,) in session.execute(select(PluginExecution.plugin_name)).all()}
        assert "builtin.generic_file_parser" in plugin_names
        assert "builtin.standard_release_package_generator" in plugin_names

    versions = client.get(f"/api/v1/records/{record['internal_record_id']}/versions")
    assert versions.status_code == 200
    assert [version["version_number"] for version in versions.json()] == [2, 1]

    export = client.post(f"/api/v1/integrations/jobboss2/release-packages/{released.json()['release_package_id']}/export", json={"actor": "alice"})
    assert export.status_code == 200, export.text
    assert export.json()["external_system"] == "jobboss2"
    assert Path(export.json()["response"]["path"]).exists()
    with SessionLocal() as session:
        assert session.scalar(select(IntegrationEvent).where(IntegrationEvent.external_system == "jobboss2")) is not None


def test_unresolved_dependency_blocks_release():
    client = AuthenticatedTestClient(app)
    ingest = client.post("/api/v1/ingest", json=ingest_payload())
    assert ingest.status_code == 201, ingest.text

    search = client.get("/api/v1/search", params={"q": "CUST-42"})
    record = search.json()[0]["record"]

    with SessionLocal() as session:
        dependencies = session.scalars(select(Dependency)).all()
        assert len(dependencies) == 1
        assert dependencies[0].resolution_status == "unresolved"

    review = client.post(f"/api/v1/records/{record['internal_record_id']}/lifecycle", json={"to_state": "Review", "actor": "alice"})
    assert review.status_code == 200
    released = client.post(f"/api/v1/records/{record['internal_record_id']}/lifecycle", json={"to_state": "Released", "actor": "alice"})
    assert released.status_code == 409
    assert "unresolved dependencies" in released.json()["detail"]


def test_naming_plugin_can_derive_customer_identity_for_arbitrary_document():
    client = AuthenticatedTestClient(app)
    payload = ingest_payload(
        filename="ACME-900_REVb.pdf",
        content=b"%PDF-1.7\nwork instruction",
        customer_part_number=None,
        customer_revision=None,
        internal_revision="DOC-001",
        mime_type="application/pdf",
    )
    ingest = client.post("/api/v1/ingest", json=payload)
    assert ingest.status_code == 201, ingest.text

    search = client.get("/api/v1/search", params={"q": "ACME-900"})
    assert search.status_code == 200
    record = search.json()[0]["record"]
    assert record["customer_part_number"] == "ACME-900"
    assert record["customer_revision"] == "B"
    assert search.json()[0]["latest_version"]["version_metadata"]["document"]["extension"] == ".pdf"


def test_folder_ingest_indexes_arbitrary_files_with_unmapped_identity(tmp_path):
    root = tmp_path / "legacy-job"
    root.mkdir()
    (root / "random notes.txt").write_text("operator note", encoding="utf-8")
    (root / "plate.dxf").write_text("0\nSECTION", encoding="utf-8")

    client = AuthenticatedTestClient(app)
    result = client.post(
        "/api/v1/ingest-folder",
        json={"folder_path": str(root), "actor": "desktop", "internal_revision": "001", "recursive": True},
    )
    assert result.status_code == 200, result.text
    assert result.json()["scanned"] == 2
    assert result.json()["ingested"] == 2

    search = client.get("/api/v1/search", params={"q": "UNMAPPED"})
    assert search.status_code == 200
    assert len(search.json()) == 2
    assert all(item["record"]["record_metadata"]["identity_status"] == "unmapped_requires_review" for item in search.json())


def test_security_rejects_anonymous_write_and_read():
    client = TestClient(app)
    assert client.get("/api/v1/search", params={"q": "x"}).status_code == 401
    assert client.post("/api/v1/ingest", json=ingest_payload()).status_code == 401
    with SessionLocal() as session:
        assert session.scalar(select(Record)) is None


def test_security_rejects_bearer_actor_spoof_and_missing_role():
    client = TestClient(app)
    forged = client.post(
        "/api/v1/ingest", json=ingest_payload(actor="bob"),
        headers={"Authorization": "Bearer " + AUTH_TOKENS["alice"]},
    )
    assert forged.status_code == 403
    assert "identity" in forged.json()["detail"].lower()
    with SessionLocal() as session:
        assert session.scalar(select(Record)) is None


def test_security_rejects_unauthorized_write_by_viewer_and_reviewer():
    tokens = json.loads(os.environ["FORGEVAULT_API_TOKENS_JSON"])
    tokens[hashlib.sha256(b"viewer-key").hexdigest()] = {"user": "viewonly", "role": "viewer"}
    tokens[hashlib.sha256(b"reviewer-key").hexdigest()] = {"user": "checker", "role": "reviewer"}
    original = os.environ["FORGEVAULT_API_TOKENS_JSON"]
    os.environ["FORGEVAULT_API_TOKENS_JSON"] = json.dumps(tokens)
    try:
        client = TestClient(app)
        assert client.get("/api/v1/search", params={"q": "x"},
                          headers={"Authorization": "Bearer viewer-key"}).status_code == 200
        assert client.post("/api/v1/records", json={"actor": "viewonly"},
                           headers={"Authorization": "Bearer viewer-key"}).status_code == 403
        assert client.post("/api/v1/ingest", json={"actor": "checker"},
                           headers={"Authorization": "Bearer reviewer-key"}).status_code == 403
        assert client.post("/api/v1/reviews/x/decision", json={"reviewer": "alice"},
                           headers={"Authorization": "Bearer reviewer-key"}).status_code == 403
    finally:
        os.environ["FORGEVAULT_API_TOKENS_JSON"] = original
