# FinSight AI — Financial Report Analyzer AI

[![Quick Start Guide](https://img.shields.io/badge/Quick_Start-Copy--Paste_Commands-10b981?style=for-the-badge)](./QUICKSTART.md)

> For instant copy-pasteable commands to run the project without re-installing dependencies, see [QUICKSTART.md](./QUICKSTART.md).

An enterprise-grade, academic full-stack application designed to ingest, process, and analyze corporate financial reports (10-K, 10-Q, quarterly earnings) using Retrieval-Augmented Generation (RAG).

---

## 🌟 Key Features

1. **Secure Authentication**: Firebase Auth for email/password and OAuth login.
2. **PDF Ingestion & Parsing**: PyMuPDF (Fitz) extracts text with strict page number tracking.
3. **Semantic Chunking & Clean Text**: Financial notation preservation and recursive character splitting.
4. **Local Vector Search**: ChromaDB vector store with SentenceTransformers (`all-MiniLM-L6-v2`) embeddings.
5. **Grounded RAG Q&A**: LLM responses strictly grounded in the document with page number citations (`[Page X]`).
6. **Hallucination Prevention**: Explicit fallback disclaimers when facts are absent from the document.
7. **Financial Data Visualizations**: Interactive charts rendered with Recharts from extracted financial metrics.
8. **Multi-tenant Cloud Storage & Database**: Firebase Storage and Cloud Firestore for document and chat persistence.

---

## 🏗️ Architecture & Tech Stack

- **Frontend**: React 18, Vite, TypeScript/JavaScript, Tailwind CSS, React Router v6, Axios, Recharts, Lucide Icons.
- **Backend**: Python 3.10+, FastAPI, Pydantic v2, Uvicorn.
- **AI / RAG**: LangChain, PyMuPDF, Sentence Transformers, ChromaDB, Google Gemini / OpenAI.
- **Cloud / BaaS**: Firebase Authentication, Cloud Firestore, Firebase Storage, Firebase Admin SDK.

---

## 📁 Repository Structure

```
FINANCE_REPORT_ANALYZER_AI/
├── backend/                  # FastAPI Application
│   ├── app/
│   │   ├── api/              # API dependencies & auth guards
│   │   ├── config/           # App settings & env loading
│   │   ├── document_processing/ # PDF extraction, cleaning, chunking
│   │   ├── firebase/         # Firebase Admin SDK, Auth, Firestore, Storage
│   │   ├── llm/              # LLM client abstractions
│   │   ├── models/           # Domain data models
│   │   ├── rag/              # RAG query pipeline & prompt templates
│   │   ├── routes/           # FastAPI APIRouter endpoints
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Business logic layer
│   │   ├── utils/            # Logging, helpers
│   │   ├── vectorstore/      # ChromaDB client & embedding wrappers
│   │   └── main.py           # Application entrypoint
│   ├── requirements.txt
│   └── .env.example
├── frontend/                 # React + Vite Application
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── context/          # React context providers (Auth, Report)
│   │   ├── firebase/         # Firebase Web SDK initialization
│   │   ├── hooks/            # Custom React hooks
│   │   ├── layouts/          # Page layout wrappers (Main, Auth)
│   │   ├── pages/            # Application view pages
│   │   ├── services/         # API & HTTP client services
│   │   ├── types/            # TypeScript interfaces / type definitions
│   │   ├── utils/            # Formatting & constants
│   │   ├── App.tsx           # Router & root component
│   │   └── main.tsx          # React DOM entrypoint
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── .env.example
├── .gitignore
├── .env.example
└── README.md
```

---

## 🚀 Quick Start Guide

### Prerequisites
- Node.js (v18+) and npm
- Python (v3.10+)

### 1. Backend Setup

```bash
# 1. IMPORTANT: Navigate to the backend directory first!
cd backend

# 2. Create virtual environment (if not created yet)
python -m venv .venv

# 3. Activate virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# Windows (Command Prompt - CMD):
.venv\Scripts\activate.bat

# Linux / macOS:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure environment variables
cp .env.example .env

# 6. Run development server:
# Option A: After activating virtual environment inside backend/
uvicorn app.main:app --reload --port 8000

# Option B: Direct run from backend/ directory (Windows PowerShell / CMD)
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Backend Swagger UI will be available at: `http://localhost:8000/docs`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment variables
cp .env.example .env

# Start development server
npm run dev
```

Frontend app will be available at: `http://localhost:5173`
