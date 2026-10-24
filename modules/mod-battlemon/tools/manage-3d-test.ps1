param(
    [ValidateSet('install', 'remove', 'validate')]
    [string]$Action = 'validate',
    [string]$Client = 'D:\WoW\Dark-Bro-WXL-COA\Dark-Brotherhood-wxl',
    [string]$ServerData = '',
    [string]$Python = ''
)

$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
if (-not $ServerData) {
    $ServerData = Join-Path $repoRoot 'env/dist/bin/data'
}
if (-not $Python) {
    $Python = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
}
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'Pass -Python with a Python executable that has NumPy and Pillow installed.'
}
if ($Action -eq 'validate') {
    & $Python (Join-Path $PSScriptRoot 'pixelmon/validate.py')
} else {
    & $Python (Join-Path $PSScriptRoot 'pixelmon/deploy.py') $Action --client $Client --server-data $ServerData
}
if ($LASTEXITCODE -ne 0) {
    throw "Battlemon 3D $Action failed (exit $LASTEXITCODE)."
}
