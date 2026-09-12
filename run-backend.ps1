Set-Location backend
Write-Host "Starting TrueIntent FastAPI backend on http://localhost:8000..." -ForegroundColor Cyan
.\venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
