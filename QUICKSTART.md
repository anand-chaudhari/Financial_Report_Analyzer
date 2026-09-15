# 🚀 FinSight AI — Quick Start Guide (Localhost Execution)

> **Note**: You **DO NOT** need to re-install `requirements.txt` or `npm install` every time you restart the project! You only need to run the start commands listed below.

---

## 📌 Summary: How FinSight AI Works on Localhost

FinSight AI runs **100% locally** on your machine.
- **Backend (FastAPI)**: Serves API requests on `http://localhost:8000` and processes 600+ page PDFs in the background using a local thread pool worker.
- **Frontend (React + Vite)**: Displays the analyst interface on `http://localhost:5173` and polls job status in real-time.

---

## 🏃 How to Start the Project (Step-by-Step)

Open **two separate terminal windows** on your machine.

---

### Terminal 1: Backend Server (FastAPI)

#### Why this command?
We use `python -m uvicorn app.main:app` without `--reload` on Windows to prevent sub-process permission issues while maintaining fast multi-threaded execution.

#### 🪟 Windows (PowerShell / Command Prompt)
```powershell
# 1. Go to backend folder
cd backend

# 2. Start the FastAPI server using the virtual environment
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 🍎 macOS / 🐧 Linux
```bash
# 1. Go to backend folder
cd backend

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Start the FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

*  **Backend API URL**: `http://localhost:8000`
* 📖 **Interactive API Specs (Swagger Docs)**: `http://localhost:8000/docs`

---

### Terminal 2: Frontend Application (React + Vite)

#### Why this command?
`npm run dev` launches Vite's lightning-fast development server with hot-module reloading (HMR).

#### 🪟 Windows / 🍎 macOS / 🐧 Linux
```bash
# 1. Go to frontend folder
cd frontend

# 2. Start Vite dev server
npm run dev
```

* 🌐 **Frontend Web Application URL**: `http://localhost:5173`

---

## 🔑 Firebase Credentials Setup (First-Time Only)

The backend uses `serviceAccountKey.json` to verify user logins.

> 💡 **Note**: In development mode (`ENVIRONMENT=development`), if no key is present, dev fallback authentication allows testing locally without blocking. However, to enable full Firebase Auth and Firestore syncing, place your key in `backend/serviceAccountKey.json`.

### How to get your key:
1. Open the [Firebase Console](https://console.firebase.google.com).
2. Select your project → Click ⚙️ **Project Settings** → **Service accounts** tab.
3. Click **"Generate new private key"** to download the JSON file.
4. Move and rename the file to:
   ```
   FINANCE_REPORT_ANALYZER_AI/backend/serviceAccountKey.json
   ```
5. Restart Terminal 1 (Backend).

---

## 🧪 Testing Large PDF Uploads (600+ Pages)

1. Open `http://localhost:5173` in your browser and log in.
2. Go to **Upload Report** page.
3. Drag and drop a large financial report (e.g., 600-page annual report up to 250 MB).
4. Click **Process Document**.
5. **Notice what happens**:
   - The upload completes in **under 1 second**.
   - You are immediately redirected to **My Reports**.
   - A live progress banner appears in the top navigation bar showing progress (`Queued` → `Analyzing` → `Extracting` → `Embedding` → `Indexing` → `Ready`).
   - You can click around **Dashboard**, **Analytics**, **AI Analyst**, and **Settings** while processing continues in the background without any lag!

---

## ❓ Frequently Asked Questions

### 1. Do I need to run `pip install` or `npm install` every time?
**NO.** Dependencies are saved in your `.venv` and `node_modules` folders. You only run install commands if new packages are added to `requirements.txt` or `package.json`.

### 2. What does `ERR_CONNECTION_REFUSED` mean?
This means Terminal 1 (Backend) is not running. Make sure Terminal 1 is active and displays:
```
INFO: Uvicorn running on http://0.0.0.0:8000
```

### 3. Why is the first upload slightly slower?
On the very first run, FinSight AI downloads the lightweight SentenceTransformer embedding model (`sentence-transformers/all-MiniLM-L6-v2`, ~90 MB) to your local cache. This happens only once. All subsequent uploads use the cached model.

### 4. How do I stop both servers?
Go to each terminal window and press **`Ctrl + C`**.
