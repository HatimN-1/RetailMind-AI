$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Environnement Python introuvable : $python"
}

$env:SPARK_HOME = (& $python -c "import pyspark; from pathlib import Path; print(Path(pyspark.__file__).parent)").Trim()
$env:PYSPARK_PYTHON = $python

Write-Host "Spark : $env:SPARK_HOME"
& $python -m retailmind.spark_etl --master "local[2]"

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
