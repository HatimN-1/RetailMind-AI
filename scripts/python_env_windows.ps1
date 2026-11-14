# Dot source this script from another PowerShell script. Works with user .venv in parent.
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$localPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
$parentPython = Join-Path (Split-Path $projectRoot -Parent) '.venv\Scripts\python.exe'
if (Test-Path $localPython) { $pythonExe = $localPython }
elseif (Test-Path $parentPython) { $pythonExe = $parentPython }
else { throw "Python virtualenv introuvable dans $projectRoot ou son parent. Voir DEMARRAGE_V2_WINDOWS.md" }
Set-Location $projectRoot
