# FinSight AI — Architecture, Performance & Complete Workflow Guide

FinSight AI is an enterprise-grade, local-first Financial Report Intelligence platform powered by Retrieval-Augmented Generation (RAG). It enables financial analysts to upload massive corporate disclosures (10-K, 10-Q, annual reports up to **500+ pages / 200MB**, Word documents, and financial spreadsheets) and interact with them in natural, conversational language with 100% source-grounded accuracy and zero cross-document contamination.

---

## 1. High-Level System Architecture

```mermaid
graph TD
    User["👤 Financial Analyst (Browser)"] -->|1. Upload PDF / DOCX / CSV| Frontend["⚡ React + Vite Frontend"]
    Frontend -->|2. POST /api/v1/documents/upload| FastAPI["🚀 FastAPI Server (Port 8000)"]
    FastAPI -->|3. 1MB Chunked Disk Stream + Concurrent SHA-256| Disk["📁 Local Disk Storage (uploads/)"]
    
    FastAPI -->|4. Check Fingerprint: doc_hash + model + v2.2.0| CacheCheck{"Existing Cache Verified?"}
    CacheCheck -- YES --> InstantReady["⚡ Instant Return: Status READY (0ms)"]
    InstantReady --> Frontend
    
    CacheCheck -- NO --> QueueJob["⚙️ Enqueue to BackgroundWorkerPool"]
    QueueJob -->|5. Return HTTP 200 & Document Record| Frontend
    
    subgraph Background Worker Execution
        QueueJob --> FormatRouter{"Format Router"}
        FormatRouter -- .pdf --> PyMuPDF["📄 PDF Extractor (Batch=30, PyMuPDF)"]
        PyMuPDF --> SelectiveOCR{"Chars < 20?"}
        SelectiveOCR -- Yes --> VisionOCR["👁️ Gemini 2.0 Flash Vision OCR"]
        SelectiveOCR -- No --> UnifiedDoc["📋 Unified ExtractedDocument"]
        VisionOCR --> UnifiedDoc
        
        FormatRouter -- .docx --> DocxExtractor["📝 Word Extractor (Interleaved w:p & w:tbl)"]
        DocxExtractor --> UnifiedDoc
        
        FormatRouter -- .csv/.tsv --> CSVExtractor["📊 CSV Extractor (Delimiter Sniffer + 35-Row Chunks)"]
        CSVExtractor --> UnifiedDoc
        
        UnifiedDoc --> Chunker["🧩 Table-Aware Chunker (Prepends Table Headers)"]
        Chunker --> Embedder["🧠 BAAI/bge-small-en-v1.5 Dense Embeddings (384-dim)"]
        Embedder --> ChromaDB["🗄️ ChromaDB Vector Store (Scoped by document_id)"]
        ChromaDB --> Verify["✅ Vector Persistence Verification"]
        Verify --> ReadyState["Status = COMPLETED, Stage = READY"]
    end

    Frontend -->|6. Poll GET /status (1.5s)| FastAPI
    FastAPI -->|7. Real-time Progress (0-100%)| Frontend
    ReadyState -->|8. Document Ready| Frontend
```

---

## 2. RAG Question Answering Flowchart

```mermaid
graph TD
    Analyst["💬 Analyst Asks Question"] -->|POST /api/v1/chat/stream| ChatRoute["API Route /chat/stream"]
    ChatRoute -->|Resolve document_id & user_id| RAGService["RAG Service"]
    
    RAGService -->|Query Similarity| VectorService["ChromaDB Vector Store"]
    VectorService -->|Strict Filter: document_id (Zero Bleed)| ChromaDB["🗄️ ChromaDB Collection"]
    ChromaDB -->|Return Top-15 Candidate Chunks| VectorService
    
    VectorService -->|Apply Keyword BM25 & Table Priority Boost| RAGService
    RAGService -->|Format Context: Primary Document Evidence First| PromptBuilder["Context Assembly"]
    PromptBuilder -->|Inject Evidence + System Persona| GroqLLM["🤖 Groq LLM (Llama 3.3 70B Versatile)"]
    
    loop Server-Sent Events (SSE)
        GroqLLM -->|Stream Token Delta| ChatRoute
        ChatRoute -->|SSE Event: data: {token: ...}| Frontend["⚡ Split-View Chat UI"]
    end
    
    GroqLLM -->|Stream Complete| ChatRoute
    ChatRoute -->|SSE Event: [DONE] with Citations| Frontend
    ChatRoute -->|Persist Thread & Message| Storage["🔥 Firestore / Local Storage"]
```

