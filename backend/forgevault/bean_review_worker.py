"""Isolated real BEAN Core memory worker for ForgeVault record reviews.

Reads one strictly metadata-only packet on stdin. BEAN Core owns the persistent
memory and event journal; this worker does not import a mock adapter, modify
PDM records, or interpret a journal entry as an engineering approval.
"""
from __future__ import annotations

import json
import sys


def run(packet: dict) -> dict:
    from bean.integration.reasoning_layer import BeanReasoningLayer
    from bean.memory.event_logger import EventType, Source

    key = packet["record_key"]
    current = set(packet["issues"])
    with BeanReasoningLayer(packet["bean_memory_path"]) as bean:
        db = bean.store._conn()
        historical = []
        for row in db.execute(
            "SELECT data FROM events WHERE event_type='observation' "
            "AND subtype='forgevault_record_review' ORDER BY id DESC LIMIT 1000"
        ):
            try:
                item = json.loads(row[0])
            except (ValueError, TypeError):
                continue
            if item.get("record_key") == key:
                historical.append(item)
        prior = historical[0] if historical else None
        prior_issues = set(prior["issues"]) if prior else set()
        recorded = {
            "record_key": key,
            "version_sha256": packet["version_sha256"],
            "issues": sorted(current),
            "lifecycle": packet["lifecycle"],
            "evidence_refs": packet["evidence_refs"],
            "source_system": "ForgeVault",
        }
        event_id = bean.record_event(
            "ForgeVault source-grounded record health review",
            event_type=EventType.OBSERVATION,
            source=Source.SYSTEM,
            subtype="forgevault_record_review",
            data=recorded,
        )
        return {
            "source": "BEAN Core persistent memory",
            "memory_written": True,
            "bean_event_id": event_id,
            "prior_reviews": len(historical),
            "persistent_issues": sorted(current & prior_issues),
            "new_issues": sorted(current - prior_issues),
            "resolved_issues": sorted(prior_issues - current),
            "decision_authority": "none",
        }


def main() -> None:
    packet = json.load(sys.stdin)
    result = run(packet)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
