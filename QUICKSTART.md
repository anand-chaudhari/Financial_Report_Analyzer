# FinSight AI — Quick Start Command Guide

> **Note**: You **DO NOT** need to re-install `requirements.txt` or `npm install` every time! You only need to run the start commands below.

---

## 🚀 How to Start the Project (Copy-Pasteable)

Open **two separate terminals** in your terminal application or IDE.

---

### Terminal 1: Backend Server (FastAPI)

#### Windows (PowerShell / CMD)
```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

#### macOS / Linux
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

*Backend API will be running at*: `http://localhost:8000`  
*Swagger Documentation*: `http://localhost:8000/docs`

---

### Terminal 2: Frontend App (React + Vite)

#### Windows / macOS / Linux
```bash
cd frontend
npm run dev
```

*Frontend Web Application will be running at*: `http://localhost:5173`

---

## ❓ Frequently Asked Questions

### Do I need to run `pip install -r requirements.txt` every time?
**NO.** Packages are already installed inside `.venv`. You only need to run `pip install` if new python packages are added to the project.

### Why did I get `ERR_CONNECTION_REFUSED` in the browser?
This error happens when Terminal 1 (Backend) is closed or not running. Make sure Terminal 1 is open and shows `Uvicorn running on http://127.0.0.1:8000`.

### How do I stop the servers?
Click inside the terminal window and press **`Ctrl + C`**.
