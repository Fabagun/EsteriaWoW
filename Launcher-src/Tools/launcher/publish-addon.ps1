param(
    [Parameter(Mandatory = $true)]
    [string[]]$SourceFolders,

    [Parameter(Mandatory = $true)]
    [string]$AddonsRoot,

    [Parameter(Mandatory = $true)]
    [string]$Id,

    [Parameter(Mandatory = $true)]
    [string]$Name,

    [Parameter(Mandatory = $true)]
    [string]$Version,

    [string]$Description = '',
    [string]$Author = '',
    [string]$Category = '',
    [string]$Homepage = '',
    [string]$Changelog = '',
    [string]$BaseUrl = 'http://planetkai.hopto.org:7384/addons/',
    [switch]$Required
)

$ErrorActionPreference = 'Stop'

if ($Id -notmatch '^[A-Za-z0-9._-]+$') {
    throw 'Id may only contain letters, numbers, dot, underscore, and dash.'
}
if ($Version -notmatch '^[A-Za-z0-9._-]+$') {
    throw 'Version may only contain letters, numbers, dot, underscore, and dash.'
}

$resolvedFolders = @()
foreach ($folder in $SourceFolders) {
    $resolved = (Resolve-Path -LiteralPath $folder).Path
    if (-not (Test-Path -LiteralPath $resolved -PathType Container)) {
        throw "Addon source folder does not exist: $folder"
    }
    $tocFiles = @(Get-ChildItem -LiteralPath $resolved -Filter '*.toc' -File)
    if ($tocFiles.Count -eq 0) {
        throw "Addon source folder has no .toc file: $resolved"
    }
    $resolvedFolders += $resolved
}

New-Item -ItemType Directory -Force -Path $AddonsRoot | Out-Null
$packageDir = Join-Path $AddonsRoot $Id
New-Item -ItemType Directory -Force -Path $packageDir | Out-Null
$zipPath = Join-Path $packageDir "$Version.zip"
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

Compress-Archive -LiteralPath $resolvedFolders -DestinationPath $zipPath -CompressionLevel Optimal

$hash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
$size = (Get-Item -LiteralPath $zipPath).Length
$folderNames = @($resolvedFolders | ForEach-Object { Split-Path $_ -Leaf })

$catalogPath = Join-Path $AddonsRoot 'catalog.json'
if (Test-Path -LiteralPath $catalogPath) {
    $catalog = Get-Content -LiteralPath $catalogPath -Raw | ConvertFrom-Json
} else {
    $catalog = [PSCustomObject]@{
        schemaVersion = 1
        baseUrl = $BaseUrl
        addons = @()
    }
}

if (-not $catalog.PSObject.Properties['schemaVersion']) {
    $catalog | Add-Member -NotePropertyName schemaVersion -NotePropertyValue 1
}
$catalog.baseUrl = $BaseUrl
$current = @($catalog.addons | Where-Object { $_.id -ne $Id })
$entry = [PSCustomObject]@{
    id = $Id
    name = $Name
    version = $Version
    description = $Description
    author = $Author
    category = $Category
    homepage = $Homepage
    changelog = $Changelog
    packageUrl = "$Id/$Version.zip"
    sha256 = $hash
    size = $size
    folders = $folderNames
    required = [bool]$Required
}
$catalog.addons = @($current + $entry | Sort-Object name)

$tempCatalog = "$catalogPath.tmp"
$catalog | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $tempCatalog -Encoding UTF8
Move-Item -LiteralPath $tempCatalog -Destination $catalogPath -Force

Write-Output "Published $Name $Version"
Write-Output "Package: $zipPath"
Write-Output "SHA256: $hash"
Write-Output "Size: $size"
Write-Output "Catalog: $catalogPath"
