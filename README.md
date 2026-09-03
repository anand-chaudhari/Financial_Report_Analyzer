# 💼 FinSight AI — Autonomous Financial Report Analyzer & Intelligence Platform

[![Vite React](https://img.shields.io/badge/Frontend-React_18_%2B_Vite_%2B_TailwindCSS-06b6d4?style=for-the-badge&logo=react)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_%2B_Python_3.12-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![ChromaDB](https://img.shields.io/badge/Vector_Store-ChromaDB-6366f1?style=for-the-badge)](https://www.trychroma.com/)
[![Groq & NVIDIA NIM](https://img.shields.io/badge/LLM_Engine-Groq_%2B_NVIDIA_NIM_%2B_Gemini-10b981?style=for-the-badge)](https://groq.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-amber?style=for-the-badge)](https://opensource.org/licenses/MIT)

> **FinSight AI** is an enterprise-grade full-stack financial intelligence platform engineered to ingest, parse, index, and analyze complex corporate financial filings (SEC 10-K, 10-Q, Annual Reports, Earnings Disclosures) using hybrid Retrieval-Augmented Generation (RAG). It provides verifiable, page-cited answers, auto-generated interactive charts, side-by-side filing comparisons, and institutional export suites.

---

## 📑 Table of Contents
1. [System Architecture & Workflow](#-system-architecture--workflow)
2. [Key Features & Capabilities](#-key-features--capabilities)
3. [Comprehensive File & Folder Structure (With Use Cases)](#-comprehensive-file--folder-structure-with-use-cases)
4. [Tech Stack](#-tech-stack)
5. [Installation & Local Setup](#-installation--local-setup)
6. [Environment Variables Configuration](#-environment-variables-configuration)
7. [Comprehensive Interview Questions & In-Depth Answers](#-comprehensive-interview-questions--in-depth-answers)
   - [Part 1: RAG Architecture & Vector Search](#part-1-rag-architecture--vector-search)
   - [Part 2: Financial Precision & Hallucination Prevention](#part-2-financial-precision--hallucination-prevention)
   - [Part 3: Document Processing & Performance Optimization](#part-3-document-processing--performance-optimization)
   - [Part 4: Multi-Model LLM Orchestration & Failover](#part-4-multi-model-llm-orchestration--failover)
   - [Part 5: Full-Stack Engineering & Scalability](#part-5-full-stack-engineering--scalability)
8. [License](#-license)

---

## 🏗️ System Architecture & Workflow

```
+---------------------------------------------------------------------------------------------------+
|                                      FINSIGHT AI ARCHITECTURE                                      |
+---------------------------------------------------------------------------------------------------+

     [ Corporate Filing ] -> (PDF, DOCX, XLSX, TXT)
              │
              ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ 1. STREAMING INGESTION & INSPECTION ENGINE                   │
   │    • 1MB Chunked disk streaming (Handles up to 200MB files)  │
   │    • Pre-processing heuristic inspection (Page count, text)  │
   └──────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ 2. HYBRID EXTRACTION & STRUCTURE PRESERVATION                │
   │    • Native PyMuPDF (Fitz) vector extraction (~50x faster)   │
   │    • Selective OCR Fallback (Only image / scanned pages)     │
   │    • Financial Table & Grid parsing (Markdown tables)        │
   │    • Financial Section Classification (BS, PL, CF, MD&A)     │
   └──────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ 3. SEMANTIC CHUNKING & EMBEDDINGS PIPELINE                   │
   │    • Financial notation cleaner (₹, $, €, %, Cr, Lakh)       │
   │    • Recursive character chunking (1000 chars, 200 overlap)  │
   │    • SentenceTransformers (`all-MiniLM-L6-v2`) Embedding     │
   │    • ChromaDB Persistent Vector Indexing                     │
   └──────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ 4. HYBRID RETRIEVAL & CONTEXT ENRICHMENT                     │
   │    • Financial Query Expansion (Revenue -> Turnover, Sales)  │
   │    • Multi-vector similarity search + Metadata filtering     │
   │    • Section boundary preservation & Table preservation      │
   └──────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ 5. MULTI-MODEL LLM INFERENCE & FAILOVER ENGINE               │
   │    • Primary Engine: Groq (OpenAI GPT-OSS-120B / Compound)   │
   │    • Failover 1: NVIDIA NIM (Moonshot Kimi K3 / Llama 3.2)   │
   │    • Failover 2: Google Gemini (Gemini 2.0 Flash / Pro)      │
   │    • Guardrail: Zero-Hallucination & Exact Citation Prompt   │
   └──────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ 6. INTERACTIVE ANALYST DASHBOARD & VISUALIZATION             │
   │    • In-Chat Interactive Recharts (Bar & Trend Line toggles) │
   │    • Zebra-striped financial markdown tables & Metric Badges │
   │    • Interactive In-Document PDF Split View                  │
   │    • Institutional Export Suite (Excel Model, PDF, Slides)   │
   └──────────────────────────────────────────────────────────────┘
```

---

## 🌟 Key Features & Capabilities

1. **Deterministic Financial Accuracy**:
   - Explicit strict instruction prompts enforce exact table lookups rather than fuzzy summaries.
   - Respects accounting notations: negative numbers in parentheses `(1,200)` are parsed as `-1200`.
   - Never hallucinates missing figures; provides explicit disclaimers when disclosures are absent.
2. **Interactive In-Chat Dynamic Visualizations**:
   - Any financial comparative table in chat automatically offers an interactive toggle between **Table View**, **Bar Chart**, and **Trend Line** powered by Recharts.
3. **Live In-Document PDF Split Viewer**:
   - View citations directly side-by-side with the active PDF document, jumping automatically to cited page numbers.
4. **Multi-Model High-Availability LLM Routing**:
   - Instant sub-2-second generation via **Groq** (`openai/gpt-oss-120b`, `groq/compound`, `qwen/qwen3.6-27b`) with automatic failover to **NVIDIA NIM** (`moonshotai/kimi-k3`) and **Google Gemini**.
5. **200 MB Large-File Optimization**:
   - Memory-friendly 1 MB streamed uploads, incremental page processing, selective OCR, and batched ChromaDB insertions.
6. **Side-by-Side Corporate Comparison**:
   - Compare two financial reports (e.g., FY24 vs FY25 or Company A vs Company B) with automated absolute and percentage variance calculations.
7. **Institutional Export Suite**:
   - Export analyst threads to **Excel CSV Financial Models**, **CFO Executive Brief PDFs**, and **Board Presentation JSON Decks**.

---

## 📁 Comprehensive File & Folder Structure (With Use Cases)

### 🔹 Backend Structure (`backend/`)

```
backend/
├── app/
│   ├── api/
│   │   └── deps.py                    # [USE CASE]: Authentication dependency injection; validates Firebase JWT tokens and injects authenticated user state into route handlers.
│   ├── config/
│   │   └── settings.py                # [USE CASE]: Central Pydantic v2 application configuration; loads environment variables, API keys (Groq, NVIDIA, Gemini), and storage paths.
│   ├── document_processing/
│   │   ├── cleaner.py                 # [USE CASE]: Cleans raw OCR/PDF text while preserving critical financial syntax (currencies ₹/$/€, percentages, accounting brackets, negative signs).
│   │   ├── chunker.py                 # [USE CASE]: Recursive semantic character text splitter that breaks documents into contextual overlapping chunks with page and section metadata.
│   │   ├── section_detector.py        # [USE CASE]: Pattern matcher that identifies core financial sections (Balance Sheet, P&L, Cash Flow, Notes, MD&A, Auditor Report).
│   │   ├── pdf_extractor.py           # [USE CASE]: Fast PyMuPDF (Fitz) text/table extractor with smart heuristics and OCR fallback for scanned pages.
│   │   ├── file_detector.py           # [USE CASE]: Inspects MIME types and extensions to route documents to appropriate parsers (PDF, DOCX, XLSX, TXT).
│   │   ├── models.py                  # [USE CASE]: Dataclasses representing document chunks, extracted tables, and section hierarchies.
│   │   └── extractors/                # [USE CASE]: Specialized parser modules for DOCX, XLSX spreadsheets, and plain text files.
│   ├── firebase/
│   │   └── firebase_service.py        # [USE CASE]: Firebase Admin SDK integration managing Cloud Firestore collections and cloud storage backups.
│   ├── llm/
│   │   ├── llm_client.py              # [USE CASE]: Primary LLM orchestrator implementing automated failover across Groq, NVIDIA NIM, Gemini, and OpenAI.
│   │   └── nvidia_client.py           # [USE CASE]: Dedicated NVIDIA NIM API integration layer targeting Moonshot Kimi K3, Llama 3.2, and Mistral Large.
│   ├── models/
│   │   └── domain models              # [USE CASE]: Pydantic domain models for reports, chat messages, financial summaries, and comparative metrics.
│   ├── rag/
│   │   ├── rag_service.py             # [USE CASE]: Core RAG pipeline; performs financial synonym expansion, hybrid vector search, and grounded response synthesis.
│   │   ├── financial_calculator.py    # [USE CASE]: Validates calculations, computes financial ratios (operating margins, net profit margin, YoY growth), and standardizes units.
│   │   └── prompts.py                 # [USE CASE]: System prompt engineering mandating strict factual grounding, verified page citations, and structured markdown output.
│   ├── routes/
│   │   ├── chat.py                    # [USE CASE]: FastAPI endpoints for analyst chat Q&A, thread creation, conversation history, and thread deletion.
│   │   ├── documents.py               # [USE CASE]: Endpoints for streaming document upload, inspection, processing progress polling, and PDF preview serving.
│   │   ├── financial.py               # [USE CASE]: Endpoints for structured financial overview extraction, risk analysis, and metric breakdowns.
│   │   ├── compare.py                 # [USE CASE]: Endpoints for multi-report comparison, variance analysis, and cross-quarter diffs.
│   │   └── reports.py                 # [USE CASE]: CRUD endpoints for managing user report metadata and executive summaries.
│   ├── schemas/
│   │   └── pydantic schemas           # [USE CASE]: Strict request/response validation schemas for all REST API endpoints.
│   ├── services/
│   │   ├── cache_service.py           # [USE CASE]: Multi-tier disk and memory caching for extracted metrics, overview data, and document summaries to eliminate redundant LLM calls.
│   │   ├── chat_service.py            # [USE CASE]: Manages conversational state, multi-turn memory, citation deduplication, and streaming query execution.
│   │   ├── document_service.py        # [USE CASE]: Orchestrates full document lifecycle: 1MB chunked disk writes, inspection, extraction, embedding generation, and ChromaDB insertion.
│   │   ├── financial_service.py       # [USE CASE]: Extracts core financial metrics (Revenue, EBITDA, PAT, EPS, Debt, Margins) with verified source page links.
│   │   ├── report_service.py          # [USE CASE]: Report management and metadata aggregation service.
│   │   └── summary_service.py         # [USE CASE]: Generates concise executive summaries and key bullet takeaways for uploaded filings.
│   ├── utils/
│   │   └── logger.py                  # [USE CASE]: Production logger with Windows UTF-8 stdout reconfiguration preventing UnicodeEncodeError on Indian Rupee (₹) symbols.
│   ├── vectorstore/
│   │   ├── embeddings.py              # [USE CASE]: SentenceTransformer embedding generator (`sentence-transformers/all-MiniLM-L6-v2`) with batched vectorized inference.
│   │   └── vector_service.py          # [USE CASE]: ChromaDB client managing isolated collections, cosine similarity search, chunk indexing, and deletion.
│   ├── main.py                        # [USE CASE]: FastAPI application entrypoint with CORS middleware, lifespan events, and global route mounting.
│   └── run_server.py                  # [USE CASE]: Development runner script launching Uvicorn with auto-reload.
├── tests/
│   ├── test_financial_rag_accuracy.py # [USE CASE]: Unit & regression tests for financial synonym retrieval, table accuracy, and metric preservation.
│   ├── test_large_pdf_optimization.py # [USE CASE]: Validates streaming 1MB writes, non-blocking async execution, and stage progression.
│   ├── test_multi_format.py           # [USE CASE]: Tests extraction on PDF, DOCX, XLSX, and TXT files.
│   ├── test_caching.py                # [USE CASE]: Verifies cache hit/miss lifecycles for financial summaries and overviews.
│   └── test_nvidia_rag.py             # [USE CASE]: Tests dedicated NVIDIA NIM endpoint routing.
├── requirements.txt                   # [USE CASE]: Python package dependencies specification.
└── .env.example                       # [USE CASE]: Template environment variables for backend.
```

---

### 🔹 Frontend Structure (`frontend/`)

```
frontend/
├── src/
│   ├── components/
│   │   ├── common/
│   │   │   └── RichMarkdownRenderer.tsx # [USE CASE]: Markdown renderer with in-chat interactive Recharts (Bar/Line), styled tables, and financial badge accents.
│   │   ├── financial/
│   │   │   └── FinancialOverviewSection.tsx # [USE CASE]: Interactive overview dashboard displaying Revenue, Profit, Margins, and verified page badges.
│   │   ├── pdf/
│   │   │   └── PdfSplitViewer.tsx       # [USE CASE]: Collapsible split PDF viewer with live page navigation, zooming, and citation highlight callouts.
│   │   ├── CitationBadge.tsx            # [USE CASE]: Interactive citation badge pill that opens page source excerpts.
│   │   ├── Header.tsx                   # [USE CASE]: Top header navigation bar with user profile actions.
│   │   ├── Navbar.tsx                   # [USE CASE]: Global responsive navigation bar with mobile slide-out drawer.
│   │   ├── Sidebar.tsx                  # [USE CASE]: Collapsible application navigation sidebar with active link indicators.
│   │   ├── MetricCard.tsx               # [USE CASE]: High-contrast financial metric card with sparklines and growth badges.
│   │   ├── ReportCard.tsx               # [USE CASE]: Filing summary card with status badges, page counts, and quick action buttons.
│   │   ├── StatCard.tsx                 # [USE CASE]: Dashboard statistical KPI card with glowing gradients.
│   │   └── LoadingSpinner.tsx           # [USE CASE]: Animated loading indicator for asynchronous operations.
│   ├── context/
│   │   ├── AuthContext.tsx              # [USE CASE]: React Context managing Firebase user authentication, login, register, and logout state.
│   │   └── ReportContext.tsx            # [USE CASE]: React Context managing uploaded reports, active report selection, and workspace syncing.
│   ├── hooks/
│   │   ├── useAuth.ts                   # [USE CASE]: Custom hook exposing authentication methods and user profile.
│   │   ├── useChat.ts                   # [USE CASE]: Custom hook managing chat message streams, sending queries, and error recovery.
│   │   └── useTheme.ts                  # [USE CASE]: Custom hook managing light/dark mode theme state.
│   ├── pages/
│   │   ├── AnalystPage.tsx              # [USE CASE]: Full-screen institutional analyst workspace featuring multi-turn chat, PDF split viewer, citation modals, and export suite.
│   │   ├── ReportAnalysisPage.tsx       # [USE CASE]: Document analysis hub with interactive tabs for AI Assistant, Visual Charts, and Executive Summary.
│   │   ├── DashboardPage.tsx            # [USE CASE]: Workspace overview displaying total filings, indexed pages, financial overview, and recent filings.
│   │   ├── UploadPage.tsx               # [USE CASE]: Drag-and-drop filing upload page with real-time 8-stage pipeline visualization.
│   │   ├── ComparePage.tsx              # [USE CASE]: Side-by-side comparative analysis view comparing metrics between two filings.
│   │   ├── AnalyticsPage.tsx            # [USE CASE]: Interactive chart dashboard showing historical revenue, margins, and expense breakdowns.
│   │   ├── ReportsPage.tsx              # [USE CASE]: Filing repository list with filtering, search, and delete options.
│   │   ├── ChatHistoryPage.tsx          # [USE CASE]: Archives and manages past analyst conversation sessions.
│   │   └── SettingsPage.tsx             # [USE CASE]: Workspace preferences, LLM provider selection, and API key management.
│   ├── services/
│   │   ├── apiClient.ts                 # [USE CASE]: Axios client configured with base URL, request interceptors, and Firebase auth headers.
│   │   ├── chatService.ts               # [USE CASE]: HTTP service interfacing with backend chat endpoints.
│   │   ├── documentService.ts           # [USE CASE]: HTTP service for uploading documents, fetching status, and file deletion.
│   │   ├── exportService.ts             # [USE CASE]: Client-side exporter generating CSV financial models, PDF briefs, and presentation slide decks.
│   │   └── financialService.ts          # [USE CASE]: HTTP service fetching structured financial overview and risk analysis.
│   ├── types/
│   │   ├── chat.ts                      # [USE CASE]: TypeScript interfaces for chat messages, citations, and conversation threads.
│   │   ├── financial.ts                 # [USE CASE]: TypeScript interfaces for financial metrics, ratios, and comparisons.
│   │   └── report.ts                    # [USE CASE]: TypeScript interfaces for report metadata, processing stages, and file details.
│   ├── utils/
│   │   ├── constants.ts                 # [USE CASE]: Configuration constants including dynamic API_BASE_URL.
│   │   └── formatters.ts                # [USE CASE]: Utility functions for formatting currency (INR/USD), percentages, file sizes, and dates.
│   ├── App.tsx                          # [USE CASE]: Root application router with protected routes and layout providers.
│   └── main.tsx                         # [USE CASE]: React DOM entrypoint initializing root React node.
├── package.json                         # [USE CASE]: Frontend dependencies and npm build scripts.
├── vite.config.ts                       # [USE CASE]: Vite build bundler configuration with React plugin and proxy settings.
└── tailwind.config.js                   # [USE CASE]: Tailwind CSS styling theme, custom colors, gradients, and typography config.
```

---

## 💻 Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Recharts, Lucide Icons, React Router v6 |
| **Backend** | Python 3.12, FastAPI, Pydantic v2, Uvicorn, AnyIO, AsyncIO |
| **Document Processing** | PyMuPDF (Fitz), Tesseract OCR, Python-docx, OpenPyXL |
| **Vector Store & Embeddings** | ChromaDB, SentenceTransformers (`all-MiniLM-L6-v2`) |
| **LLM Inference** | Groq (Llama 3.3 / GPT-OSS-120B), NVIDIA NIM (Moonshot Kimi K3), Google Gemini, OpenAI |
| **Authentication & Storage** | Firebase Auth, Cloud Firestore, Firebase Storage |

---

## 🚀 Installation & Local Setup

### 1. Clone the Repository
```bash
git clone https://github.com/anand-chaudhari/Financial_Report_Analyzer.git
cd Financial_Report_Analyzer
```

### 2. Backend Setup
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

# Run the FastAPI server
python run_server.py
```
*Backend API will run at `http://localhost:8000` (API Docs available at `http://localhost:8000/docs`).*

### 3. Frontend Setup
```bash
# Open a new terminal and navigate to frontend
cd frontend

# Install npm packages
npm install

# Start development server
npm run dev
```
*Frontend application will run at `http://localhost:5173`.*

---

## ⚙️ Environment Variables Configuration

### Backend `.env` (`backend/.env`):
```env
ENVIRONMENT=development
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Primary LLM Provider (groq | nvidia | gemini | openai)
LLM_PROVIDER=groq

# API Keys
GROQ_API_KEY=your_groq_api_key
NVIDIA_API_KEY=your_nvidia_api_key
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key

# Vector Store & Embedding Config
CHROMA_PERSIST_DIRECTORY=./chroma_data
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

---

## 🧠 Comprehensive Interview Questions & In-Depth Answers

---

### Part 1: RAG Architecture & Vector Search

#### Q1. How does FinSight AI solve the challenge of semantic retrieval on dense financial tables vs narrative disclosures?
> **Answer**: Financial filings contain two fundamentally different types of information: dense narrative text (e.g., Management Discussion & Analysis) and structured numerical tables (Balance Sheets, Income Statements). Standard text chunkers destroy table structure by splitting rows arbitrarily across chunk boundaries.
> FinSight AI addresses this through **structure-aware parsing and metadata injection**:
> 1. In `pdf_extractor.py`, tables are recognized as contiguous grid units and converted into Markdown table format (`| Metric | FY24 | FY25 |`).
> 2. Chunks containing tables are tagged with metadata `is_table: True` and retain the preceding section header (e.g., `Consolidated Statement of Profit and Loss`).
> 3. During retrieval, the RAG service performs query classification: when a quantitative metric is requested, it prioritizes chunks with `is_table: True` and boosts table-dense sections.

#### Q2. Why is ChromaDB chosen as the local vector store, and how is cosine distance used?
> **Answer**: ChromaDB is an embedded, serverless vector database that runs in-process with Python, eliminating the need for an external database cluster during development. It supports persistent on-disk HNSW (Hierarchical Navigable Small World) indexing.
> FinSight AI uses normalized 384-dimensional embeddings generated by `sentence-transformers/all-MiniLM-L6-v2`. Cosine similarity is computed as:
> $$\text{Cosine Similarity} = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2}$$
> Since embeddings are $L_2$-normalized upon creation, cosine similarity reduces to a fast dot product, enabling sub-10ms top-$k$ nearest-neighbor retrieval.

#### Q3. What is Financial Query Expansion and why is it necessary?
> **Answer**: Financial terminology varies significantly across international accounting standards (IFRS vs US GAAP vs Indian AS). A user asking for *"Revenue"* might be searching for a filing that uses *"Revenue from Operations"*, *"Turnover"*, or *"Net Sales"*.
> If an exact string match or naive semantic search is performed, distance scores may be suboptimal. In `rag_service.py`, FinSight AI expands queries with financial synonyms:
> - **Revenue** $\rightarrow$ `["Revenue from operations", "Total revenue", "Turnover", "Net sales"]`
> - **Profit** $\rightarrow$ `["Net profit for the year", "Profit after tax", "PAT", "Consolidated net income"]`
> - **EBITDA** $\rightarrow$ `["Operating profit", "EBITDA", "PBITDA", "Earnings before interest, tax, depreciation"]`
> The multi-term retrieval aggregates context from all synonyms and deduplicates the resulting chunks.

---

### Part 2: Financial Precision & Hallucination Prevention

#### Q4. How does FinSight AI eliminate LLM hallucinations in quantitative financial Q&A?
> **Answer**: Hallucinations in financial AI can cause critical decision errors. FinSight AI implements a multi-layered guardrail strategy:
> 1. **Strict Context Injection & Source Citation**: The system prompt instructs the model that it is operating under statutory audit conditions. It must strictly answer using only the provided context chunks and cite every fact using `[Page X]` or `Source: Page X — Section`.
> 2. **Explicit Fallback Requirement**: If a specific number or breakdown is not explicitly disclosed in the retrieved context, the prompt mandates that the model state: *"The provided document does not disclose [Metric]."* It is strictly forbidden from extrapolating or guessing.
> 3. **Exact Numeric Value Preservation**: The model is instructed to prefer exact table figures over high-level narrative summaries and preserve the specified currency (e.g. ₹ vs $) and scale (Crore, Lakh, Million, Billion).

#### Q5. How does the system handle accounting nuances like negative numbers in parentheses `(1,500)`?
> **Answer**: In financial reporting, negative balances, cash outflows, or losses are conventionally written in parentheses `(e.g., (1,500))` rather than with a minus sign `-1,500`. Standard NLP tokenizers often strip parentheses or misinterpret them as punctuation.
> FinSight AI's `cleaner.py` and `financial_calculator.py` explicitly parse accounting syntax:
> ```python
> if val_str.startswith('(') and val_str.endswith(')'):
>     numeric_val = -float(val_str[1:-1].replace(',', ''))
> ```
> This guarantees that net cash flow reductions and net losses are accurately recognized with their negative sign in downstream chart visualizations and comparative variance calculations.

---

### Part 3: Document Processing & Performance Optimization

#### Q6. How does FinSight AI process 200 MB PDF files on localhost without memory exhaustion?
> **Answer**: Loading a 200 MB PDF entirely into memory can consume gigabytes of RAM when rasterized or parsed into text objects. FinSight AI prevents memory exhaustion through four optimizations:
> 1. **Chunked Streaming Upload**: In `routes/documents.py`, files are streamed in 1 MB chunks directly to temporary disk storage rather than buffered in RAM via `await upload_file.read(1024 * 1024)`.
> 2. **Pre-Processing PDF Inspection**: `inspect_pdf()` samples the first few pages to determine if the PDF is digitally native or scanned, preventing unneeded OCR on clean text PDFs.
> 3. **Incremental Page Extraction**: PyMuPDF iterates page-by-page, closing page objects and invoking Python garbage collection between 25-page batches.
> 4. **Selective OCR**: OCR (Tesseract) is executed **only** on pages where extracted text falls below 30 characters and image areas are detected.

#### Q7. Why is PyMuPDF (Fitz) preferred over PDFPlumber or PyPDF for financial extraction?
> **Answer**: PyMuPDF is a Python binding for the MuPDF C library. It provides:
> - **Speed**: ~20x to 50x faster than pure Python parsers like PyPDF or PDFMiner.
> - **Layout & Coordinate Fidelity**: Provides exact bounding box coordinates (`bbox`) for tabular text blocks and fonts, enabling precise row and column detection.
> - **Low Memory Footprint**: Uses C-level memory allocations with minimal Python object overhead.

---

### Part 4: Multi-Model LLM Orchestration & Failover

#### Q8. Describe the multi-tier failover architecture in `llm_client.py`.
> **Answer**: High availability is critical because public LLM endpoints frequently suffer from rate limits (HTTP 429), regional outages, or model deprecations. FinSight AI implements an automated waterfall failover hierarchy:
> 1. **Primary Provider (Groq)**: Targets high-throughput LPU models (`openai/gpt-oss-120b`, `groq/compound`, `qwen/qwen3.6-27b`) delivering sub-2s responses.
> 2. **Failover 1 (NVIDIA NIM)**: If Groq fails (HTTP 429/500/timeout), requests are immediately routed to `https://integrate.api.nvidia.com/v1` targeting `moonshotai/kimi-k3` or `meta/llama-3.2-90b-vision-instruct`.
> 3. **Failover 2 (Google Gemini)**: If NVIDIA NIM fails, requests fall through to Google Gemini (`gemini-2.0-flash`, `gemini-1.5-pro`).
> 4. **Failover 3 (OpenAI)**: Direct fallback to OpenAI GPT-4o.
> 5. **Reasoning Tag Cleaner**: Strips `<think>...</think>` reasoning tokens generated by deep thinking models before delivering clean markdown to the frontend.

#### Q9. Why was the Windows UTF-8 stdout fix implemented in `logger.py`?
> **Answer**: On Windows systems, the default console encoding is often `cp1252` or `Windows-1252`. When financial amounts with the Indian Rupee symbol (`₹`) or non-ASCII characters were logged, Python's standard `sys.stdout` threw an unhandled `UnicodeEncodeError`, terminating the logging thread.
> In `backend/app/utils/logger.py`, stdout is explicitly reconfigured:
> ```python
> if sys.platform.startswith("win"):
>     sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
> ```
> This ensures resilient logging across all platforms and international currencies.

---

### Part 5: Full-Stack Engineering & Scalability

#### Q10. Why are heavy CPU-bound operations in FastAPI wrapped with `asyncio.to_thread`?
> **Answer**: FastAPI runs an asynchronous event loop on a single main thread. Running CPU-intensive or synchronous blocking I/O (such as PyMuPDF extraction, SentenceTransformer embedding calculation, or synchronous `requests` calls) on the main thread blocks the event loop, preventing all concurrent requests (e.g., status polling or chat queries) from executing.
> By wrapping synchronous functions in `await asyncio.to_thread(...)`, FastAPI offloads the execution to AnyIO's thread pool worker threads, keeping the asyncio event loop responsive to incoming HTTP requests.

#### Q11. How does `RichMarkdownRenderer.tsx` dynamically detect and render charts from chat messages?
> **Answer**: `RichMarkdownRenderer` parses markdown table structures (`| Header 1 | Header 2 |`) into columns and row records. It inspects whether columns contain valid numeric financial values using `parseFinancialNumber()`.
> When at least 2 data rows and 1 numeric column are detected:
> - It provides an interactive header toolbar with **Table**, **Bar Chart**, and **Trend Line** view buttons.
> - In chart mode, it maps row labels to the X-axis (`XAxis dataKey="name"`) and numeric columns to Recharts `<Bar>` or `<Line>` components with custom glassmorphism tooltips and currency formatting.

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
