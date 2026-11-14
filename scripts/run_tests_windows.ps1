$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'python_env_windows.ps1')
$env:TEMP = Join-Path $projectRoot '.test-temp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
& $pythonExe -m pytest
exit $LASTEXITCODE
