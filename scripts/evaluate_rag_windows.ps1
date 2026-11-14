param([ValidateSet('qdrant','tfidf')][string]$Backend = 'qdrant')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'python_env_windows.ps1')
& $pythonExe -m retailmind.cli evaluate-rag --backend $Backend --output "data/reports/rag_$Backend.json"
exit $LASTEXITCODE
