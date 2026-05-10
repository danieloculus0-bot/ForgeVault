from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import PluginExecution
from ..plugins import default_registry


def merge_metadata(*parts: dict) -> dict:
    merged: dict = {}
    for part in parts:
        for key, value in (part or {}).items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = merge_metadata(merged[key], value)
            else:
                merged[key] = value
    return merged


def run_ingest_plugins(
    session: Session,
    *,
    filename: str,
    original_source_path: str,
    content: bytes,
    submitted_metadata: dict,
    entity_type: str,
    entity_id: str,
) -> dict:
    metadata = submitted_metadata.copy()
    dependencies: list[dict] = []
    executions: list[dict] = []

    for parser in default_registry.parser_plugins_for(filename):
        result = parser.parse(filename=filename, original_source_path=original_source_path, content=content)
        metadata = merge_metadata(metadata, result.metadata)
        dependencies.extend(result.dependencies)
        output = {"metadata": result.metadata, "dependencies": result.dependencies, "confidence": result.confidence}
        session.add(
            PluginExecution(
                plugin_name=result.plugin_name,
                plugin_kind="parser",
                entity_type=entity_type,
                entity_id=entity_id,
                input_summary={"filename": filename, "original_source_path": original_source_path, "byte_size": len(content)},
                output=output,
            )
        )
        executions.append({"plugin_name": result.plugin_name, "plugin_kind": "parser", **output})

    derived_identity: dict = {}
    for naming_plugin in default_registry.naming_plugins:
        candidate = naming_plugin.derive_identity(filename=filename, original_source_path=original_source_path, metadata=metadata)
        session.add(
            PluginExecution(
                plugin_name=naming_plugin.name,
                plugin_kind="naming",
                entity_type=entity_type,
                entity_id=entity_id,
                input_summary={"filename": filename, "original_source_path": original_source_path},
                output=candidate,
            )
        )
        executions.append({"plugin_name": naming_plugin.name, "plugin_kind": "naming", "metadata": candidate, "dependencies": [], "confidence": candidate.get("confidence", 0) if candidate else 0})
        if candidate and not derived_identity:
            derived_identity = candidate

    metadata["plugin_executions"] = executions
    return {"metadata": metadata, "dependencies": dependencies, "derived_identity": derived_identity}
