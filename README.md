# ForgeVault

Standalone local PDM and engineering-file custody system. It indexes files, maintains record identities and append-only versions, and assembles controlled release packages without requiring Axiom.

## Current build state

**Reviewed:** 2026-10-20 · **Inspected main:** `e1156cdc6271` · **Stage:** experimental/beta; individual workflow evidence below.

- [ForgeVault CI](https://github.com/danieloculus0-bot/ForgeVault/actions/runs/39502332876) — **Passed** at inspected `main`.
- [ForgeVault tests](https://github.com/danieloculus0-bot/ForgeVault/actions/runs/39502332968) — **Passed** at inspected `main`.
- [ForgeVault smoke and build](https://github.com/danieloculus0-bot/ForgeVault/actions/runs/39502333036) — **Passed** at inspected `main`.
- [ForgeVault Desktop Build](https://github.com/danieloculus0-bot/ForgeVault/actions/runs/39502333172) — **Passed** at inspected `main`.

[Live CI and build history](https://github.com/danieloculus0-bot/ForgeVault/actions) takes precedence over this dated snapshot.

## Working capabilities

- Managed content-addressed file objects; staged atomic writes, SHA-256 validation on reads and corruption/interruption/concurrency regression tests.
- Customer/internal revision mapping, checkout/review/release lifecycle and package manifests; JobBOSS² export/outbox framework.
- Checksum-verified read-only released PDF/version handoff used by the real ForgeVault → EZ-FAIR → Axiom integration; Gothic Lime desktop interface.

## Install and run

For Windows desktop setup, Docker, and FastAPI development commands use [the archived setup guide](docs/archive/README_2026-10-20_before_refresh.md). Install the package and development dependencies from `pyproject.toml`; run `python -m pytest -q` for automated tests.

## Known engineering limits

- A released-PDF handoff is a local service contract, not a remotely authenticated API or automatically approved customer drawing.
- Automated Windows packaging and storage tests do not prove workstation rollout, verified off-site backups or two-phase database/object-store recovery.
- ForgeVault owns controlled source files; EZ-FAIR owns extraction and Axiom owns imported inspection records.

## Next priorities

Verify backup/restore and orphan-object reconciliation, then expose permissioned cross-app retrieval while retaining exact version identity.

## Documentation

- [Storage integrity validation](docs/VALIDATION.md)
- [Axiom controlled FAI integration](https://github.com/danieloculus0-bot/Axiom_Beta/blob/main/.github/workflows/controlled-fai-wiring.yml)
- [**Full earlier README: setup, feature history, experiments and rationale**](docs/archive/README_2026-10-20_before_refresh.md)

Historical details are archived, not discarded. Unverified planned features are not silently described as shipped.


## API security deployment requirements

The \`/api/v1\` HTTP API (including desktop bridge endpoints) requires a Bearer
token on **every** request. No authentication bypass is enabled for local traffic.
Provision \`FORGEVAULT_API_TOKENS_JSON\` through deployment secrets as
\`{"<sha256-of-token>":{"user":"verified-user","role":"editor"}}\`.
Hash each random token with \`hashlib.sha256(token.encode()).hexdigest()\`;
do not commit raw tokens or credentials. Supported roles are \`viewer\`,
\`editor\`, \`reviewer\`, \`admin\`. Review decisions require reviewer/admin,
record writes editor/admin, and destructive/JobBoss2 export operations admin.
The server attributes actions to the authenticated identity and rejects
conflicting actor/submitted_by/reviewer claims. Bearer tokens are not browser
cookies, so cross-site requests cannot acquire them automatically. Keep tokens
out of query parameters and require HTTPS on all non-loopback transports.

The packaged API's \`/ui\` is a static frontend; browser-to-API token
provisioning and end-user sign-in **are not implemented in this patch**.
The web UI's protected API calls will fail until a secure client-side credential
workflow or verified identity proxy is integrated. This is an explicit,
fail-closed deployment blocker, not a reason to re-enable anonymous writes.
The supplied Docker Compose file binds only to loopback and demands external
database and token secrets. Confirm authorization for any other transport or
integration separately.
