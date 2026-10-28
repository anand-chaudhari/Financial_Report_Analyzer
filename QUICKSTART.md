# 🚀 FinSight AI — Quick Start Guide (Localhost Execution)

> **Note**: You **DO NOT** need to re-install `requirements.txt` or `npm install` every time you restart the project! You only need to run the start commands listed below.

---

## 📌 Summary: How FinSight AI Works on Localhost

FinSight AI runs **100% locally** on your machine:
- **Backend (FastAPI)**: Serves API requests on `http://localhost:8000` and processes 500+ page PDFs, Word files (DOCX), and spreadsheets (CSV/TSV) in the background using a local thread pool worker.
- **Frontend (React + Vite)**: Displays the interactive analyst interface on `http://localhost:5173` with real-time SSE streaming and status polling.

---

## 🏃 How to Start the Project (Step-by-Step)

Open **two separate terminal windows** on your machine.

---

### Terminal 1: Backend Server (FastAPI)

#### Why `python -m uvicorn` instead of `uvicorn`?
> ⚠️ **Windows Application Control Notice**: On Windows, running `uvicorn.exe` directly gets blocked with `"An Application Control policy has blocked this file"`. Calling `python -m uvicorn` runs directly through the trusted Python interpreter, bypassing this block cleanly and reliably.

#### 🪟 Windows (PowerShell / Command Prompt)

**Option A (Recommended — Direct 1-Click / Copy-Paste):**
```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Option B (If your `.venv` is already activated in terminal):**
```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 🍎 macOS / 🐧 Linux
```bash
# 1. Go to backend folder
cd backend

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Start the FastAPI server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

* 📡 **Backend API URL**: `http://localhost:8000`
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
   Financial_Report_Analyzer/backend/serviceAccountKey.json
   ```
5. Restart Terminal 1 (Backend).

---

## 🧪 Testing Document Uploads (PDF, DOCX, CSV)

1. Open `http://localhost:5173` in your browser and log in.
2. Go to the **Upload Report** page.
3. Drag and drop any supported financial filing:
   - **PDF**: SEC 10-K, 10-Q, or full 500-page annual report (up to 200 MB).
   - **DOCX**: Executive financial reviews with headings and tables.
   - **CSV / TSV**: Multi-year financial statements with comma or tab delimiters.
4. Click **Process Document**.
5. **Notice what happens**:
   - The upload completes in **under 1 second**.
   - You can watch the real-time progress bar: `Uploading` → `Queued` → `Analyzing` → `Extracting` → `Embedding` → `Indexing` → `Ready`.
   - Re-uploading the same file completes **instantly (< 1 second)** due to verified vector cache fingerprinting (`v2.2.0`).
   - You can click around **Dashboard**, **Analytics**, and **AI Analyst** while processing continues in the background without any lag!

---

## 🌐 Testing Automated External Web Search & Verified Citation Links

1. Go to the **AI Analyst** page.
2. With an active document open (e.g. SBI annual report), ask a question about a peer company:
   - *"What was HDFC Bank's net profit in 2024?"*
   - *"How does this company compare with TCS?"*
   - *"What is Apple's current stock price and performance today?"*
3. **Notice what happens**:
   - In default **Auto** mode, FinSight AI automatically detects that the question is about an external entity or not in the document.
   - It executes a live web discovery pass and retrieves real-time Yahoo Finance quotes.
   - The generated response includes **clickable Markdown links** (`[Publisher](URL)`) and a dedicated **`### 🌐 Verified External Sources & Links`** section so you can cross-check figures independently without blindly trusting AI outputs.

4. **Try `@websearch` Mode directly**:
   - Click the **`🚀 @websearch`** button in the search mode bar, or type **`@websearch What is Microsoft's current market cap?`** in the chat input.
   - Local document RAG is completely bypassed; the answer is synthesized **exclusively from live AI + Web Search** with zero PDF page citations.

---

## ❓ Frequently Asked Questions

### 1. Do I need to run `pip install` or `npm install` every time?
**NO.** Dependencies are saved in your `.venv` and `node_modules` folders. You only run install commands if new packages are added to `requirements.txt` or `package.json`.

### 2. What does `ERR_CONNECTION_REFUSED` mean?
This means Terminal 1 (Backend) is not running. Make sure Terminal 1 is active and displays:
```
INFO: Uvicorn running on http://0.0.0.0:8000
```

### 3. How do I push my changes to GitHub if permission is denied?
If your terminal gives a permission error while pushing to GitHub, authenticate using the GitHub CLI:
```bash
gh auth login
```
Select `GitHub.com` → `HTTPS` → `Login with a web browser` → authorize with your GitHub account, then run `git push origin main`.

### 4. How do I stop both servers?
Go to each terminal window and press **`Ctrl + C`**.
