# Start the TrueIntent FastAPI backend on http://localhost:8000
# Uses the repo-root .venv created by setup.ps1.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "No .venv found. Run .\setup.ps1 first."
}
Write-Host "Starting TrueIntent FastAPI backend on http://localhost:8000..." -ForegroundColor Cyan
Write-Host "Docs: http://localhost:8000/docs   Health: http://localhost:8000/health   Ready: http://localhost:8000/ready" -ForegroundColor DarkGray
& $python -m backend --port 8000