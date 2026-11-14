$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'python_env_windows.ps1')
& $pythonExe -m uvicorn retailmind.api:app --reload --host 127.0.0.1 --port 8000
