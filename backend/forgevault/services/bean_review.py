"""Metadata-only PDM health review backed by the actual BEAN Core event memory.

This is review advice, not a lifecycle transition. Verification uses the real
vault object's checksum and the current database record. No CAD/PDF bytes,
customer names, file paths or operator identity are exported to BEAN.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Checkout, Dependency, FileVersion, Record, ReleasePackage, ReleasePackageItem
from ..storage.local import LocalVaultStorage
from ..workflow_model import ReviewRequest


def collect_record_health(session: Session, record: Record) -> dict:
    latest = session.scalar(
        select(FileVersion).where(FileVersion.record_id == record.id)
        .order_by(FileVersion.version_number.desc()).limit(1)
    )
    issues = []
    evidence = []
    if not latest:
        issues.append("missing_file_version")
    else:
        obj = latest.file_object
        if obj is None or obj.storage_adapter != "local":
            issues.append("unsupported_object_storage")
        else:
            try:
                content = LocalVaultStorage(settings.local_vault_root).get(obj.sha256)
                if len(content) != obj.byte_size:
                    issues.append("stored_object_size_mismatch")
                else:
                    evidence.append("vault-object:sha256:" + obj.sha256)
            except (OSError, ValueError):
                issues.append("stored_object_integrity_failed")
        if (record.customer_revision != latest.customer_revision
                or record.internal_revision != latest.internal_revision):
            issues.append("latest_version_revision_mismatch")
    if not record.customer_part_number or record.customer_part_number.upper().startswith("UNMAPPED"):
        issues.append("unmapped_customer_identity")
    unresolved = session.scalar(
        select(func.count()).select_from(Dependency).where(
            Dependency.source_record_id == record.id,
            Dependency.resolution_status != "resolved",
        )
    ) or 0
    if unresolved:
        issues.append("unresolved_dependencies")
    checkout = session.scalar(select(Checkout.id).where(
        Checkout.record_id == record.id, Checkout.released_at.is_(None)
    ).limit(1))
    if checkout:
        issues.append("active_checkout")
    pending = session.scalar(select(func.count()).select_from(ReviewRequest).where(
        ReviewRequest.record_id == record.id, ReviewRequest.status == "pending"
    )) or 0
    if pending:
        issues.append("pending_review")
    state = record.lifecycle_state.name if record.lifecycle_state else "Unknown"
    if state == "Released":
        matched = None
        if latest:
            matched = session.scalar(
                select(ReleasePackageItem.id)
                .join(ReleasePackage, ReleasePackage.id == ReleasePackageItem.release_package_id)
                .where(
                    ReleasePackage.record_id == record.id,
                    ReleasePackage.customer_revision == latest.customer_revision,
                    ReleasePackage.internal_revision == latest.internal_revision,
                    ReleasePackageItem.file_version_id == latest.id,
                ).limit(1)
            )
        if not matched:
            issues.append("released_without_matching_version_package")
    evidence.append("forgevault-record:" + str(record.id))
    return {
        "record_key": hashlib.sha256(str(record.id).encode("utf-8")).hexdigest(),
        "version_sha256": latest.file_object.sha256 if latest and latest.file_object else None,
        "lifecycle": state,
        "issues": sorted(set(issues)),
        "evidence_refs": evidence,
        "version_number": latest.version_number if latest else None,
        "unresolved_dependencies": unresolved,
        "pending_reviews": pending,
        "result": "needs_attention" if issues else "no_detected_issues",
    }


def run_bean_review(snapshot: dict) -> dict:
    """Use a separate process because Core has process-global SQLite state."""
    path = os.environ.get("FORGEVAULT_BEAN_MEMORY_PATH")
    if not path:
        path = str(Path(settings.local_vault_root).resolve().parent / "forgevault-bean-memory.sqlite3")
    root = os.environ.get("FORGEVAULT_BEAN_CORE_ROOT")
    env = os.environ.copy()
    if root:
        source = Path(root).expanduser().resolve()
        if not (source / "bean" / "integration" / "reasoning_layer.py").is_file():
            raise RuntimeError("Configured BEAN Core checkout is missing or invalid")
        env["PYTHONPATH"] = str(source) + os.pathsep + env.get("PYTHONPATH", "")
    python = os.environ.get("FORGEVAULT_BEAN_PYTHON")
    if not python:
        if getattr(sys, "frozen", False):
            raise RuntimeError("Packaged ForgeVault requires FORGEVAULT_BEAN_PYTHON pointing to a Python interpreter with BEAN Core")
        python = sys.executable
    packet = {
        key: snapshot[key] for key in
        ("record_key", "version_sha256", "lifecycle", "issues", "evidence_refs")
    }
    packet["bean_memory_path"] = path
    try:
        proc = subprocess.run(
            [python, "-m", "forgevault.bean_review_worker"],
            input=json.dumps(packet), text=True, capture_output=True,
            env=env, timeout=20, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("BEAN Core worker could not complete the review") from exc
    if proc.returncode != 0:
        if "No module named 'bean'" in proc.stderr:
            raise RuntimeError("BEAN Core is not installed; configure FORGEVAULT_BEAN_CORE_ROOT")
        raise RuntimeError("BEAN Core review failed; see local ForgeVault logs")
    try:
        result = json.loads(proc.stdout)
    except ValueError as exc:
        raise RuntimeError("BEAN Core did not return a valid review receipt") from exc
    if not result.get("memory_written") or result.get("decision_authority") != "none":
        raise RuntimeError("BEAN Core did not confirm a read-only evidence receipt")
    return {**snapshot, "bean": result, "release_approved": False, "read_only": True}
