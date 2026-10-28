# 💼 FinSight AI — High-Performance Multi-Format Financial Report Intelligence & Hybrid RAG System

[![Vite React](https://img.shields.io/badge/Frontend-React_18_%2B_Vite_%2B_TailwindCSS-06b6d4?style=for-the-badge&logo=react)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_%2B_Python_3.11+-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![ChromaDB](https://img.shields.io/badge/Vector_Store-ChromaDB_HNSW-6366f1?style=for-the-badge)](https://www.trychroma.com/)
[![Groq & Gemini](https://img.shields.io/badge/LLM_Engine-Groq_%2B_Llama_3.3_70B_%2B_Gemini_Vision-10b981?style=for-the-badge)](https://groq.com/)
[![Firebase](https://img.shields.io/badge/Deployment-Firebase_Hosting_%2B_Firestore-ffca28?style=for-the-badge&logo=firebase)](https://firebase.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-amber?style=for-the-badge)](https://opensource.org/licenses/MIT)

> **FinSight AI** is an enterprise-grade, local-first financial report intelligence platform engineered to ingest, parse, index, and analyze massive corporate disclosures—including SEC Form 10-K, 10-Q, annual reports up to **500+ pages / 200 MB**, executive Word summaries (DOCX), and structured financial spreadsheets (CSV/TSV)—delivering grounded, verifiable financial insights without browser timeouts, memory crashes, or tabular hallucination.

---

## 📑 Table of Contents
1. [Key Innovations & What's New](#-key-innovations--whats-new)
2. [Why FinSight AI? (Architecture & Design Choices)](#-why-finsight-ai-architecture--design-choices)
3. [System Architecture & Workflow](#-system-architecture--workflow)
4. [Supported Document Formats](#-supported-document-formats)
5. [Core Features Breakdown](#-core-features-breakdown)
6. [Tech Stack & Technical Choices](#-tech-stack--technical-choices)
7. [Clean Repository Structure](#-clean-repository-structure)
8. [Installation & Local Setup](#-installation--local-setup)
9. [Firebase Production Deployment](#-firebase-production-deployment)
10. [Frequently Asked Questions & Technical Interview Answers](#-frequently-asked-questions--technical-interview-answers)
11. [License](#-license)

---<img width="661" height="585" alt="Screenshot 2026-10-28 012827" src="https://github.com/user-attachments/assets/89a7c255-c124-4a5b-bb86-6e644fb2967a" />
<img width="1577" height="798" alt="Screenshot 2026-10-28 120453" src="https://github.com/user-attachments/assets/57d4d01a-082f-40f8-9b4d-3fb563641c30" />


## 🚀 Key Innovations & What's New

FinSight AI incorporates several state-of-the-art architectural upgrades designed for financial engineering:

* 📄 **Unified Multi-Format Ingestion**: Native, memory-safe parsing of **PDFs** (up to 500+ pages / 200 MB), **Word files (DOCX)** with interleaved visual body parsing, and **Financial Datasets (CSV/TSV)** with auto-delimiter sniffing and multi-encoding detection (`utf-8`, `utf-8-sig`, `latin-1`).
* ⚡ **Zero-Memory 1 MB Chunked Streaming Upload**: Files are streamed to disk in 1 MB chunks while computing SHA-256 hashes concurrently on-the-fly, eliminating duplicate disk reads and keeping RAM flat during large file uploads.
* ⚡ **Deterministic Vector Cache Fingerprinting (`v2.2.0`)**: Instant cache reuse (`doc_hash + embedding_model + pipeline_version`) checks ChromaDB persistence. Re-uploaded documents resolve to `Ready` status in **< 1 second (0 ms indexing)**.
* 📊 **Table-Aware Markdown Chunking**: Splitting a multi-row financial table automatically prepends column headers and divider lines (`| Metric | FY23 | FY24 |`) to every sub-chunk, eliminating column and fiscal year severance.
* 👁️ **Selective Page-Level OCR**: PyMuPDF native vector extraction handles digital pages at C-speed. Vision OCR (Google Gemini 2.0 Flash) is triggered **strictly on image-only pages** (< 20 native text characters), avoiding redundant API calls.
* 🛡️ **Zero Cross-Document Semantic Bleed**: ChromaDB dense vector queries are strictly constrained to `document_id`. Multi-document tenants never cross-contaminate semantic retrieval results.
* 🔄 **Idempotent Background Worker & Retry Endpoint**: Duplicate background tasks are rejected automatically, and a dedicated retry endpoint (`POST /api/v1/documents/{document_id}/retry`) allows one-click recovery without re-uploading files.
* 💬 **Premium Analyst Chat Workspace**: Server-Sent Events (SSE) streaming chat, split-view PDF synchronization, rich financial Markdown tables, KPI badges, and clickable page citations.

---

## 💡 Why FinSight AI? (Architecture & Design Choices)

Processing multi-hundred-page annual reports (like State Bank of India's 450-page filing or Apple's 10-K) presents acute computational challenges:
* **Conventional RAG systems crash** because they load 100 MB+ files into memory buffers or attempt full-document OCR.
* **Standard text splitters break financial tables** across token boundaries, detaching numeric rows from column headers and causing LLMs to hallucinate fiscal periods.
* **Unqualified vector fallbacks bleed data** across different corporate reports when querying smaller datasets.

FinSight AI resolves these challenges through a decoupled, asynchronous, localhost-first architecture:

| Challenge | Generic RAG Implementations | FinSight AI Architecture |
| :--- | :--- | :--- |
| **Upload Memory** | Reads full 100 MB+ byte buffer into RAM | 1 MB chunked disk streaming with inline SHA-256 |
| **Table Continuity** | Chunks by character count; severs column headers | Detects Markdown tables; prepends headers to all sub-chunks |
| **Document Bleed** | Fallback search drops document filter; leaks data | Strict `where={"document_id": id}` constraint; zero bleed |
| **Duplicate Uploads**| Recalculates embeddings on every upload | Instant verified vector cache fingerprinting (`v2.2.0`) |
| **Scanned Pages** | Scans entire PDF or skips images entirely | Page-level check: runs OCR only on pages with < 20 characters |
| **Worker Collision**| Spawns multiple parallel workers for same job | Idempotent background pool (`is_job_running` check) |

---

## 🏗️ System Architecture & Workflow

```
                        FINSIGHT AI ARCHITECTURE
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
   1. Upload API             2. Status API               3. Chat Stream
   (POST /upload)          (GET /status 1.5s)          (POST /chat/stream)
        │                           │                           │
        ▼                           ▼                           ▼
 1MB Disk Streaming           Returns Stage &             Scoped ChromaDB
+ Concurrent SHA-256        Progress (0-100%)             Vector Retrieval
        │                           │                           │
        ▼                           │                           ▼
 Cache Fingerprint Match?           │                     Context Assembly
   ├── YES ──► Instant Ready (0ms)  │                  (Primary Tables First)
   └── NO  ──► Enqueue Worker       │                           │
        │                           │                           ▼
        ▼                           │                     Groq Llama 3.3
 LOCAL WORKER THREAD POOL           │                     70B LLM Engine
 (Format-Specific Extractor         │                           │
  → Table-Aware Markdown Chunker    │                           ▼
  → BAAI/bge-small-en-v1.5 Vectors  │                  Real-time SSE Streaming
  → Scoped ChromaDB Indexing) ──────┘                  to Split-View UI
```

---

## 📂 Supported Document Formats

FinSight AI processes heterogeneous corporate disclosures through a unified internal schema:

### 1. PDF Reports (`.pdf`)
* High-speed native vector text and table extraction powered by **PyMuPDF (`fitz`)**.
* Adaptive page-level OCR detection (< 20 characters and image present) powered by **Google Gemini 2.0 Flash Vision**.
* Memory-controlled batching (30 pages per batch) with explicit garbage collection, maintaining flat memory usage on 500+ page filings.
* Unprocessed OCR pages are recorded in metadata without silently dropping information.

### 2. Word Documents (`.docx`)
* Sequential XML body parsing (`w:p` paragraphs and `w:tbl` tables interleaved in true visual order).
* Preserves hierarchical heading structure, keeping financial tables under their correct sections.
* De-duplicates horizontally merged cells (`prev_cell_tc`).
* Extracts detected company names, fiscal periods, currencies, and units.

### 3. Financial Datasets (`.csv`, `.tsv`)
* Automatic character encoding detection supporting `UTF-8`, `UTF-8-BOM` (`utf-8-sig`), and `Latin-1`.
* Delimiter sniffing supporting commas (`,`), tabs (`\t`), semicolons (`;`), and pipes (`|`).
* Automatic column normalization and malformed row handling with non-fatal metadata warnings.
* Batched into structured 35-row chunks with headers preserved and row-range citations (`CSV Rows 2–36`).

---<img width="1252" height="782" alt="Screenshot 2026-10-28 131121" src="https://github.com/user-attachments/assets/9c5afa58-291e-4490-8672-a2947ec11511" />


## 🌟 Core Features Breakdown

### 1. ⚡ Non-Blocking 500+ Page Ingestion
- Uploads files up to **200 MB** and **500+ pages** in **under 1 second**.
- Background worker reports transparent stages: `Uploading` → `Queued` → `Analyzing` → `Extracting` → `OCR` → `Chunking` → `Embedding` → `Indexing` → `Ready`.
- Automatic dynamic ETA estimation and responsive progress bars.

### 2. 💬 Interactive AI Financial Analyst
- Grounded conversational Q&A powered by **Groq Llama 3.3 70B Versatile** at 250+ tokens/second.
- Side-by-side **PDF Split Viewer** synchronized with chat citations.
- Precedence ordering: Primary financial tables and audited statements are injected ahead of secondary summaries to ensure empirical grounding.

### 3. 📊 Tabular Integrity & Dynamic Charts
- Preserves multi-column financial statements (Balance Sheets, Income Statements, Cash Flow statements).
- Rich Markdown renderer displaying financial tables with alternating rows and KPI badges.
- Time-series financial metric visualization using **Recharts**.

### 4. 🛡️ Resilient Recovery & Security
- Instant one-click retry endpoint (`POST /api/v1/documents/{document_id}/retry`) for interrupted jobs.
- User-isolated storage (`uploads/{user_id}/{document_id}/`).
- Rate-limited upload endpoints and magic-byte format validation.

---

## 🛠️ Tech Stack & Technical Choices

| Layer | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Backend Framework** | **FastAPI / Python** | 3.11+ / 0.115+ | Asynchronous REST and SSE streaming endpoints |
| **Web Server** | **Uvicorn** | 0.32+ | High-throughput ASGI server execution |
| **Vector Database** | **ChromaDB** | 0.5+ | Local persistent HNSW dense vector store |
| **Dense Embeddings** | **BAAI/bge-small-en-v1.5**| 384-dim | State-of-the-art semantic retrieval embeddings |
| **Foundation LLM** | **Meta Llama 3.3 70B** | Via Groq | Ultra-fast inference with strong numerical reasoning |
| **Vision OCR** | **Gemini 2.0 Flash** | Via Google AI | Selective multimodal OCR on scanned PDF pages |
| **PDF Extraction** | **PyMuPDF (`fitz`)** | 1.24+ | C-speed native PDF text and vector table parsing |
| **DOCX Extraction** | **python-docx** | 1.1+ | Interleaved XML body parsing of Word documents |
| **CSV Parser** | **Python `csv` + Sniffer**| Built-in | Memory-safe multi-encoding delimited streaming |
| **Frontend Framework**| **React 18 / TypeScript**| React 18, TS 5.6 | Type-safe financial dashboard workspace |
| **Build Tooling** | **Vite** | 5.4+ | Lightning-fast development server & production bundler |
| **Styling** | **Tailwind CSS** | 3.4+ | Modern dark/light responsive financial UI |
| **Deployment** | **Firebase Hosting** | v13+ | Global CDN hosting for production frontend bundle |

---

## 🗂️ Clean Repository Structure

```
Financial_Report_Analyzer/
├── backend/
│   ├── app/
│   │   ├── api/                 # Rate limiting & middleware
│   │   ├── config.py            # Application settings & environment config
│   │   ├── document_processing/ # Multi-format extraction & chunking
│   │   │   ├── chunker.py       # Table-preserving Markdown chunker
│   │   │   ├── cleaner.py       # Whitespace & tab delimiter cleaner
│   │   │   ├── extractors/      # PDF, DOCX, CSV format extractors
│   │   │   └── pdf_extractor.py # PyMuPDF & selective OCR engine
│   │   ├── firebase/            # Firebase Admin SDK & token validation
│   │   ├── llm/                 # Multi-provider LLM client (Groq, Gemini, NVIDIA)
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── models/              # Pydantic data models
│   │   ├── rag/                 # RAG prompt templates & context builder
│   │   ├── routes/              # REST & SSE endpoints (chat, documents, compare)
│   │   ├── services/            # Background worker, document & cache services
│   │   └── vectorstore/         # ChromaDB client & scoped vector operations
│   ├── requirements.txt         # Python dependencies
│   ├── run_server.py            # Auto-restart supervisor script
│   ├── start_backend.bat        # Windows 1-click startup script
│   └── start_backend.ps1        # PowerShell 1-click startup script
├── frontend/
│   ├── src/
│   │   ├── components/          # ReportCard, PdfSplitViewer, chat components
│   │   ├── context/             # AuthContext, ReportContext
│   │   ├── pages/               # UploadPage, AnalystPage, ReportsPage, ComparePage
│   │   ├── services/            # Axios API clients & SSE consumer
│   │   └── types/               # TypeScript interfaces
│   ├── dist/                    # Compiled production bundle for Firebase Hosting
│   ├── package.json             # Frontend dependencies & scripts
│   └── vite.config.ts           # Vite build configuration
├── scripts/
│   ├── setup.ps1                # Automated Windows setup script
│   └── setup.sh                 # Automated macOS/Linux setup script
├── .firebaserc                  # Firebase project configuration
├── .gitignore                   # Git exclusion rules (secrets, caches, uploads)
├── firebase.json                # Firebase Hosting and security rules config
├── firestore.rules              # Firestore security rules
├── storage.rules                # Firebase Storage security rules
├── PROJECT_REPORT.md            # Comprehensive Academic Research Project Report
├── PROJECT_OVERVIEW.md          # Architectural deep-dive & overview
├── QUICKSTART.md                # Fast execution guide for daily use
└── README.md                    # Project documentation
```

---

## 🏃 Installation & Local Setup

### Prerequisites
* **Python**: 3.11 or higher
* **Node.js**: v18 or higher (v20+ recommended)
* **Git**: Installed and configured

### Step 1: Clone the Repository
```bash
git clone https://github.com/anand-chaudhari/Financial_Report_Analyzer.git
cd Financial_Report_Analyzer
```

### Step 2: Configure Environment Variables
Copy the template in `backend/.env.example` to `backend/.env`:
```ini
# Environment
ENVIRONMENT=development
PORT=8000
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]

# LLM API Keys (Obtain free keys from respective consoles)
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
NVIDIA_API_KEY=your_nvidia_api_key_here

# Pipeline Limits
MAX_PDF_PAGES=2000
OCR_MAX_PAGES=15
PARALLEL_EXTRACTION_WORKERS=8
```

### Step 3: Run the Application

#### Terminal 1 — Backend (FastAPI)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
* Backend API: `http://localhost:8000`
* Swagger Interactive Docs: `http://localhost:8000/docs`

#### Terminal 2 — Frontend (React + Vite)
```powershell
cd frontend
npm install
npm run dev
```
* Web Application: `http://localhost:5173`

---

## ☁️ Firebase Production Deployment

The frontend is configured for deployment to **Firebase Hosting**:

1. Install Firebase CLI:
   ```bash
   npm install -g firebase-tools
   ```
2. Log in and verify project selection:
   ```bash
   firebase login
   firebase use default
   ```
3. Build the frontend for production:
   ```bash
   cd frontend
   npm run build
   cd ..
   ```
4. Deploy Hosting, Firestore rules, and Storage rules:
   ```bash
   firebase deploy
   ```

---
<img width="1587" height="826" alt="Screenshot 2026-10-28 120523" src="https://github.com/user-attachments/assets/ea0fe683-4509-43e7-910c-5c2fcc5b266c" />
<img width="1553" height="865" alt="Screenshot 2026-10-28 121228" src="https://github.com/user-attachments/assets/0797fd52-e71a-476a-adfd-7e8a23fcdfe5" />
<img width="1811" height="842" alt="Screenshot 2026-10-28 120808" src="https://github.com/user-attachments/assets/fdc1eec1-bd66-4812-a8fb-e8cc37338a11" />

## ❓ Frequently Asked Questions & Technical Interview Answers

### Q1: How does FinSight AI prevent hallucinating numbers from financial tables?
> **Answer**: Standard text chunkers split text by character count, often cutting in the middle of a 50-row balance sheet. As a result, subsequent chunks contain raw numbers without column headers (`FY23`, `FY24`). FinSight AI's **Table-Aware Chunking Algorithm** detects Markdown table syntax (`|--- | ---|`) and automatically prepends the header row and separator line to every split sub-chunk. This guarantees the LLM always sees the column definitions and fiscal periods alongside every number.

### Q2: How does the system handle 500+ page PDFs without running out of memory?
> **Answer**: FinSight AI uses a 1 MB chunked disk-streaming upload mechanism that never reads the entire file into a RAM buffer. PDF pages are extracted in batches of 30 using PyMuPDF (which accesses native C descriptors on disk) followed by explicit Python garbage collection (`gc.collect()`). Peak RAM remains under 850 MB even when processing a 450-page annual report.

### Q3: What is "Instant Cache Reuse"?
> **Answer**: When a file is uploaded, an incremental SHA-256 hash is computed in real time. FinSight AI constructs a pipeline fingerprint: `cache_fingerprint = f"{doc_hash}_{EMBEDDING_MODEL}_{INDEX_PIPELINE_VERSION}"`. If this exact filing has already been indexed under the current pipeline version, FinSight AI verifies vector persistence in ChromaDB and returns an instant `Ready` response in **< 1 second**, completely bypassing redundant parsing and embedding generation.

### Q4: How is cross-document semantic bleed eliminated?
> **Answer**: In `vector_service.py`, all ChromaDB similarity queries construct a strict filter: `where={"$and": [{"user_id": user_id}, {"document_id": document_id}]}`. Generic fallbacks that drop the `document_id` filter have been eliminated. Searches for a document return chunks strictly belonging to that document ID.

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---
*Built with precision for financial analysts, auditors, and research engineers.*
