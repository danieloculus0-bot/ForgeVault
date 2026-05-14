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
