Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "      TrueIntent Development Setup       " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host "[1/2] Setting up Backend Python environment..." -ForegroundColor Yellow
Set-Location backend
if (-not (Test-Path "venv")) {
    python -m venv venv
}
.\venv\Scripts\pip.exe install --upgrade pip
.\venv\Scripts\pip.exe install -r requirements.txt
Set-Location ..

Write-Host "[2/2] Setting up Frontend dependencies..." -ForegroundColor Yellow
Set-Location frontend
npm install
Set-Location ..

Write-Host "==========================================" -ForegroundColor Green
Write-Host " Setup complete! Run backend and frontend:" -ForegroundColor Green
Write-Host "   .\run-backend.ps1" -ForegroundColor Green
Write-Host "   .\run-frontend.ps1" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
