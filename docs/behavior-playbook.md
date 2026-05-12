# ForgeVault Behavior Playbook

ForgeVault's core product rule is simple: make the correct action obvious, make risky actions guided, and make destructive actions hard to do by accident.

## Behavior pillars

1. Default to safe.
2. Ask plain-language questions.
3. Remember user choices.
4. Hide technical setup unless needed.
5. Route risky changes through review.
6. Never delete filesystem data casually.
7. Preserve original paths and evidence.
8. Prefer one-click workflows over configuration screens.

## First launch

ForgeVault should start with the shortest useful path:

```text
Use this computer
Point me to the folders
Start indexing
```

Default mode:

```text
Local Vault
```

The user should not see database strings, migrations, terminal commands, or server settings unless they open Advanced.

## Source folder behavior

Primary actions:

```text
Browse for Source Folder
Add Source Folder
Index Selected
Add Another Folder
Remove From Index
```

Rules:

- Adding a source folder does not move files.
- Indexing does not reorganize files.
- Removing from index does not delete files.
- Original paths stay searchable and visible.
- Hidden/system/temp junk is skipped by default.
- Unknown file types are still indexed.

## File identity behavior

When ForgeVault cannot determine a customer/part/revision identity, it should not block indexing.

Use temporary identity:

```text
UNMAPPED-[hash]
```

Then show:

```text
Needs Review
```

The user can later map the file to a customer, part number, revision, job, project, or release package.

## Check-out behavior

Simple wording:

```text
Check Out
Check In New Version
Cancel Checkout
Submit for Review
```

Rules:

- One active checkout per record.
- Show who has it checked out.
- Wrong-user check-in is blocked.
- Cancel checkout is allowed only for owner/checker/admin unless review/force path is used.
- Cancel checkout does not delete files.
- If check-in affects released content, route to review.

## Check-in behavior

Ideal simple flow:

1. User selects checked-out record.
2. Clicks Check In New Version.
3. Picks replacement/new file.
4. Adds short note.
5. ForgeVault detects revision/extension/source path changes.
6. If low risk, save as new version.
7. If controlled/released/risky, submit for checker review.

User-facing result:

```text
Version saved
```

or:

```text
Submitted for review
```

not:

```text
permission denied
```

unless truly blocked.

## Review behavior

Review queue should handle:

- pending check-ins,
- release requests,
- source folder changes,
- destructive requests,
- force-cancel checkout requests,
- revision mapping changes,
- bulk indexing warnings.

Plain actions:

```text
Approve
Reject
Request Changes
Assign Checker
```

Reviewer should see:

- what changed,
- who submitted it,
- source path,
- old version,
- new version,
- file type,
- note/reason,
- risk level.

## Release behavior

Release should be guided.

Before release, ForgeVault checks:

- file has identity,
- no active checkout,
- latest version exists,
- required docs are present if configured,
- dependencies are known/resolved if configured,
- review is complete if required,
- backup/checkpoint exists.

If blocked, show plain blockers:

```text
Cannot release yet
- File is still checked out by Daniel
- Customer revision is missing
- Review is pending
```

## Destructive behavior

Default destructive alternative:

```text
Remove From Index
```

Actual filesystem delete should be rare, admin-only, backup-first, and typed-confirmed.

Typed confirmation:

```text
DELETE
```

Do not use casual labels like Reset, Clear, Purge, or Delete Everything in normal UI.

## Backup behavior

Before risky actions, create an operation checkpoint.

Risky actions include:

- reset local vault,
- database migration,
- source folder storage path change,
- destructive delete,
- bulk replace/reindex,
- release package overwrite,
- shared server configuration change.

Backup/checkpoint should include:

- actor,
- action,
- timestamp,
- affected paths,
- settings snapshot,
- source folder list,
- database snapshot when practical,
- manifest of affected records.

## Notification behavior

Email is future-pluggable, but behavior should already assume notifications exist.

Events:

- review requested,
- review approved/rejected,
- checkout overdue,
- destructive action requested,
- backup failed,
- release blocked,
- release completed.

If email is not configured, record notifications in the app notification log.

## User roles

### Viewer

Can search, preview, open metadata, and view released files.

### Contributor

Can add/index allowed source folders, check out, check in drafts, and submit for review.

### Checker

Can approve/reject changes, review pending check-ins, resolve mistakes, and approve release readiness.

### Administrator

Can configure vaults, users, source folders, backup paths, notification settings, server/database settings, and destructive actions.

## Unprecedented simplicity targets

ForgeVault should feel like:

```text
Find the file
Check it out
Make the change
Check it back in
Send it for review
Release it
```

It should not feel like:

```text
configure database connection strings, migration state, source adapters, storage roots, metadata schemas, and lifecycle objects
```

That complexity can exist underneath, but the user should not have to stare at it.

## Immediate build priorities

1. Add review request model/API.
2. Add notification event model/API, email later.
3. Add backup checkpoint service.
4. Add check-in workflow endpoint.
5. Add release readiness endpoint.
6. Add GUI review queue panel.
7. Add local notification log panel.
8. Add admin settings screen only after normal user flow works.
