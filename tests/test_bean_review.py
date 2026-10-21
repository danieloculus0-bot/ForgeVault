"""Real source-grounded PDM review and isolated BEAN Core continuity tests."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from forgevault.config import settings
from forgevault.database import Base
from forgevault.models import FileObject, FileVersion, LifecycleState, Record
from forgevault.services.bean_review import collect_record_health, run_bean_review
from forgevault.storage.local import LocalVaultStorage


@pytest.fixture
def fixture_record(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "local_vault_root", str(tmp_path / "vault"))
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        state = LifecycleState(name="Draft", is_release_state=False, sort_order=1)
        record = Record(internal_record_id="FV-TEST-001",
                        customer_part_number="UNMAPPED",
                        customer_revision="A", internal_revision="001",
                        lifecycle_state=state)
        db.add_all([state, record])
        db.flush()
        yield db, record, tmp_path
    engine.dispose()


def test_missing_version_and_unmapped_identity_are_visible(fixture_record):
    db, record, _ = fixture_record
    health = collect_record_health(db, record)
    assert health["issues"] == ["missing_file_version", "unmapped_customer_identity"]
    assert health["result"] == "needs_attention"
    assert health["version_sha256"] is None
    assert "forgevault-record:" in health["evidence_refs"][0]


def test_verified_object_and_release_package_gap(fixture_record):
    db, record, tmp = fixture_record
    storage = LocalVaultStorage(settings.local_vault_root)
    digest, location, size = storage.put(b"example test-only engineering file")
    obj = FileObject(sha256=digest, storage_uri=location, byte_size=size,
                     storage_adapter="local")
    version = FileVersion(record=record, file_object=obj, filename="test.step",
                          original_source_path=str(tmp / "test.step"),
                          version_number=1, customer_revision="A", internal_revision="001",
                          created_by="fixture")
    db.add(version)
    db.flush()
    result = collect_record_health(db, record)
    assert result["version_sha256"] == digest
    assert "vault-object:sha256:" + digest in result["evidence_refs"]
    assert "stored_object_integrity_failed" not in result["issues"]
    record.customer_part_number = "CUST-42"
    record.lifecycle_state.name = "Released"
    db.flush()
    result = collect_record_health(db, record)
    assert "released_without_matching_version_package" in result["issues"]
    # A corrupt content-addressed object is flagged rather than certified.
    storage._object_path(digest).write_bytes(b"tampered")
    result = collect_record_health(db, record)
    assert "stored_object_integrity_failed" in result["issues"]
    assert "vault-object:sha256:" + digest not in result["evidence_refs"]


def test_real_bean_core_remembers_prior_review(fixture_record, monkeypatch):
    core_path = os.environ.get("FORGEVAULT_BEAN_CORE_ROOT")
    if not core_path:
        pytest.skip("Real BEAN Core checkout required for this integration test")
    db, record, tmp = fixture_record
    monkeypatch.setenv("FORGEVAULT_BEAN_MEMORY_PATH", str(tmp / "bean.sqlite3"))
    first = run_bean_review(collect_record_health(db, record))
    assert first["bean"]["source"] == "BEAN Core persistent memory"
    assert first["bean"]["memory_written"] is True
    assert first["bean"]["prior_reviews"] == 0
    assert first["read_only"] and not first["release_approved"]
    assert set(first["bean"]["new_issues"]) == set(first["issues"])
    second = run_bean_review(collect_record_health(db, record))
    assert second["bean"]["prior_reviews"] == 1
    assert set(second["bean"]["persistent_issues"]) == set(first["issues"])
    assert second["bean"]["bean_event_id"] > first["bean"]["bean_event_id"]
    record.customer_part_number = "CUST-42"
    db.flush()
    third = run_bean_review(collect_record_health(db, record))
    assert third["bean"]["prior_reviews"] == 2
    assert "unmapped_customer_identity" in third["bean"]["resolved_issues"]
    assert "unmapped_customer_identity" not in third["issues"]
    # The BEAN worker cannot mutate the PDM record, release state or file bytes.
    assert record.lifecycle_state.name == "Draft"
