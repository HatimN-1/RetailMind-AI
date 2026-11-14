$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$local = '.\.venv\Scripts\python.exe'
$parent = '..\.venv\Scripts\python.exe'
if (Test-Path $local) { $python = $local }
elseif (Test-Path $parent) { $python = $parent }
else {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
    )
    $base = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $base) { throw 'Python 3.11/3.12 introuvable. Installer Python ou corriger son chemin.' }
    & $base -m venv .venv
    $python = $local
}
& $python -m pip install -e '.[dev]'
& $python -m retailmind.bootstrap --rows 5000
& $python -m pytest
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host 'Node.js/npm non trouve. Installer Node.js LTS : https://nodejs.org' -ForegroundColor Yellow
} else {
    Set-Location frontend
    npm install
    Write-Host 'Pour demarrer : Terminal 1 scripts/run_api_windows.ps1 ; Terminal 2 cd frontend ; npm run dev'
}
