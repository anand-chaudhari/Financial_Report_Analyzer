# 💼 FinSight AI — Localhost-First Autonomous Financial Report Analyzer & Intelligence Platform

[![Vite React](https://img.shields.io/badge/Frontend-React_18_%2B_Vite_%2B_TailwindCSS-06b6d4?style=for-the-badge&logo=react)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_%2B_Python_3.12-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![ChromaDB](https://img.shields.io/badge/Vector_Store-ChromaDB-6366f1?style=for-the-badge)](https://www.trychroma.com/)
[![Groq & Gemini](https://img.shields.io/badge/LLM_Engine-Groq_%2B_NVIDIA_NIM_%2B_Gemini-10b981?style=for-the-badge)](https://groq.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-amber?style=for-the-badge)](https://opensource.org/licenses/MIT)

> **FinSight AI** is a local-first, high-performance financial intelligence application engineered to ingest, parse, index, and analyze massive corporate filings (10-K, 10-Q, annual reports up to **600+ pages / 250 MB**) without freezing your browser or causing backend HTTP timeouts.

---

## 📑 Table of Contents
1. [Why FinSight AI? (Simple Explanation & Design Choices)](#-why-finsight-ai-simple-explanation--design-choices)
2. [System Architecture & Asynchronous Workflow](#-system-architecture--asynchronous-workflow)
3. [Key Features & Features Breakdown](#-key-features--features-breakdown)
4. [Tech Stack & Technical Choices](#-tech-stack--technical-choices)
5. [Complete File & Folder Structure (With Use Cases)](#-complete-file--folder-structure-with-use-cases)
6. [Installation & Local Setup](#-installation--local-setup)
7. [Environment Variables Configuration](#-environment-variables-configuration)
8. [Frequently Asked Questions & Technical Interview Answers](#-frequently-asked-questions--technical-interview-answers)
9. [License](#-license)

---

## 💡 Why FinSight AI? (Simple Explanation & Design Choices)

Processing a 600-page annual report is extremely heavy: it involves reading text, extracting complex accounting tables, running OCR on scanned pages, calculating vector embeddings for thousands of text paragraphs, and storing them in a database.

If a server tries to do all of this inside a standard web request, the browser waits, hits a 5-minute timeout (`AxiosError: timeout of 300000ms exceeded`), and crashes.

FinSight AI solves this architecturally using a **Decoupled Asynchronous Localhost Engine**:

### 🎯 Key Design Choices & "Why We Chose This":

1. **Non-Blocking Instant Upload (< 1 Second Response)**
   - *Why?* The backend receives the file, streams it to local disk, creates a job ID, and returns HTTP 200 immediately. You don't have to sit looking at a spinning loader for 10 minutes.
2. **Local Worker Thread Pool (`ThreadPoolExecutor`)**
   - *Why?* Heavy CPU operations (PDF extraction, OCR, vector embeddings) run on dedicated background threads. This keeps FastAPI's main thread free so normal requests (`GET /dashboard`, `GET /reports`, `GET /analytics`) respond in **< 50ms** even while a 600-page report is indexing in the background.
3. **SHA-256 Instant Hash Reuse**
   - *Why?* If you re-upload a report you already processed, FinSight AI detects the exact file hash and reuses existing indexed vector chunks instantly—zero redundant waiting.
4. **Selective OCR (Smart Scanning)**
   - *Why?* Native text extraction using PyMuPDF is **50x faster** than OCR. We extract native text first; OCR is only executed on pages that are pure scanned images. This cuts unnecessary processing time by up to **95%**.
5. **Memory-Controlled Batching (20 Pages / Batch)**
   - *Why?* Loading a 600-page PDF into RAM all at once can crash your laptop. We extract, chunk, embed, and index in small 20-page batches with automatic garbage collection (`gc.collect()`), keeping RAM usage under 1 GB.
6. **Non-Blocking Status Polling & Persistent Header Progress Banner**
   - *Why?* While a report processes in the background, you can navigate freely across Dashboard, My Reports, AI Analyst, Compare, and Settings. The header progress banner shows real-time progress (`0-100%`) without locking the screen.
7. **Multi-Model LLM Routing (Groq + Gemini + NVIDIA NIM)**
   - *Why?* Groq provides lightning-fast answers (sub-2 seconds). If Groq is rate-limited, the system automatically falls back to NVIDIA NIM or Gemini without interrupting your session.

---

## 🏗️ System Architecture & Asynchronous Workflow

```
                   FINSIGHT AI LOCALHOST ARCHITECTURE
                                  │
      ┌───────────────────────────┼───────────────────────────┐
      │                           │                           │
 1. Upload API             2. Status API               3. Normal APIs
 (POST /upload)          (GET /status 3s)           (Dashboard, Reports)
      │                           │                           │
      ▼                           ▼                           ▼
Save to Disk &              Return Real-Time            Instant Response
Return Job ID               Progress (0-100%)              (< 50 ms)
      │                           │                           │
      ▼                           │                           │
 Enqueue Job                      │                           │
      │                           │                           │
      ▼                           │                           │
 LOCAL WORKER THREAD POOL         │                           │
(PDF Extractor → Selective OCR    │                           │
 → Chunker → Embeddings           │                           │
 → ChromaDB Indexing) ────────────┘                           │
      │                                                       │
      ▼                                                       ▼
Document READY ───────────────────────────────────► RAG Q&A Available
```

---

## 🌟 Key Features & Features Breakdown

### 1. ⚡ Non-Blocking 600+ Page Processing
- Handles filings up to **250 MB** and **600+ pages** without browser timeout.
- Instant HTTP upload response in **< 1 second**.
- Background progress visible in the top navigation header (`Queued` → `Analyzing` → `Extracting` → `Embedding` → `Indexing` → `Ready`).

### 2. 💬 Humanic RAG AI Analyst with Source Footers
- Chat naturally with your financial filings using Groq's high-speed LLMs (`llama-3.3-70b-versatile`).
- Warm, conversational tone with strict financial grounding.
- Clear page citations listed cleanly at the bottom of responses (`Sources: Page 4, Page 18`), keeping text neat and easy to read.

### 3. 📊 Dynamic Interactive Financial Charts (Recharts)
- Automatic detection of financial tables in AI responses.
- In-chat toggle between **Table View**, **Bar Chart**, and **Trend Line**.
- Dedicated **Analytics Page** with structured financial charts (Revenue Trend, Net Profit Margin, Expense Breakdown, YoY Comparisons).

### 4. 📄 In-Document PDF Split Viewer
- Side-by-side view of your financial document alongside AI Analyst responses.
- Click any citation badge to jump directly to the exact page in the PDF.

### 5. ⚖️ Side-by-Side Corporate Comparison
- Compare two filings (e.g., FY24 vs FY25 or Company A vs Company B).
- Automated absolute and percentage variance calculations.

### 6. 📁 Multi-Format Support
- Ingests **PDF**, **Excel (.xlsx, .xls)**, **CSV**, **Word (.docx)**, **Markdown**, and **JSON** filings.

---

## 💻 Tech Stack & Technical Choices

| Layer | Technology | Why We Chose It |
|---|---|---|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS | Lightning-fast HMR, strict type safety, modern dark/light glassmorphic UI. |
| **Backend** | Python 3.12, FastAPI, Uvicorn | High performance async event loop with native Python AI ecosystem compatibility. |
| **Worker Queue** | Python `ThreadPoolExecutor(max_workers=2)` | In-process multi-threading for CPU-bound tasks without requiring complex Redis/Celery setups on localhost. |
| **PDF Processing** | PyMuPDF (Fitz) | 50x faster than pure-Python PDF tools; preserves exact text coordinates and tabular structure. |
| **OCR Service** | Gemini Vision / Tesseract | Selective OCR fallback only for scanned pages to optimize API quota and speed. |
| **Vector Store** | ChromaDB | In-process serverless vector database; no external database setup needed for localhost. |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` | Lightweight 384-dimensional vector model delivering fast embeddings on local CPUs. |
| **LLM Inference** | Groq, NVIDIA NIM, Gemini | Sub-2-second generation via Groq with automatic failover fallback. |
| **Charts** | Recharts | Declarative React charting library for responsive financial visual analytics. |

---

## 📁 Complete File & Folder Structure (With Use Cases)

```
FINANCE_REPORT_ANALYZER_AI/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py                    # Auth dependency injection & Firebase user token validation
│   │   │   └── rate_limiter.py            # Upload & AI request rate limiting per user identity
│   │   ├── config/
│   │   │   └── settings.py                # Central app configuration (250MB upload limit, 600s timeouts)
│   │   ├── document_processing/
│   │   │   ├── pdf_extractor.py           # PyMuPDF fast text/table extractor & selective OCR trigger
│   │   │   ├── processor.py               # Main document pipeline & 20-page memory-controlled batching
│   │   │   ├── chunker.py                 # Recursive semantic chunking (800-1000 chars with overlap)
│   │   │   └── cleaner.py                 # Normalizes financial numbers (₹, $, %, negative brackets)
│   │   ├── services/
│   │   │   ├── background_worker.py        # Local ThreadPool worker pool managing async task queue
│   │   │   ├── document_service.py        # Streaming disk writes, SHA-256 hash check, stage tracking
│   │   │   ├── chat_service.py            # Conversational state, RAG query execution, humanic prompts
│   │   │   └── financial_service.py       # Extraction of key financial metrics (Revenue, PAT, Margins)
│   │   ├── rag/
│   │   │   ├── rag_service.py             # Hybrid vector search, financial synonym expansion, LLM synthesis
│   │   │   └── prompts.py                 # Strict financial prompts mandating page footers & no hallucinations
│   │   ├── vectorstore/
│   │   │   ├── vector_service.py          # ChromaDB client, batched vector indexing (250 chunks/batch)
│   │   │   └── embeddings.py              # SentenceTransformers embedding generator instance
│   │   ├── routes/
│   │   │   ├── documents.py               # Upload endpoint, status polling (/status), document listing
│   │   │   ├── chat.py                    # Analyst chat Q&A endpoints & conversation management
│   │   │   ├── compare.py                 # Multi-report comparison & variance calculation endpoints
│   │   │   └── financial.py               # Structured financial charts data endpoints
│   │   └── main.py                        # FastAPI entrypoint, CORS setup, and router registration
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.tsx                 # Header navbar with persistent background progress bar
│   │   │   ├── pdf/PdfSplitViewer.tsx     # In-document split view with page citation jumping
│   │   │   └── common/RichMarkdownRenderer.tsx # Renders markdown tables & interactive Recharts
│   │   ├── context/
│   │   │   ├── ReportContext.tsx          # Global report state & 3s status polling loop
│   │   │   └── AuthContext.tsx            # Firebase user login/logout authentication state
│   │   ├── pages/
│   │   │   ├── UploadPage.tsx             # Single drag-and-drop upload page with 250MB support
│   │   │   ├── AnalystPage.tsx            # Full AI Analyst workspace (Chat + PDF Viewer + Exports)
│   │   │   ├── DashboardPage.tsx          # Workspace overview KPI cards & recent filings list
│   │   │   ├── AnalyticsPage.tsx          # Recharts financial analytics dashboard
│   │   │   └── ComparePage.tsx            # Side-by-side filing comparison tool
│   │   ├── services/
│   │   │   ├── apiClient.ts               # Central Axios client configured for localhost API
│   │   │   └── documentService.ts         # Lightweight document upload & status API calls
├── ARCHITECTURE_AND_WORKFLOW.md           # In-depth architectural documentation & Mermaid flowcharts
├── QUICKSTART.md                          # Simple step-by-step command guide to start the project
└── README.md                              # Main project documentation
```

---

## 🚀 Installation & Local Setup

### Option A — Automated Setup (Recommended for New Developers)

**Windows (PowerShell):**
```powershell
git clone https://github.com/anand-chaudhari/Financial_Report_Analyzer.git
cd Financial_Report_Analyzer
.\scripts\setup.ps1
```

**macOS / Linux:**
```bash
git clone https://github.com/anand-chaudhari/Financial_Report_Analyzer.git
cd Financial_Report_Analyzer
bash scripts/setup.sh
```

The script will:
- Create a Python virtual environment (`backend/.venv`)
- Install all Python dependencies (`requirements.txt`)
- Install all Node.js dependencies (`npm install`)
- Create required directories (`uploads/`, `chroma_data/`, `cache/`)
- Copy `.env.example` templates to `.env` for both backend and frontend

---

### Option B — Manual Setup (Step-by-Step)

#### 1. Clone the Repository
```bash
git clone https://github.com/anand-chaudhari/Financial_Report_Analyzer.git
cd Financial_Report_Analyzer
```

#### 2. Backend Setup (FastAPI)
```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1
# (Linux/macOS)
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create required data directories
mkdir uploads chroma_data cache

# Copy environment template
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux

# Fill in your API keys in backend/.env, then start the server:
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
*Backend API will run at `http://localhost:8000` (Swagger docs: `http://localhost:8000/docs`).*

#### 3. Frontend Setup (React + Vite)
```bash
# Open a new terminal and navigate to frontend
cd frontend

# Copy environment template
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux

# Fill in your Firebase config in frontend/.env, then:
npm install
npm run dev
```
*Frontend app will run at `http://localhost:5173`.*

---

## ⚙️ Environment Variables Configuration

Full templates are in `backend/.env.example` and `frontend/.env.example`. Copy them and fill in your values.

### Backend `backend/.env` — Key Variables:

| Variable | Required | Description | Where to get it |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ Yes | Primary LLM for AI analysis | [aistudio.google.com](https://aistudio.google.com/app/apikey) (free) |
| `GROQ_API_KEY` | Optional | Fast fallback LLM | [console.groq.com](https://console.groq.com) (free) |
| `NVIDIA_API_KEY` | Optional | Secondary fallback LLM | [build.nvidia.com](https://build.nvidia.com) |
| `FIREBASE_CREDENTIALS_PATH` | ✅ Yes | Path to `serviceAccountKey.json` | Firebase Console → Service Accounts |
| `BACKEND_PORT` | No | Default: `8000` | Change if port 8000 is in use |
| `MAX_UPLOAD_SIZE_MB` | No | Default: `250` | Adjust for your machine |

### Frontend `frontend/.env` — Key Variables:

| Variable | Required | Description |
|---|---|---|
| `VITE_API_BASE_URL` | ✅ Yes | Backend URL — keep as `http://localhost:8000` for local dev |
| `VITE_FIREBASE_API_KEY` | ✅ Yes | Firebase Web App API Key |
| `VITE_FIREBASE_PROJECT_ID` | ✅ Yes | Your Firebase Project ID |
| Other `VITE_FIREBASE_*` | ✅ Yes | From Firebase Console → Web App Config |

### 🔑 Firebase Service Account Key Setup:
1. Go to [Firebase Console](https://console.firebase.google.com) → Your Project
2. Click ⚙️ **Project Settings** → **Service accounts** tab
3. Click **"Generate new private key"** → Save the downloaded JSON
4. Rename and place it at: `backend/serviceAccountKey.json`



## 🧠 Frequently Asked Questions & Technical Interview Answers

### Q1. Why did the previous upload fail with `timeout of 300000ms exceeded`?
> **Answer**: The legacy code ran the entire extraction, OCR, embedding, and vector indexing synchronously inside the HTTP request loop. A 600-page PDF takes 5–8 minutes to index, which exceeded the browser's 5-minute (300,000ms) HTTP timeout.

### Q2. How did you fix the request timeout architecturally?
> **Answer**: We decoupled file upload from document processing. `POST /api/v1/documents/upload` streams the file to disk in 1MB chunks, creates a job ID, enqueues the job onto a local `ThreadPoolExecutor` worker, and returns **HTTP 200 OK in under 1 second**. The frontend then polls `GET /documents/{id}/status` every 3 seconds to render real-time progress.

### Q3. How does background processing avoid slowing down normal API requests?
> **Answer**: Heavy PDF processing is offloaded to a dedicated Python `ThreadPoolExecutor(max_workers=2)`. This leaves FastAPI's main `asyncio` event loop free to handle incoming requests for Dashboard, Reports, and Analytics with sub-50ms response times.

### Q4. How do you prevent out-of-memory (OOM) errors on large 200 MB PDFs?
> **Answer**: 
> 1. Files are written using 1MB chunked streams (never loaded into RAM all at once).
> 2. PDF extraction, chunking, and embedding run in 20-page batches.
> 3. Memory garbage collection (`gc.collect()`) runs between batches.

### Q5. What happens if the user re-uploads the exact same PDF file?
> **Answer**: The backend calculates a SHA-256 file hash upon upload. If an identical hash already exists in the system, it reuses the previously indexed vector chunks instantly and completes in **< 1 second**.

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
