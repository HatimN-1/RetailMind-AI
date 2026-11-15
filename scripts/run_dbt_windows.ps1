$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$dbtDir = Join-Path $root "dbt"
$dbtExe = Join-Path $root ".venv\Scripts\dbt.exe"
$python = Join-Path $root ".venv\Scripts\python.exe"
$parquet = Join-Path $root "data\curated\spark_transactions.parquet"

if (-not (Test-Path $dbtExe -PathType Leaf)) {
    throw 'dbt introuvable. Installer : .\.venv\Scripts\python.exe -m pip install -e ".[analytics]"'
}
if (-not (Test-Path $parquet -PathType Container) -or
    @(Get-ChildItem -Path $parquet -Filter "*.parquet" -File -ErrorAction SilentlyContinue).Count -eq 0) {
    throw "Parquet PySpark introuvable : $parquet. Executer scripts/run_spark_windows.ps1 d'abord."
}

New-Item -ItemType Directory -Force -Path (Join-Path $root "data\marts") | Out-Null

# The profile and read_parquet source use paths relative to the dbt working directory.
Push-Location $dbtDir
try {
    & $dbtExe build --project-dir . --profiles-dir .
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}

& $python (Join-Path $root "scripts\verify_dbt.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
