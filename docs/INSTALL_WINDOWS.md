# ForgeVault Windows Install

This is the simple Windows setup path.

## Easiest path: desktop build artifact

1. Go to the GitHub Actions build for ForgeVault.
2. Download the `ForgeVaultDesktop-windows` artifact.
3. Unzip it somewhere simple, such as your Desktop.
4. Double-click `START-FORGEVAULT.exe`.
5. Your browser should open to ForgeVault.
6. Click `Browse for Source Folder`, or paste the folder path you want to manage.
7. Click `Add Source Folder`.
8. Click `Index Selected`.
9. Search `UNMAPPED` to see files that need cleanup.

ForgeVault stores its local database and vault here by default:

```text
%LOCALAPPDATA%\ForgeVault
```

## Build it yourself from source

Install Python 3.11 or newer, then open PowerShell in the ForgeVault repo folder and run:

```powershell
.\scripts\build_windows_desktop.ps1
```

After the build finishes, run:

```powershell
.\dist\ForgeVaultDesktop-windows\START-FORGEVAULT.exe
```

## Run from source without building an EXE

Open PowerShell in the ForgeVault repo folder and run:

```powershell
.\scripts\Launch-ForgeVault.ps1 --manage-folder "C:\Engineering\Jobs"
```

Replace `C:\Engineering\Jobs` with the real folder you want ForgeVault to manage.

## Safety notes

- ForgeVault does not delete your source files during setup.
- Adding a source folder only tells ForgeVault where to index files from.
- Removing a source folder from the UI removes it from ForgeVault's index only.
- Checked-in versions are copied into ForgeVault's local vault.
- The original source path is preserved for traceability.

## First-run checklist

- App opens in browser.
- Source folder is added.
- Index Selected completes.
- Table shows records.
- Select a record.
- Check Out works.
- Check In New Version opens a file chooser.
- Review queue shows submitted reviews.
