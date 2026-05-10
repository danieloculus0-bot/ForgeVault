from __future__ import annotations

import mimetypes
import re
from pathlib import PurePath

from .base import ParserResult, ReleasePackageResult

CAD_EXTENSIONS = {".sldprt", ".sldasm", ".step", ".stp", ".dxf", ".dwg", ".iges", ".igs"}
DOCUMENT_EXTENSIONS = {".pdf", ".txt", ".md", ".csv", ".doc", ".docx", ".xls", ".xlsx", ".png", ".jpg", ".jpeg"}


class GenericFileParser:
    name = "builtin.generic_file_parser"
    supported_extensions = set()

    def parse(self, *, filename: str, original_source_path: str, content: bytes) -> ParserResult:
        path = PurePath(original_source_path or filename)
        extension = path.suffix.lower()
        guessed_mime, _ = mimetypes.guess_type(filename)
        metadata = {
            "file": {
                "filename": filename,
                "extension": extension,
                "byte_size": len(content),
                "source_directory": str(path.parent) if str(path.parent) != "." else "",
                "mime_type_guess": guessed_mime or "application/octet-stream",
                "classification": "cad" if extension in CAD_EXTENSIONS else "document" if extension in DOCUMENT_EXTENSIONS else "arbitrary",
            }
        }
        return ParserResult(plugin_name=self.name, metadata=metadata, confidence=100)


class NeutralCadParser:
    name = "builtin.neutral_cad_parser"
    supported_extensions = CAD_EXTENSIONS

    def parse(self, *, filename: str, original_source_path: str, content: bytes) -> ParserResult:
        extension = PurePath(filename).suffix.lower()
        text = content[:200_000].decode("utf-8", errors="ignore")
        dependencies: list[dict] = []
        for match in re.finditer(r"(?:FILE_NAME|REFERENCE|XREF|DEPENDENCY)\s*[:=]\s*['\"]?([^'\"\r\n;]+)", text, flags=re.IGNORECASE):
            dependencies.append(
                {
                    "dependency_type": "cad_reference",
                    "referenced_path": match.group(1).strip(),
                    "resolution_status": "unresolved",
                    "confidence": 70,
                    "evidence": {"plugin": self.name, "pattern": match.group(0)[:120]},
                }
            )
        metadata = {"cad": {"extension": extension, "neutral_format": extension in {".step", ".stp", ".dxf", ".iges", ".igs"}}}
        return ParserResult(plugin_name=self.name, metadata=metadata, dependencies=dependencies, confidence=80)


class GenericDocumentParser:
    name = "builtin.generic_document_parser"
    supported_extensions = DOCUMENT_EXTENSIONS

    def parse(self, *, filename: str, original_source_path: str, content: bytes) -> ParserResult:
        extension = PurePath(filename).suffix.lower()
        text = content[:16_384].decode("utf-8", errors="ignore")
        title = ""
        if extension == ".pdf" and text.startswith("%PDF"):
            title = "PDF document"
        elif text.strip():
            title = text.strip().splitlines()[0][:255]
        return ParserResult(
            plugin_name=self.name,
            metadata={"document": {"extension": extension, "detected_title": title, "text_preview_available": bool(text.strip())}},
            confidence=75,
        )


class RegexNamingPlugin:
    name = "builtin.regex_naming_plugin"
    pattern = re.compile(r"(?P<customer_part_number>[A-Za-z0-9][A-Za-z0-9_.-]{2,})[_\s-]+(?:REV|R)?(?P<customer_revision>[A-Za-z0-9]{1,8})", re.IGNORECASE)

    def derive_identity(self, *, filename: str, original_source_path: str, metadata: dict) -> dict:
        for candidate in (filename, PurePath(original_source_path).name):
            match = self.pattern.search(candidate)
            if match:
                return {
                    "customer_part_number": match.group("customer_part_number"),
                    "customer_revision": match.group("customer_revision").upper(),
                    "mapping_source": self.name,
                    "confidence": 60,
                }
        return {}


class StandardReleasePackageGenerator:
    name = "builtin.standard_release_package_generator"

    def build(self, *, record, versions: list, dependencies: list) -> ReleasePackageResult:
        version_items = []
        for version in versions:
            file_object = version.file_object
            version_items.append(
                {
                    "file_version_id": str(version.id),
                    "version_number": version.version_number,
                    "filename": version.filename,
                    "original_source_path": version.original_source_path,
                    "sha256": file_object.sha256,
                    "byte_size": file_object.byte_size,
                    "storage_uri": file_object.storage_uri,
                    "customer_revision": version.customer_revision,
                    "internal_revision": version.internal_revision,
                    "metadata": version.version_metadata,
                }
            )
        manifest = {
            "generator": self.name,
            "record": {
                "id": str(record.id),
                "internal_record_id": record.internal_record_id,
                "customer_part_number": record.customer_part_number,
                "customer_revision": record.customer_revision,
                "internal_revision": record.internal_revision,
                "metadata": record.record_metadata,
            },
            "file_versions": version_items,
            "dependencies": [
                {
                    "id": str(dep.id),
                    "dependency_type": dep.dependency_type,
                    "referenced_path": dep.referenced_path,
                    "resolution_status": dep.resolution_status,
                    "target_record_id": str(dep.target_record_id) if dep.target_record_id else None,
                    "confidence": dep.confidence,
                }
                for dep in dependencies
            ],
        }
        return ReleasePackageResult(plugin_name=self.name, manifest=manifest, items=[{"file_version_id": item["file_version_id"], "item_role": "primary"} for item in version_items])
