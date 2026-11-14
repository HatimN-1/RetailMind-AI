$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'python_env_windows.ps1')
# Preserve packaged datasets, models and metrics: no bootstrap/retraining here.
& $pythonExe -m pip install -e '.[dev,rag,agent]'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host 'RAG installe. Arreter FastAPI avant indexation Qdrant locale.'
Write-Host 'Ensuite : scripts/index_rag_windows.ps1 puis scripts/run_api_windows.ps1'
