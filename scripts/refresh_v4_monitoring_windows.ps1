# V4.5.2: explicit operator-side refresh; never triggers or clears an Airflow DAG.
param(
    [ValidateRange(1, 20)][int]$Limit = 10,
    [switch]$SkipData
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'python_env_windows.ps1')

$arguments = @('scripts/export_v4_monitoring.py', '--limit', [string]$Limit)
if ($SkipData) { $arguments += '--skip-data' }
& $pythonExe @arguments
if ($LASTEXITCODE -ne 0) {
    throw 'Echec de l export Airflow : l ancien instantane reste intact.'
}
Write-Host 'Instantane mis a jour. React relit ce fichier toutes les 60 s ; le bouton Relire est immediat.'
