# run_ci.ps1 - one-click test + coverage + quality gate
# Usage: .\run_ci.ps1   (run at project root)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

Write-Host "==> Running pytest (coverage gate >=90%)..."
& "venv\Scripts\python.exe" -m pytest
if ($LASTEXITCODE -ne 0) {
    Write-Error "CI gate failed (tests failed or coverage < 90%)"
    exit 1
}
Write-Host "==> CI passed OK"