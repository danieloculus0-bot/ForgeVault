# ForgeVault x BEAN Core: first real record-health integration

**Status:** experimental review-only feature, separate from `main`. Not a release or autonomous PDM approval.

## Code preserved

- Pre-integration baseline: `archive/forgevault-pre-bean-20261020` (unchanged snapshot of main).
- Feature implementation: `feature/bean-pdm-record-review-20261020`.
- Security work remains separately open in ForgeVault PR #7 and PR #8; this feature is **not** a replacement for authentication/authorization.

## What works in ForgeVault source

Existing record ingestion, folder indexing, SHA-256 content-addressed object storage, version history, checkout, human review, lifecycle release/package generation, dependency data, controlled released drawing handoff, and search are retained. We do not delete or rewrite these mechanisms.

## New implemented behavior

1. Select a record in the existing desktop/browser UI and choose **BEAN Review**.
2. The ForgeVault backend reads the latest version, **re-reads its stored bytes through the real SHA-256 checked LocalVaultStorage**, looks for revision mismatch, missing identity, active checkout, pending human review, unresolved dependencies, and missing release-package evidence when the record is marked Released.
3. The explicitly invoked subprocess imports the **real** `bean.integration.reasoning_layer.BeanReasoningLayer` from a BEAN Core checkout, persists a canonical observation in BEAN's SQLite event memory and returns the durable BEAN event ID. It compares the current issue codes with prior reviews of the same stable hashed record key, indicating recurring, new and resolved issues.
4. The UI displays actual findings and continuity counts. ForgeVault file bytes, customer naming/path, operator identities, and document bodies **are not sent to the BEAN memory**.
5. BEAN does not check in, release, change metadata, change records, approve reviews, run a language model, or claim the record is safe. No detected issue is **not** engineering approval.

This is an actual memory integration, not a simulated AI verdict. It does **not** demonstrate reasoning generalization or autonomous learning.

## Development installation

Install ForgeVault Python dependencies and checkout the public BEAN Core repository. Run ForgeVault normally, with:

- `FORGEVAULT_BEAN_CORE_ROOT`: full path to the BEAN checkout containing `bean/integration/reasoning_layer.py`
- `FORGEVAULT_BEAN_MEMORY_PATH` (optional): writable BEAN-specific SQLite memory path; default is `forgevault-bean-memory.sqlite3` beside the local vault root
- `FORGEVAULT_BEAN_PYTHON` (optional): Python interpreter that has ForgeVault installed; **required for a packaged ForgeVault executable** because the frozen executable itself cannot run `python -m`

Example on Windows PowerShell for source-based development:

```powershell
$env:FORGEVAULT_BEAN_CORE_ROOT = "D:\BEAN\core"
$env:FORGEVAULT_BEAN_MEMORY_PATH = "$env:LOCALAPPDATA\ForgeVault\bean-memory.sqlite3"
```

The integration returns HTTP 503 with a clear error if BEAN Core is absent or not configured. It does not silently substitute a fake agent. A packaged Windows desktop needs the separately installed Python and source checkout: the packaging workflow compiling ForgeVault by itself does **not** make BEAN Core available.

## Verification and deployment gaps

- `.github/workflows/bean-record-review.yml` checks out BEAN Core at a pinned commit and runs real Core restart/memory continuity tests, not mocks. Normal ForgeVault test/build CI also runs.
- **Security:** main branch does not have the incomplete security PRs merged. The existing unauthenticated browser surface and ForgeVault's broader actor-input problems must be addressed before shared-network or production deployment. This POST route must only be exposed after authenticated caller/role handling is integrated.
- **Multitenancy and load:** BEAN memory is run in an isolated subprocess for each explicit review to avoid Core's process-global SQLite singleton colliding with ForgeVault threads. High-volume concurrency, multi-host locking, and packaged desktop setup need separate production tests.
- **Scoring:** issue codes are deterministic source-specific checks; no evidence score is treated as a calibrated probability or a release criterion. The existing ledger remains separate from BEAN's episodic memory.
- **Human process:** checks surface risks and history. They do not replace signoff, geometric/drawing validation, a PDM release gate, or real factory acceptance testing.
