param(
    [switch]$Recreate
)

$ErrorActionPreference = 'Stop'

Write-Host "[setup] Starting environment setup..." -ForegroundColor Cyan

$venvPath = Join-Path $PSScriptRoot ".venv"

if ($Recreate -and (Test-Path $venvPath)) {
    Write-Host "[setup] Removing existing .venv..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $venvPath
}

if (-not (Test-Path $venvPath)) {
    Write-Host "[setup] Creating virtual environment (.venv)..." -ForegroundColor Cyan
    python -m venv .venv
}

$activate = Join-Path $venvPath "Scripts\Activate.ps1"
if (-not (Test-Path $activate)) {
    throw "Activation script not found: $activate"
}

Write-Host "[setup] Activating venv..." -ForegroundColor Cyan
. $activate

Write-Host "[setup] Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

Write-Host "[setup] Installing dependencies from requirements.txt..." -ForegroundColor Cyan
pip install -r requirements.txt

Write-Host "[setup] Done. To run: 'python main.py' (venv active)" -ForegroundColor Green
