$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$venv = Join-Path $root ".venv"
$python = Join-Path $venv "Scripts\python.exe"

function Resolve-Python {
    # Prefer the launcher, then python.exe, so a PATH without Python still works.
    foreach ($candidate in @(@("py", "-3"), @("python"), @("python3"))) {
        $command = $candidate[0]
        try {
            $args = @()
            if ($candidate.Count -gt 1) { $args += $candidate[1..($candidate.Count - 1)] }
            $args += "-c", "import sys; print(sys.executable)"
            $found = & $command @args 2>$null
            if ($LASTEXITCODE -eq 0 -and $found) { return $found.Trim() }
        } catch {
            continue
        }
    }
    # Last resort: the standard per-user install roots on Windows.
    $globs = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python3*\python.exe"),
        (Join-Path $env:ProgramFiles "Python3*\python.exe")
    )
    foreach ($pattern in $globs) {
        $hit = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue |
               Sort-Object FullName -Descending | Select-Object -First 1
        if ($hit) { return $hit.FullName }
    }
    throw "No Python interpreter found. Install Python 3.11+ and ensure 'py' or 'python' is on PATH."
}

if (-not (Test-Path $python)) {
    $base = Resolve-Python
    Write-Host "Creating virtual environment at .venv using $base ..." -ForegroundColor Cyan
    & $base -m venv $venv
}

Write-Host "Installing Python dependencies from backend\requirements.txt ..." -ForegroundColor Cyan
& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $root "backend\requirements.txt")
& $python -m pip install -r (Join-Path $root "backend\requirements-dev.txt")

Write-Host "Installing frontend dependencies ..." -ForegroundColor Cyan
Push-Location (Join-Path $root "frontend")
try { npm install } finally { Pop-Location }

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "  Backend : .\.venv\Scripts\python.exe -m backend --port 8000"
Write-Host "  Frontend: .\run-frontend.ps1"
Write-Host "  Tests   : .\.venv\Scripts\python.exe -m pytest"