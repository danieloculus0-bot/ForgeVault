# ForgeVault Architecture

ForgeVault is a generic file/object PDM, not a SolidWorks-specific vault. The core domain owns records, versions, revisions, lifecycle state, dependencies, release packages, audit, and metadata. Format-specific behavior is isolated behind plugins.

## Service boundaries

* **Ingestion service** accepts staged content, preserves the original source path, executes parser and naming plugins, creates ingest jobs, maps or creates managed records, appends immutable versions, and stores inferred dependencies.
* **Metadata service** manages internal record IDs, dual customer/internal revision identity, lifecycle seeds, and discovered metadata field definitions.
* **Versioning service** computes SHA-256 hashes, writes content to the local content-addressed vault, deduplicates file objects, appends file versions, and releases checkout locks on successful check-in.
* **Lifecycle service** validates state transitions and delegates release package construction to release generator plugins. Unresolved dependencies block release.
* **Search service** queries database indexes over record identity, filenames, source paths, and JSON metadata. It never crawls the vault filesystem.
* **Folder ingestion service** recursively indexes user-selected folders, preserving original paths and assigning reviewable unmapped identities when customer naming data is missing.
* **Integration service** creates durable JobBOSS² release handoff events and outbox JSON payloads for ERP middleware or webhook gateways.
* **Plugin service** runs parser, naming, and release package plugins and persists every plugin execution for auditability.

## Plugin architecture

ForgeVault exposes protocols for:

* CAD parser plugins: extract metadata and inferred dependencies from CAD-like files without making any vendor format authoritative.
* Document parser plugins: extract metadata from PDFs, office documents, images, and work instructions.
* Customer naming plugins: derive customer part/revision from customer-specific filenames or paths when supplied metadata is incomplete.
* Release package generators: build immutable manifests and item lists for shop packages.

The built-in registry provides generic implementations for arbitrary files, neutral CAD references, documents, regex naming, and standard release packages. Additional plugins can be registered without changing the core schema.

## Persistence principles

* Files are blobs; metadata drives control and retrieval.
* Version history is append-only.
* Release packages snapshot exact file version IDs and hashes.
* Internal record IDs are immutable and coexist with customer part/revision mappings.
* Inferred relationships are recorded with confidence and evidence so imperfect legacy data remains traceable.
