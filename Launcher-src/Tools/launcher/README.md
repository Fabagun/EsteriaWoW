# Esteria launcher build helper

`install.ps1` downloads a portable Node.js 20 runtime and runs the Electron
launcher build without changing the repository's global Node installation.

```powershell
Set-Location Launcher-src\Tools\launcher
.\install.ps1
```

The helper writes the packaged artifacts to the launcher root's `dist` or
`distprod` directory, depending on the active electron-builder configuration:

- `Esteria Launcher.exe` (portable); and
- `Esteria Launcher_Installer.exe` (NSIS).

The downloaded `node` directory is ignored by Git. Keep the client CDN source
and launcher-update artifacts outside this repository; see
`CDN-SETUP-WINDOWS10.md` for the Windows 10 CDN procedure.

## Publish an add-on package for the new launcher

`publish-addon.ps1` packages one or more local add-on folders, calculates the
SHA-256 and size, and creates or updates the CDN `catalog.json` entry.

```powershell
.\publish-addon.ps1 `
  -SourceFolders 'D:\Addons\Questie' `
  -AddonsRoot 'C:\Esteria\CDN\addons' `
  -Id 'questie' `
  -Name 'Questie' `
  -Version '1.2.0' `
  -Description 'Quest tracking for Esteria.'
```

For a required multi-folder add-on:

```powershell
.\publish-addon.ps1 `
  -SourceFolders 'D:\Addons\EsteriaCore','D:\Addons\EsteriaCore_Config' `
  -AddonsRoot 'C:\Esteria\CDN\addons' `
  -Id 'esteria-core' `
  -Name 'Esteria Core' `
  -Version '2026.10.07' `
  -Required
```

The package payload and generated `catalog.json` belong in the external CDN
staging directory, not in Git.
