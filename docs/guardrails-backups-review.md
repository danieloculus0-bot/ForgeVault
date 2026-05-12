# ForgeVault Guardrails, Backups, and Review Workflows

ForgeVault should make it easy to do the right thing and hard to do the wrong thing.

This is a core product rule, not a future nice-to-have.

## Safety principle

Normal users should be able to work without feeling blocked by bureaucracy, but they should not be able to accidentally destroy files, wipe folders, overwrite controlled revisions, or release bad data without review.

ForgeVault should guide, warn, checkpoint, and route work for review before damage happens.

## Destructive action rules

Any action that can alter, delete, overwrite, migrate, unlink, reset, or purge filesystem data must require explicit confirmation.

Examples:

- delete from disk,
- remove a managed source folder,
- reset local vault,
- purge local database,
- delete stored file objects,
- overwrite an existing released revision,
- bulk re-index with replacement behavior,
- move source files,
- rename source files,
- migrate live folders,
- change shared/server database settings,
- change vault storage path.

Default behavior must be non-destructive.

Preferred default wording:

```text
This will not delete files from disk.
ForgeVault will only remove this folder from the index.
```

For actual filesystem deletion:

```text
This can permanently delete files from disk.
Type DELETE to continue.
```

For major destructive/admin actions, require elevated permission or checker/admin approval.

## Backup-first behavior

ForgeVault should automatically create backup/checkpoint records before risky operations.

Backup targets can include:

- local backup folder,
- shared backup folder,
- admin-configured backup target,
- future cloud/object storage target,
- future Git-style metadata push for vault configuration/history.

Default local backup structure:

```text
%LOCALAPPDATA%\ForgeVault\backups\
  config\
  database\
  manifests\
  operation-checkpoints\
```

Backups should include:

- settings.json snapshots,
- source folder list,
- database backup/checkpoint when practical,
- release manifests,
- pre-migration operation manifest,
- user/action/timestamp metadata.

Risky operation flow:

1. Create operation checkpoint.
2. Validate source and destination paths.
3. Warn user in plain language.
4. Require confirmation or review if destructive.
5. Execute.
6. Write audit log.
7. Notify reviewer/admin when configured.

## Permission levels

ForgeVault should support simple practical roles.

### Viewer

Can search, preview, and read released/available files.

Cannot check out, check in, release, change setup, or approve work.

### Contributor

Can add/index source folders if allowed, check out files, submit check-ins, and create review requests.

Cannot perform destructive actions, force cancel another user's checkout, release packages, reset vaults, or change shared settings.

### Checker

Can review submitted changes, approve/reject check-ins, approve release readiness, and cancel/resolve contributor mistakes.

### Administrator

Can configure vault settings, manage users, manage source folders, approve destructive actions, configure backup paths, configure email notifications, and manage shared/server connection settings.

## New user safety

A new or low-permission user should still be able to do useful work.

They should be guided toward safe workflows:

- check out file,
- make intended update,
- check in as pending review,
- add notes,
- submit to checker,
- receive approval/rejection feedback.

They should not feel useless, but they should not be able to wreck released data.

Recommended behavior:

```text
Your change was submitted for review.
A checker will review it before it becomes released.
```

not:

```text
Permission denied.
```

unless the action is truly blocked.

## Review queue

ForgeVault should have a review queue for controlled work.

Review items should include:

- pending check-ins,
- revision changes,
- release requests,
- forced checkout cancellation requests,
- source folder additions/removals,
- high-risk bulk indexing operations,
- destructive action requests,
- shared/server configuration changes.

Review item fields:

```text
id
request_type
status
submitted_by
assigned_checker
record_id
file_version_id
source_folder_id
summary
reason
risk_level
created_at
reviewed_at
reviewed_by
review_comment
```

Statuses:

```text
pending
approved
rejected
cancelled
completed
```

Risk levels:

```text
low
medium
high
critical
```

## Email notification plug-in path

Email should be pluggable later, but the workflow should be designed now.

Future email events:

- review request submitted,
- checker assigned,
- review approved,
- review rejected,
- checkout overdue,
- forced checkout requested,
- release approved,
- release blocked,
- destructive action requested,
- backup failed,
- shared/server connection failed.

Email config should live in admin settings, not in code.

Fields:

```text
smtp_host
smtp_port
smtp_security
smtp_username
smtp_password_secret_ref
from_address
admin_notification_emails
checker_notification_emails
send_test_email
```

The product should also support future alternatives:

- Gmail/Google Workspace connector,
- Microsoft 365 connector,
- webhook notifications,
- local-only notification log.

## Audit log requirements

Every controlled or risky action must be auditable.

Capture:

- actor,
- action,
- affected record/file/folder,
- previous value,
- new value,
- approval path,
- reviewer,
- timestamp,
- backup/checkpoint reference,
- notification status.

## UI rules for guardrails

The UI should be calm and plain-language.

Use wording like:

```text
Submit for Review
Approve Change
Reject Change
Backup Created
Remove from Index
Delete from Disk
```

Avoid vague/destructive wording like:

```text
Reset
Clear
Nuke
Purge
Delete Everything
```

unless guarded by admin-only advanced mode and explicit typed confirmation.

## Immediate implementation steps

1. Add `source_folders` persistence and setup status APIs.
2. Add review request model/table.
3. Add role/permission checks for destructive and release actions.
4. Add backup/checkpoint service before destructive operations.
5. Add email notification event model, without requiring SMTP setup yet.
6. Add UI review queue.
7. Add admin notification settings later.

## Product rule

If an action can break the vault, delete data, confuse production, or bypass release control, ForgeVault should either:

- prevent it,
- route it for review,
- create a backup first,
- or require explicit admin confirmation.

Prefer safe automation over user burden.
