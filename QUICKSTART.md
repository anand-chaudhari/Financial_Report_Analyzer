# FinSight AI — Quick Start Command Guide

> **Note**: You **DO NOT** need to re-install `requirements.txt` or `npm install` every time! You only need to run the start commands below.

---

## 🚀 How to Start the Project Locally (Full Local Stack)

Open **two separate terminals** in your terminal application or IDE.

---

### Terminal 1: Backend Server (FastAPI)

#### Windows (PowerShell / CMD)
```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### macOS / Linux
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
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

> ✅ The frontend `.env` is pre-configured with `VITE_API_BASE_URL=http://localhost:8000/api/v1`  
> All API calls go **directly to your local backend** — Render is NOT involved.

---

## 🔑 First-Time Setup: Firebase Credentials

The backend needs a `serviceAccountKey.json` to verify user logins (Firebase JWT tokens).

**Without this file, every API call returns 401 Unauthorized.**

### How to get it:
1. Go to [Firebase Console](https://console.firebase.google.com) → your project
2. Click ⚙️ **Project Settings** → **Service accounts** tab
3. Click **"Generate new private key"** → Download the JSON file
4. Rename it to `serviceAccountKey.json` and move it to:
   ```
   C:\Users\Anand\FINANCE_REPORT_ANALYZER_AI\backend\serviceAccountKey.json
   ```
5. Restart the backend — done ✅

> ⚠️ Never commit `serviceAccountKey.json` to GitHub — it's already in `.gitignore`.

---

## 🔄 Environment Modes

| Mode | Frontend URL | Backend | Change |
|---|---|---|---|
| **Local Full Stack** | `localhost:5173` | `localhost:8000` (your CPU) | Default — nothing to change |
| **Local Frontend → Render** | `localhost:5173` | Render server | In `frontend/.env`, change URL to `/api/v1` |
| **Production (Firebase)** | `financereportai.web.app` | Render server | Automatic via `.env.production` |

---

## ❓ Frequently Asked Questions

### Do I need to run `pip install -r requirements.txt` every time?
**NO.** Packages are already installed inside `.venv`. You only need to run `pip install` if new python packages are added to the project.

### Why did I get `ERR_CONNECTION_REFUSED`?
The backend Terminal is closed or not running. Make sure Terminal 1 shows:  
`Uvicorn running on http://0.0.0.0:8000`

### Why do I get `401 Unauthorized`?
`serviceAccountKey.json` is missing from the `backend/` folder. Follow the **Firebase Credentials** section above.

### Why is PDF upload slow on first run?
The first upload downloads the AI embedding model (`sentence-transformers/all-MiniLM-L6-v2`, ~90MB) to your local machine. This is a one-time download. Subsequent uploads are fast.

### How do I stop the servers?
Click inside the terminal window and press **`Ctrl + C`**.
