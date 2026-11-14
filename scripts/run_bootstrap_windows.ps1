$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'python_env_windows.ps1')
& $pythonExe -m retailmind.bootstrap --rows 5000
