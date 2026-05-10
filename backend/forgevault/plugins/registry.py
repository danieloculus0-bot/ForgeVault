from __future__ import annotations

from pathlib import PurePath

from .builtin import GenericDocumentParser, GenericFileParser, NeutralCadParser, RegexNamingPlugin, StandardReleasePackageGenerator


class PluginRegistry:
    def __init__(self) -> None:
        self.parsers = [GenericFileParser(), NeutralCadParser(), GenericDocumentParser()]
        self.naming_plugins = [RegexNamingPlugin()]
        self.release_generators = {StandardReleasePackageGenerator.name: StandardReleasePackageGenerator()}
        self.default_release_generator_name = StandardReleasePackageGenerator.name

    def parser_plugins_for(self, filename: str):
        extension = PurePath(filename).suffix.lower()
        for parser in self.parsers:
            supported = getattr(parser, "supported_extensions", set())
            if not supported or extension in supported:
                yield parser

    def release_generator(self, name: str | None = None):
        generator_name = name or self.default_release_generator_name
        try:
            return self.release_generators[generator_name]
        except KeyError as exc:
            raise ValueError(f"unknown release package generator: {generator_name}") from exc


default_registry = PluginRegistry()