---

## 3. Core Architectural Principles & Optimizations

### A. Zero-Memory 1 MB Chunked Streaming Upload
- **Problem**: Uploading a 200 MB annual report using standard `UploadFile.read()` loads the entire file into a RAM byte buffer. Under multiple concurrent uploads, this triggers out-of-memory crashes.
- **Solution**: The `POST /api/v1/documents/upload` endpoint streams incoming files directly to disk in **1 MB chunk buffers**:
  ```python
  hasher = hashlib.sha256()
  with open(temp_file_path, "wb") as f_out:
      while True:
          chunk = await file.read(1024 * 1024)
          if not chunk:
              break
          f_out.write(chunk)
          hasher.update(chunk)
  computed_hash = hasher.hexdigest()
  ```
  This keeps memory consumption flat at **1 MB**, while concurrently calculating the SHA-256 hash without requiring a second disk read.

### B. Table-Aware Chunking with Header Retention
- **Problem**: When a 60-row financial statement is split across chunk boundaries, sub-chunks lose their column headers (e.g. `FY22 | FY23 | FY24`), causing the LLM to hallucinate or misalign numbers.
- **Solution**: The chunker detects Markdown table blocks and automatically prepends the header row and separator line (`| Metric | FY23 | FY24 |\n|---|---|---|`) to every sub-chunk. Numerical disclosures are never severed from their column definitions.

### C. Elimination of Cross-Document Semantic Bleed
- **Problem**: When searching documents with sparse embeddings, standard RAG fallbacks drop the `document_id` filter and query across all user documents, causing data from one company (e.g. SBI) to bleed into queries for another company (e.g. Apple).
- **Solution**: FinSight AI strictly constrains ChromaDB vector queries:
  ```python
  where_filter = {"$and": [{"user_id": user_id}, {"document_id": document_id}]}
  ```
  Queries with a specified `document_id` never fall back to unfiltered searches.

### D. Deterministic Vector Cache Fingerprinting (`v2.2.0`)
- **Problem**: Analysts frequently re-upload the same report during research, causing redundant re-indexing and token consumption.
- **Solution**: Constructs a pipeline cache key:
  $$\text{Fingerprint} = \text{SHA256}(\text{File}) + \text{EmbeddingModel} + \text{PipelineVersion}$$
  If this fingerprint matches an existing indexed document and ChromaDB vector persistence is verified, the document is immediately marked `Ready` in **0 ms**.

### E. Selective Page-Level Multimodal OCR
- **Problem**: Running OCR on every page of a 500-page digital filing is slow and costly. Conversely, sampling a few pages risk missing scanned appendices.
- **Solution**: Evaluates every page individually:
  - If native character count $\ge 20$: Extracts text via **PyMuPDF** at C-speed.
  - If native character count $< 20$ and images are detected: Activates **Google Gemini 2.0 Flash Vision** exclusively on that page.
  - Pages exceeding the OCR budget are flagged in `unprocessed_ocr_pages` metadata rather than silently discarded.

---

## 4. End-to-End Ingestion Stages

| Stage Name | Progress % | Operation Description |
| :--- | :--- | :--- |
| **Uploading** | 0% – 20% | 1 MB chunked stream from client to server disk storage. |
| **Queued** | 20% – 25% | Pre-flight validation, magic-byte format detection, worker queue assignment. |
| **Analyzing** | 25% – 35% | Document structure inspection, page-level character density profiling. |
| **Extracting** | 35% – 55% | Native text & table extraction across PDF, DOCX, or CSV extractors. |
| **OCR** | 55% – 65% | Targeted Gemini Vision OCR on scanned or image-only pages. |
| **Chunking** | 65% – 75% | Table-aware Markdown splitting with column header preservation. |
| **Embedding** | 75% – 90% | Batched dense vector generation via BAAI/bge-small-en-v1.5. |
| **Indexing** | 90% – 98% | ChromaDB HNSW upsert, metadata indexing, and persistence verification. |
| **Ready** | 100% | Document indexing complete; interactive RAG analysis enabled. |

---

## 5. Failure Recovery & Background Idempotency

* **Collision Prevention**: `submit_background_processing` verifies `is_job_running(target_id)` before queueing, preventing duplicate parallel processing of the same filing.
* **One-Click Retry Endpoint**: If processing is interrupted (e.g., machine reboot), the client triggers `POST /api/v1/documents/{document_id}/retry`, which re-enqueues the saved file without requiring re-upload.
