param(
    [ValidateSet('inventory', 'sample', 'all', 'validate', 'install', 'remove')]
    [string]$Action = 'sample',
    [string]$Client = 'D:\WoW\Dark-Bro-WXL-COA\Dark-Brotherhood-wxl',
    [string]$Pixelmon = 'F:\_d-bak\_other\Pixelmon-1.21.1-9.4.0-universal',
    [string]$ServerData = '',
    [string]$Output = '',
    [string]$Python = '',
    [string]$Forms = '',
    [switch]$RetryFailed,
    [int]$TimeoutSeconds = 240
)

$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
if (-not $ServerData) { $ServerData = Join-Path $repoRoot 'env/dist/bin/data' }
if (-not $Output) { $Output = Join-Path $PSScriptRoot '../generated/pixelmon-batch' }
if (-not $Python) {
    $Python = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
}
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'Pass -Python with Python 3.10+ and NumPy / Pillow 12.3+ installed.'
}
$arguments = @('--output', $Output, '--client', $Client)
if ($Action -in @('inventory', 'sample', 'all')) {
    $command = if ($Action -eq 'inventory') { 'inventory' } else { 'run' }
    $arguments += @('--pixelmon', $Pixelmon, '--timeout', $TimeoutSeconds)
    if ($Action -eq 'all') { $arguments += '--all' }
    if ($Forms) { $arguments += @('--forms', $Forms) }
    if ($RetryFailed) { $arguments += '--retry-failed' }
    & $Python -X utf8 (Join-Path $PSScriptRoot 'pixelmon/batch.py') $command @arguments
} else {
    $arguments += @('--server-data', $ServerData)
    & $Python -X utf8 (Join-Path $PSScriptRoot 'pixelmon/direct_deploy.py') $Action @arguments
}
if ($LASTEXITCODE -ne 0) { throw "Battlemon batch $Action failed (exit $LASTEXITCODE)." }
