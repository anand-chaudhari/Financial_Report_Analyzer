# 📘 FinSight AI — Complete Setup Guide

> **Who is this for?**
> This guide is for **anyone who just cloned this repository** and wants to run FinSight AI on their own computer from scratch. No prior experience with FastAPI or React is assumed. Just follow every step in order.

---

## 📋 What You Will Need Before Starting

Before you touch any code, make sure you have these things ready:

| What You Need | Where to Get It | Free? |
|---|---|---|
| **Python 3.10 or higher** | [python.org/downloads](https://www.python.org/downloads/) | ✅ Free |
| **Node.js LTS (v18 or higher)** | [nodejs.org](https://nodejs.org) | ✅ Free |
| **Groq API Key** | [console.groq.com](https://console.groq.com) → Sign up → API Keys | ✅ Free |
| **NVIDIA NIM API Key** | [build.nvidia.com](https://build.nvidia.com) → Sign in → Get API Key | ✅ Free |
| **Gemini API Key** | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) | ✅ Free |
| **Firebase Project** (for login) | [console.firebase.google.com](https://console.firebase.google.com) | ✅ Free |

> 💡 **You only need ONE LLM key to start.** The app will use Gemini first, then fall back to NVIDIA NIM, then Groq. But having all three gives you automatic failover.

---

## 🗂️ Step 0 — Understand the Project Structure

When you clone the repo, you will see this:

```
FINANCE_REPORT_ANALYZER_AI/
│
├── backend/          ← Python + FastAPI (the AI brain)
│   ├── app/          ← All the backend logic
│   ├── .env          ← YOUR secret API keys go here (you create this)
│   ├── .env.example  ← Template to copy from
│   ├── requirements.txt  ← Python packages to install
│   └── serviceAccountKey.json  ← Firebase key (you download this)
│
├── frontend/         ← React + Vite (the web interface)
│   ├── src/          ← All the UI code
│   ├── .env          ← YOUR Firebase config goes here (you create this)
│   └── .env.example  ← Template to copy from
│
├── scripts/
│   ├── setup.ps1     ← Automated setup for Windows
│   └── setup.sh      ← Automated setup for macOS/Linux
│
├── SETUP.md          ← You are reading this!
└── QUICKSTART.md     ← Short version for daily use after setup
```

The app runs in **two separate terminals**:
- **Terminal 1** → runs the backend (Python API on port `8000`)
- **Terminal 2** → runs the frontend (React website on port `5173`)

---

## 🪟 WINDOWS USERS — Step-by-Step

---

### ✅ Step 1 — Install Python

1. Open [python.org/downloads](https://www.python.org/downloads/)
2. Download **Python 3.12** (the latest 3.x version)
3. Run the installer
4. ⚠️ **IMPORTANT**: On the first screen, check the box **"Add Python to PATH"** before clicking Install
5. After install, verify it works — open PowerShell and type:
   ```powershell
   python --version
   ```
   You should see something like: `Python 3.12.x`

---

### ✅ Step 2 — Install Node.js

1. Open [nodejs.org](https://nodejs.org)
2. Download the **LTS** version (the one that says "Recommended For Most Users")
3. Run the installer (just click Next → Next → Install)
4. After install, verify:
   ```powershell
   node --version
   npm --version
   ```
   You should see version numbers like `v20.x.x` and `10.x.x`

---

### ✅ Step 3 — Clone the Repository

Open **PowerShell** and run:

```powershell
git clone https://github.com/anand-chaudhari/Financial_Report_Analyzer.git
cd Financial_Report_Analyzer
```

> 🔁 If you already cloned it, just navigate into the folder:
> ```powershell
> cd C:\Users\YourName\Financial_Report_Analyzer
> ```

---

### ✅ Step 4 — Run the Automated Setup (Installs Everything)

Still in the project root folder, run:

```powershell
.\scripts\setup.ps1
```

> ⚠️ If you see an error about "running scripts is disabled", run this first, then try again:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

This script will automatically:
- ✅ Create a Python virtual environment in `backend/.venv/`
- ✅ Install all Python packages from `requirements.txt`
- ✅ Run `npm install` for the frontend
- ✅ Create the data folders (`uploads/`, `chroma_data/`, `cache/`)
- ✅ Copy the `.env.example` template files to `.env`

> 💡 **This may take 3–5 minutes** on the first run because it downloads the AI embedding model (~90 MB). Be patient!

---

### ✅ Step 5 — Set Up Your API Keys (Backend)

After Step 4, open the file `backend\.env` in any text editor (Notepad, VS Code, etc.).

You will see this:

```env
ENVIRONMENT=development
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000

GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
NVIDIA_API_KEY=your_nvidia_api_key_here
LLM_PROVIDER=gemini

CHROMA_PERSIST_DIRECTORY=./chroma_data
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
MAX_UPLOAD_SIZE_MB=250
MAX_PDF_PAGES=2000
PDF_PROCESSING_TIMEOUT_SEC=600

FIREBASE_CREDENTIALS_PATH=./serviceAccountKey.json
FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
```

**Replace the placeholder values with your real keys:**

```env
GEMINI_API_KEY=AIzaSy...your_real_gemini_key...
GROQ_API_KEY=gsk_...your_real_groq_key...
NVIDIA_API_KEY=nvapi-...your_real_nvidia_key...
FIREBASE_STORAGE_BUCKET=your-firebase-project-id.appspot.com
```

**Where to find each key:**

| Key | Steps |
|---|---|
| `GEMINI_API_KEY` | Go to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) → Click "Create API Key" → Copy |
| `GROQ_API_KEY` | Go to [console.groq.com](https://console.groq.com) → Log in → API Keys → Create → Copy |
| `NVIDIA_API_KEY` | Go to [build.nvidia.com](https://build.nvidia.com) → Pick any model → Click "Get API Key" → Copy |
| `FIREBASE_STORAGE_BUCKET` | Firebase Console → Your Project → Project Settings → General → scroll down to find your project ID → it will be `your-project-id.appspot.com` |

Save the file after editing.

---

### ✅ Step 6 — Set Up Firebase Service Account Key (Backend)

This key lets the backend verify user logins securely.

1. Go to [console.firebase.google.com](https://console.firebase.google.com)
2. Select **your Firebase project**
3. Click the ⚙️ gear icon → **Project Settings**
4. Click the **"Service accounts"** tab
5. Click **"Generate new private key"** button
6. A JSON file will download (something like `financereportai-firebase-adminsdk-xxx.json`)
7. **Rename it** to exactly: `serviceAccountKey.json`
8. **Move it** into the `backend/` folder:
   ```
   FINANCE_REPORT_ANALYZER_AI\
   └── backend\
       └── serviceAccountKey.json   ← Place it here
   ```

> 🔒 This file is **already in `.gitignore`** — it will never be accidentally pushed to GitHub.

---

### ✅ Step 7 — Set Up Firebase Config (Frontend)

After Step 4, open the file `frontend\.env` in any text editor.

You will see:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_FIREBASE_API_KEY=your_firebase_api_key_here
VITE_FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=your_messaging_sender_id
VITE_FIREBASE_APP_ID=your_firebase_app_id
VITE_FIREBASE_MEASUREMENT_ID=G-XXXXXXXXXX
```

**Where to find these values:**
1. Go to [console.firebase.google.com](https://console.firebase.google.com)
2. Select your project
3. Click the ⚙️ gear icon → **Project Settings**
4. Scroll down to **"Your apps"** section
5. Click on your **Web app** (the `</>` icon)
6. You will see a block that looks like this — copy each value:

```js
const firebaseConfig = {
  apiKey: "AIzaSy...",             // → VITE_FIREBASE_API_KEY
  authDomain: "xxx.firebaseapp.com", // → VITE_FIREBASE_AUTH_DOMAIN
  projectId: "xxx",                  // → VITE_FIREBASE_PROJECT_ID
  storageBucket: "xxx.appspot.com",  // → VITE_FIREBASE_STORAGE_BUCKET
  messagingSenderId: "123456789",    // → VITE_FIREBASE_MESSAGING_SENDER_ID
  appId: "1:123:web:abc",           // → VITE_FIREBASE_APP_ID
  measurementId: "G-XXXXXXX"        // → VITE_FIREBASE_MEASUREMENT_ID
};
```

**Leave `VITE_API_BASE_URL=http://localhost:8000` exactly as-is** — this tells the frontend to talk to your local backend.

Save the file after editing.

---

### ✅ Step 8 — Start the Backend Server (Terminal 1)

Open a **new PowerShell window** and run these commands:

```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

✅ **Success looks like this:**
```
INFO:     Started server process [XXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

You can also verify it's working by opening: [http://localhost:8000/docs](http://localhost:8000/docs) — you should see the API documentation page.

> ⚠️ **Keep this terminal open and running.** If you close it, the backend stops.

---

### ✅ Step 9 — Start the Frontend App (Terminal 2)

Open a **second new PowerShell window** and run:

```powershell
cd frontend
npm run dev
```

✅ **Success looks like this:**
```
  VITE v5.x.x  ready in XXX ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
```

> ⚠️ **Keep this terminal open too.** If you close it, the website stops.

---

### ✅ Step 10 — Open the App in Your Browser

Open your browser and go to:

> ### 🌐 [http://localhost:5173](http://localhost:5173)

You should see the **FinSight AI login page**. Create an account (or log in) and start uploading financial reports!

---

## 🍎 macOS / 🐧 LINUX USERS

Same steps as Windows, but with these differences:

**Step 1 — Install Python:**
```bash
# macOS (with Homebrew)
brew install python@3.12

# Ubuntu/Debian
sudo apt install python3.12 python3.12-venv python3-pip
```

**Step 4 — Run Automated Setup:**
```bash
bash scripts/setup.sh
```

**Step 8 — Start Backend:**
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Step 9 — Start Frontend:**
```bash
cd frontend
npm run dev
```

Everything else (API keys, Firebase setup, browser URL) is identical to the Windows steps.

---

## ⚡ After First Setup — How to Start Every Day

You already installed everything. From now on, you only need **two commands** each time:

**Terminal 1 (Backend):**
```powershell
# Windows
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
```bash
# macOS/Linux
cd backend
source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```

Then open **http://localhost:5173**. That's it!

---

## ❌ Common Errors & Fixes

### `ERR_CONNECTION_REFUSED` in the browser
**Cause:** The backend (Terminal 1) is not running.
**Fix:** Go to Terminal 1 and check if uvicorn is running. If not, re-run the backend start command.

---

### `ModuleNotFoundError: No module named 'fastapi'`
**Cause:** You are using the system Python instead of the virtual environment.
**Fix:** Make sure you use `.venv\Scripts\python.exe` (Windows) or activate the venv first.

---

### `[WinError 10013] An attempt was made to access a socket in a way forbidden`
**Cause:** Port `8000` is blocked or already in use on your machine.
**Fix:** Change the port number in the start command AND in `backend/.env`:
```powershell
# Use port 8001 instead
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```
Also update `frontend/.env`:
```
VITE_API_BASE_URL=http://localhost:8001
```

---

### `GROQ API Error` or `Gemini 503 Service Unavailable`
**Cause:** The API key is wrong or the AI service is temporarily overloaded.
**Fix:** 
- Double-check your key in `backend/.env` has no extra spaces
- The app has automatic fallback — it will try NVIDIA NIM, then Groq automatically
- Wait a minute and try again

---

### Firebase Authentication Error at Login
**Cause:** Either `serviceAccountKey.json` is missing or the frontend Firebase config is wrong.
**Fix:**
- Confirm `backend/serviceAccountKey.json` exists
- Confirm all `VITE_FIREBASE_*` values in `frontend/.env` exactly match your Firebase console

---

### First upload takes very long (1–2 minutes)
**This is normal on first run!** The app downloads the AI embedding model (`~90 MB`) to your local cache. All subsequent uploads will be much faster.

---

## 🚀 Push Your Changes to GitHub

Once you are happy with your local setup and want to save your work to GitHub, run these commands:

### First Time (if you haven't set up the remote yet):
```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

### Every Time After (normal push):
```bash
# Check what files have changed
git status

# Stage all changed files
git add .

# Write a commit message describing what you changed
git commit -m "describe what you changed here"

# Push to GitHub
git push
```

### Push Specific Files Only (not everything):
```bash
# Stage only specific files
git add backend/app/rag/rag_service.py
git add frontend/src/pages/AnalystPage.tsx

# Then commit and push
git commit -m "fix: improve RAG response quality"
git push
```

### ⚠️ Before Every Push — Safety Checklist:
Run this to make sure you are NOT accidentally pushing any secrets:

```bash
git status
```

Check the output. You should **NEVER** see these files in "Changes to be committed":
- ❌ `backend/.env`
- ❌ `frontend/.env`
- ❌ `frontend/.env.production`
- ❌ `backend/serviceAccountKey.json`

If you see any of them, remove them from staging before pushing:
```bash
git reset HEAD backend/.env
git reset HEAD backend/serviceAccountKey.json
git reset HEAD frontend/.env
```

✅ **It is safe to push:**
- `backend/.env.example`
- `frontend/.env.example`
- All `*.py`, `*.ts`, `*.tsx` source files
- `README.md`, `SETUP.md`, `QUICKSTART.md`
- `scripts/setup.ps1`, `scripts/setup.sh`

---

## 📁 Files Summary — What Goes Where

| File | Committed to GitHub? | Contains |
|---|---|---|
| `backend/.env` | ❌ NO (gitignored) | Your real API keys |
| `frontend/.env` | ❌ NO (gitignored) | Your real Firebase config |
| `backend/serviceAccountKey.json` | ❌ NO (gitignored) | Your real Firebase private key |
| `backend/.env.example` | ✅ YES | Template with placeholder values |
| `frontend/.env.example` | ✅ YES | Template with placeholder values |
| All source code (`*.py`, `*.tsx`) | ✅ YES | Application logic |

---

## 📞 Need Help?

If something is not working after following this guide:

1. Check the **terminal output** — error messages tell you exactly what went wrong
2. Check the **Common Errors** section above
3. Make sure both terminals (backend + frontend) are running at the same time
4. Try restarting both terminals and running the start commands again

---

*Guide written for FinSight AI v1.0 — Localhost Edition*
