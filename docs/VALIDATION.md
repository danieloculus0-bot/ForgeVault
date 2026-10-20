# ForgeVault Validation

ForgeVault validation is intentionally automated before packaging or release.

Core checks:

```bash
python scripts/placeholder_audit.py
python scripts/ci_smoke.py
pytest
```

Windows desktop package checks:

```powershell
.\scripts\build_windows_desktop.ps1
```

Expected validation coverage:

- UI loads from `/ui`.
- optional UI helper scripts are injected.
- source folders can be added, indexed, searched, and removed from index state.
- checkout and check-in create a new file version.
- submitted reviews are created, approved, and logged.
- release transition creates a release package.
- placeholder audit blocks unfinished product language from entering the repo.

A local Windows install is not considered proven until the generated desktop package is opened on a real Windows machine and a real test folder is indexed.

## Object durability and Windows build (2026-10-20)

The local vault now fsyncs staged files and atomically replaces their digest
paths. Every returned object is SHA-256 checked; corrupt objects cause
\`VaultIntegrityError\` rather than silently serving wrong CAD/drawing content.
Failed staging cleans up temporary files. The test suite covers concurrent
same-content uploads, truncated/tampered bytes, bad digests and interrupted
commits. Backups, database/file transaction coordination, remote-share
semantics and disaster recovery remain separate release criteria.

\`smoke-build.yml\` no longer runs the optional CairoSVG icon generator on
clean Windows runners: Cairo native DLLs were missing, and the icon is not
required for a working executable. The packaged \`ForgeVault.exe\` uses
PyInstaller's default icon unless an existing ICO is supplied. The optional
\`scripts/Make-ForgeVaultIcon.ps1\` is a separate manual branding step; it
still needs a working native Cairo installation.
