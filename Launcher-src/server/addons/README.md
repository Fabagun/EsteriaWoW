# Packaged add-ons for the Tauri launcher

The new launcher can install add-ons from ZIP packages served by the same Esteria CDN service.

For production, point `ADDONS_DIR` at an external directory such as:

```text
C:\Esteria\CDN\addons
```

Do not store production ZIP payloads in this Git checkout.

## Layout

```text
C:\Esteria\CDN\addons\
  catalog.json
  Questie\
    1.2.0.zip
  AtlasLoot\
    6.05.zip
```

Copy `catalog.example.json` as a starting point for `catalog.json`.

Each ZIP must contain the declared add-on folder at its root:

```text
Questie\
  Questie.toc
  ...
```

For add-ons that install multiple folders, list every top-level folder in `folders`.

## Hash a package

```powershell
$zip = 'C:\Esteria\CDN\addons\Questie\1.2.0.zip'
(Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
(Get-Item $zip).Length
```

Put those values into `sha256` and `size` in `catalog.json`.

A package URL can be relative to `baseUrl`, for example:

```json
{
  "baseUrl": "https://cdn.example.com/addons/",
  "addons": [
    {
      "id": "questie",
      "name": "Questie",
      "version": "1.2.0",
      "description": "Quest tracking for Esteria.",
      "packageUrl": "Questie/1.2.0.zip",
      "sha256": "...",
      "size": 123456,
      "folders": ["Questie"],
      "required": false
    }
  ]
}
```

The server exposes the catalog at `/api/v2/addons/catalog.json` and package files at `/addons/...`.
