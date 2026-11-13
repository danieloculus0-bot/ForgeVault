import base64
import os
from pathlib import Path

os.environ["FORGEVAULT_DATABASE_URL"] = "sqlite+pysqlite:///./test_forgevault.db"
os.environ["FORGEVAULT_LOCAL_VAULT_ROOT"] = "./test-vault"
os.environ["FORGEVAULT_JOBBOSS2_OUTBOX_ROOT"] = "./test-jobboss-outbox"

from fastapi.testclient import TestClient
from sqlalchemy import select

from forgevault.database import Base, SessionLocal, engine
from forgevault.main import app
from forgevault.models import Dependency, IntegrationEvent, MetadataFieldDefinition, PluginExecution, ReleasePackage


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
    client = TestClient(app)
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
    client = TestClient(app)
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
    client = TestClient(app)
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

    client = TestClient(app)
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
