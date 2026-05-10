from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ParserResult:
    plugin_name: str
    metadata: dict = field(default_factory=dict)
    dependencies: list[dict] = field(default_factory=list)
    confidence: int = 100


class CadParserPlugin(Protocol):
    name: str
    supported_extensions: set[str]

    def parse(self, *, filename: str, original_source_path: str, content: bytes) -> ParserResult: ...


class DocumentParserPlugin(Protocol):
    name: str
    supported_extensions: set[str]

    def parse(self, *, filename: str, original_source_path: str, content: bytes) -> ParserResult: ...


class NamingPlugin(Protocol):
    name: str

    def derive_identity(self, *, filename: str, original_source_path: str, metadata: dict) -> dict: ...


@dataclass(frozen=True)
class ReleasePackageResult:
    plugin_name: str
    manifest: dict
    items: list[dict]


class ReleasePackageGenerator(Protocol):
    name: str

    def build(self, *, record, versions: list, dependencies: list) -> ReleasePackageResult: ...
