# ForgeVault Windows Quickstart

ForgeVault Desktop is meant to launch like a normal local app. It opens a browser UI and stores its local database and vault under your Windows user profile.

## Easiest path

1. Download `ForgeVaultDesktop.exe` from the GitHub Actions build artifact.
2. Put it somewhere simple, such as `C:\ForgeVault\ForgeVaultDesktop.exe`.
3. Double-click `ForgeVaultDesktop.exe`.
4. Your browser opens to ForgeVault.
5. In the left panel, click `Choose Folder Now`.
6. Pick the folder that contains drawings, CAD files, PDFs, job folders, or engineering files.
7. Click `Add Source Folder`.
8. Click `Index Selected`.
9. Click a file in the table to view details, check it out, check in a replacement version, or submit it for review.

ForgeVault does not delete your files when you add or index a source folder. It indexes and stores managed copies so revision control can start without destroying the old folder layout.

## Local data location

By default, ForgeVault Desktop stores local data here:

```text
%LOCALAPPDATA%\ForgeVault
```

That folder contains the SQLite database, local vault storage, staging folder, logs, backups, and integration outbox.

## Developer/source launch

If running from source instead of the packaged EXE:

```powershell
.\scripts\Launch-ForgeVault.ps1
```

To pre-fill a source folder:

```powershell
.\scripts\Launch-ForgeVault.ps1 --manage-folder "C:\Engineering\Jobs"
```

## Build the EXE from source

```powershell
.\scripts\build_windows_desktop.ps1
```

When the build finishes, run:

```powershell
.\dist\ForgeVaultDesktop.exe
```

## First screen checklist

- `Browse for Source Folder` opens a Windows folder picker when running from the desktop launcher or EXE.
- `Folder path` can also be typed or pasted manually.
- `Display name` is optional.
- `Add Source Folder` saves the folder into ForgeVault.
- `Index Selected` scans the folder and loads files into the search table.
- Removing a source folder removes it from ForgeVault indexing only. It does not delete disk files.

## Basic file workflow

1. Search or select a file.
2. Click `Check Out` before editing or replacing it.
3. Edit the actual file using your normal CAD, PDF, Excel, or text tools.
4. Click `Check In New Version`.
5. Browse to the replacement file.
6. Add a note and revision info if needed.
7. Leave `Submit checked-in version for review` checked when quality or engineering review is needed.
8. Click `Check In`.

The check-in creates a new managed version, preserves the previous version, releases the checkout lock, and can create a pending review.
