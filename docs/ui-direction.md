# ForgeVault UI Direction

ForgeVault should look and behave like a serious manufacturing file vault, closer to Autodesk Vault, Windows File Explorer, and a controlled engineering document browser than a colorful SaaS dashboard.

## Hard visual rules

- No KPI card strip at the top.
- No oversized counts like managed records, checked out, release ready, or active folder eating screen space.
- No marketing tagline such as "messy manufacturing folders" in the app header.
- No rainbow dashboard colors.
- No red/green/blue/yellow status circus.
- No giant colorful status indicators.
- No decorative analytics-first landing page.

ForgeVault is not a metrics dashboard. It is a working file-control environment.

## Core layout goal

The default screen should prioritize actual work:

1. File/folder tree.
2. File/record table.
3. Preview pane.
4. Selected item details.
5. Check-in/check-out/version/release actions.

Screen space should be spent on files, previews, metadata, and revision control, not decorative summary cards.

## Preferred layout

```text
Top bar
- ForgeVault name/logo, compact
- current vault/path breadcrumb
- global search
- compact action buttons: Index, Check Out, Check In, Release, Export

Left pane
- Explorer-style folder/customer/job tree
- top-level customer folders
- nested project/job folders
- active folder highlighted

Center pane
- dense file/record table
- columns: name, part/customer identity, revision, state, checked out by, modified, type, size
- sortable columns
- minimal row height

Right pane
- preview area first
- CAD/image/PDF thumbnail or placeholder preview
- selected file metadata below preview
- version history
- checkout state
- dependency/release readiness

Bottom pane
- quiet activity/log strip
- indexing progress, errors, check-in/check-out messages
```

## Visual tone

- Dark industrial interface.
- Matte black, charcoal, graphite, gunmetal, and muted steel gray.
- Controlled orange accent only for primary actions and selected focus.
- Red only for critical errors, release blockers, or destructive confirmation.
- Green should be avoided except as a tiny success marker when absolutely needed.
- Blue should not compete as an accent color.
- Status should primarily be communicated with words, icons, neutral pills, borders, and placement.

## File-tree reference

ForgeVault must feel comfortable with a real shared-drive structure:

```text
Blue Prints/
  Customer A/
  Customer B/
  Customer C/
  Back Ups/
  Legacy Jobs/
  Vendor Folders/
```

Expected behavior:

- Preserve original folder paths.
- Index without rearranging the source folder.
- Handle customer folders, job folders, backup folders, and arbitrary junk-drawer structures.
- Let the user browse by folder or search across the vault.
- Make uncontrolled files visible without pretending the folder is already clean.

## Preview behavior

The right-side preview pane is important. Depending on file type, show:

- CAD preview thumbnail when available.
- PDF preview thumbnail for drawings/work instructions.
- Image preview for photos/screenshots.
- Spreadsheet/document icon with metadata when no preview exists.
- Neutral placeholder for unknown file types.

The preview should be visually dominant over dashboard stats.

## Button rules

- Primary action: orange, compact.
- Secondary action: graphite/steel button with muted border.
- Destructive action: dark button with thin red border.
- No huge bright buttons unless the action is the current focused workflow.
- No persistent giant dashboard buttons.

## Product feel

ForgeVault should feel like:

- a controlled engineering file browser,
- a practical PDM system,
- an upgrade from chaotic shared drives,
- a tool for finding, previewing, checking out, revising, and releasing manufacturing files.

ForgeVault should not feel like:

- a startup analytics dashboard,
- a colorful KPI wall,
- a marketing landing page,
- a SaaS toy,
- or a neon status board.
