#!/usr/bin/env bash
# FinSight AI — First-Time Setup Script (macOS / Linux)
# Run this ONCE after cloning the repository.
# Usage: bash scripts/setup.sh
# ─────────────────────────────────────────────────────────────

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       FinSight AI — First-Time Setup       ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
echo ""

# ─── Backend Setup ───────────────────────────────────────────
echo -e "${YELLOW}📦 [1/4] Setting up Backend (Python + FastAPI)...${NC}"

cd "$PROJECT_ROOT/backend"

# Check Python version
PYTHON_CMD=""
for cmd in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PY_VER=$("$cmd" -c "import sys; print(sys.version_info >= (3, 10))" 2>/dev/null)
        if [ "$PY_VER" = "True" ]; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}  ✗ ERROR: Python 3.10+ not found. Install from https://python.org${NC}"
    exit 1
fi

echo -e "${GRAY}  → Python: $($PYTHON_CMD --version)${NC}"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo -e "${GRAY}  → Creating Python virtual environment...${NC}"
    "$PYTHON_CMD" -m venv .venv
else
    echo -e "${GRAY}  → Virtual environment already exists, skipping.${NC}"
fi

# Activate and install
echo -e "${GRAY}  → Installing Python dependencies from requirements.txt...${NC}"
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt

# Create required directories
echo -e "${GRAY}  → Creating required data directories...${NC}"
for dir in uploads chroma_data cache; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo -e "${GRAY}    Created: $dir/${NC}"
    fi
done

# Copy .env.example → .env if not present
if [ ! -f ".env" ]; then
    echo -e "${GRAY}  → Copying .env.example → .env (fill in your API keys!)${NC}"
    cp .env.example .env
fi

echo -e "${GREEN}  ✓ Backend setup complete!${NC}"
echo ""

# ─── Frontend Setup ──────────────────────────────────────────
echo -e "${YELLOW}🌐 [2/4] Setting up Frontend (React + Vite)...${NC}"

cd "$PROJECT_ROOT/frontend"

# Check Node.js
if ! command -v node &>/dev/null; then
    echo -e "${RED}  ✗ ERROR: Node.js not found. Install from https://nodejs.org (LTS version).${NC}"
    exit 1
fi

NODE_VER=$(node --version)
echo -e "${GRAY}  → Node.js detected: $NODE_VER${NC}"

# Install Node dependencies
echo -e "${GRAY}  → Running npm install...${NC}"
npm install

# Copy .env.example → .env if not present
if [ ! -f ".env" ]; then
    echo -e "${GRAY}  → Copying .env.example → .env (fill in your Firebase config!)${NC}"
    cp .env.example .env
fi

echo -e "${GREEN}  ✓ Frontend setup complete!${NC}"
echo ""

# ─── Final instructions ──────────────────────────────────────
cd "$PROJECT_ROOT"

echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           ✓ Setup Complete!                ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}📋 NEXT STEPS:${NC}"
echo ""
echo "  1. Fill in your API keys in: backend/.env"
echo "     Required: GEMINI_API_KEY (free at https://aistudio.google.com/app/apikey)"
echo "     Optional: GROQ_API_KEY   (free at https://console.groq.com)"
echo ""
echo "  2. Fill in Firebase config in: frontend/.env"
echo "     Get from: Firebase Console → Project Settings → Web App → Config"
echo ""
echo "  3. Place your Firebase service account key at: backend/serviceAccountKey.json"
echo "     Get from: Firebase Console → Project Settings → Service Accounts → Generate Key"
echo ""
echo "  4. Start the project (see QUICKSTART.md):"
echo "     Terminal 1 (Backend):  cd backend && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo "     Terminal 2 (Frontend): cd frontend && npm run dev"
echo ""
echo "  5. Open http://localhost:5173 in your browser."
echo ""
