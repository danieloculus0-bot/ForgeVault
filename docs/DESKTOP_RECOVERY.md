# Verified ForgeVault Desktop snapshot and recovery

This tool covers only the local ForgeVault Desktop layout: SQLite at
HOME/data/forgevault.db and immutable local objects at HOME/data/vault.
It does not back up PostgreSQL servers, external file adapters, source
folders outside the vault, integrations or all local application settings.
It does not authorize restoring over a running production installation.

## Commands

Run from an installation where the forgevault package is importable.

Snapshot:
python -m forgevault.services.desktop_backup snapshot --home PATH_TO_DESKTOP_HOME --archive PATH_TO_BACKUP_ZIP

Verify:
python -m forgevault.services.desktop_backup verify --archive PATH_TO_BACKUP_ZIP

Restore to a NEW directory only:
python -m forgevault.services.desktop_backup restore --archive PATH_TO_BACKUP_ZIP --into-new-home PATH_TO_NEW_HOME

Store the ZIP outside the ForgeVault home and preferably on a separate
physical device. The tool refuses to overwrite an existing archive or
restore into an existing installation.

## What it verifies

- SQLite backup API creates a consistent committed database snapshot,
  including transactions committed before snapshot completion.
- SQLite quick_check and foreign_key_check are executed on the copy.
- All file_objects records must reference local SHA-256 object files.
- Each referenced stored object must exist and match its hash and size.
- Archive manifest, SQLite hash and all object hashes are verified again
  before the archive is atomically published.
- Recovery checks the entire archive before writing any destination files.
- Object storage paths recorded in restored SQLite are rewritten to the
  new desktop home; the source database is left unchanged.
- Restores publish a completely staged NEW destination directory, never
  destructively overwrite an existing vault.

## Limitations and release criteria

There is no disaster-recovery guarantee until these procedures have
been exercised with a real Windows desktop installation, full data,
an interrupted backup, ACLs, long filenames, locked databases and
off-device archive recovery. Online backups are safe for immutable,
append-only local objects, but objects deleted by an external process
mid-snapshot cause backup failure. PostgreSQL requires its own database
snapshot and coordination protocol. Neither the archive nor this
utility encrypts contents at rest.

Do not assume backup status is healthy based on file existence. Run
verify on a second system and perform a restore-to-new-home rehearsal.

The verification tests are in tests/test_desktop_backup.py.
