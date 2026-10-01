# Start the TrueIntent React (Vite) portal on http://localhost:5173
$ErrorActionPreference = "Stop"
Push-Location (Join-Path $PSScriptRoot "frontend")
try {
    Write-Host "Starting TrueIntent React (Vite) frontend on http://localhost:5173..." -ForegroundColor Cyan
    npm run dev
} finally {
    Pop-Location
}