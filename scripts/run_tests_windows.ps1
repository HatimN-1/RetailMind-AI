$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'python_env_windows.ps1')

$env:TEMP = Join-Path $projectRoot '.test-temp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null

# Detect the PySpark installation used by this virtual environment.
$sparkPath = & $pythonExe -c "import importlib.util; from pathlib import Path; spec = importlib.util.find_spec('pyspark'); print(Path(spec.origin).parent if spec else '')"

if ($LASTEXITCODE -ne 0) {
    throw "Impossible de détecter PySpark"
}

if ($sparkPath) {
    $env:SPARK_HOME = $sparkPath.Trim()
    $env:PYSPARK_PYTHON = $pythonExe
    Write-Host "SPARK_HOME = $env:SPARK_HOME"
}

& $pythonExe -m pytest
exit $LASTEXITCODE
