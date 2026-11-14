$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'python_env_windows.ps1')
& $pythonExe -m retailmind.cli index
exit $LASTEXITCODE
