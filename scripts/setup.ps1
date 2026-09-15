# FinSight AI — First-Time Setup Script (Windows PowerShell)
# Run this ONCE after cloning the repository.
# Usage: .\scripts\setup.ps1
# ─────────────────────────────────────────────────────────────

param(
    [switch]$SkipFrontend,
    [switch]$SkipBackend
)

Write-Host ""
Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       FinSight AI — First-Time Setup       ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = Split-Path -Parent $PSScriptRoot

# ─── Backend Setup ───────────────────────────────────────────
if (-not $SkipBackend) {
    Write-Host "📦 [1/4] Setting up Backend (Python + FastAPI)..." -ForegroundColor Yellow

    $BackendDir = Join-Path $ProjectRoot "backend"
    Set-Location $BackendDir

    # Create virtual environment
    if (-not (Test-Path ".venv")) {
        Write-Host "  → Creating Python virtual environment..." -ForegroundColor Gray
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  ✗ ERROR: Could not create virtual environment. Make sure Python 3.10+ is installed." -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "  → Virtual environment already exists, skipping." -ForegroundColor Gray
    }

    # Install Python dependencies
    Write-Host "  → Installing Python dependencies from requirements.txt..." -ForegroundColor Gray
    & ".venv\Scripts\python.exe" -m pip install --upgrade pip -q
    & ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ ERROR: pip install failed. Check requirements.txt and your internet connection." -ForegroundColor Red
        exit 1
    }

    # Create required directories
    Write-Host "  → Creating required data directories..." -ForegroundColor Gray
    $dirs = @("uploads", "chroma_data", "cache")
    foreach ($dir in $dirs) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Host "    Created: $dir/" -ForegroundColor DarkGray
        }
    }

    # Copy .env.example → .env if not present
    if (-not (Test-Path ".env")) {
        Write-Host "  → Copying .env.example → .env (fill in your API keys!)" -ForegroundColor Gray
        Copy-Item ".env.example" ".env"
    }

    Write-Host "  ✓ Backend setup complete!" -ForegroundColor Green
    Write-Host ""
}

# ─── Frontend Setup ──────────────────────────────────────────
if (-not $SkipFrontend) {
    Write-Host "🌐 [2/4] Setting up Frontend (React + Vite)..." -ForegroundColor Yellow

    $FrontendDir = Join-Path $ProjectRoot "frontend"
    Set-Location $FrontendDir

    # Check Node.js
    try {
        $nodeVersion = node --version 2>&1
        Write-Host "  → Node.js detected: $nodeVersion" -ForegroundColor Gray
    } catch {
        Write-Host "  ✗ ERROR: Node.js not found. Install from https://nodejs.org (LTS version)." -ForegroundColor Red
        exit 1
    }

    # Install Node dependencies
    Write-Host "  → Running npm install..." -ForegroundColor Gray
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ ERROR: npm install failed." -ForegroundColor Red
        exit 1
    }

    # Copy .env.example → .env if not present
    if (-not (Test-Path ".env")) {
        Write-Host "  → Copying .env.example → .env (fill in your Firebase config!)" -ForegroundColor Gray
        Copy-Item ".env.example" ".env"
    }

    Write-Host "  ✓ Frontend setup complete!" -ForegroundColor Green
    Write-Host ""
}

# ─── Final instructions ──────────────────────────────────────
Set-Location $ProjectRoot

Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║           ✓ Setup Complete!                ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "📋 NEXT STEPS:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Fill in your API keys in: backend\.env" -ForegroundColor White
Write-Host "     Required: GEMINI_API_KEY (free at https://aistudio.google.com/app/apikey)" -ForegroundColor DarkGray
Write-Host "     Optional: GROQ_API_KEY   (free at https://console.groq.com)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  2. Fill in Firebase config in: frontend\.env" -ForegroundColor White
Write-Host "     Get from: Firebase Console → Project Settings → Web App → Config" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  3. Place your Firebase service account key at: backend\serviceAccountKey.json" -ForegroundColor White
Write-Host "     Get from: Firebase Console → Project Settings → Service Accounts → Generate Key" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  4. Start the project (see QUICKSTART.md):" -ForegroundColor White
Write-Host "     Terminal 1 (Backend):  cd backend && .venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000" -ForegroundColor DarkGray
Write-Host "     Terminal 2 (Frontend): cd frontend && npm run dev" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  5. Open http://localhost:5173 in your browser." -ForegroundColor White
Write-Host ""
