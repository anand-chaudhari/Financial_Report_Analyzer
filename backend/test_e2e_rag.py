import os
import fitz # PyMuPDF
from app.services.document_service import DocumentService
from app.rag.rag_service import RAGService

def test_full_pipeline():
    # Create a test PDF in memory
    doc = fitz.open()
    
    # Page 1: Revenue & Financial Highlights
    page1 = doc.new_page()
    page1.insert_text(
        (50, 50),
        "Infosys Limited Financial Report FY2025\n"
        "Item 7. Management's Discussion and Analysis of Financial Condition\n"
        "Total consolidated revenue for fiscal year 2025 reached $18.6 billion, representing an 8.4% YoY growth.\n"
        "Operating margin for the fiscal year stood at 21.2% driven by digital services acceleration."
    )
    
    # Page 2: Cash Flows & Dividends
    page2 = doc.new_page()
    page2.insert_text(
        (50, 50),
        "Item 8. Consolidated Cash Flow Statement\n"
        "Cash flows from operating activities totaled $3.45 billion for FY2025.\n"
        "Free cash flow generation remained robust at $2.90 billion, supporting a final dividend payout of $1.10 per share."
    )

    pdf_bytes = doc.tobytes()
    doc.close()

    user_id = "test_user_cfo"
    filename = "Infosys_AR_FY2025.pdf"

    # Step 1: Upload and process PDF
    doc_service = DocumentService()
    doc_model = doc_service.process_and_save_upload(
        file_bytes=pdf_bytes,
        filename=filename,
        user_id=user_id
    )

    print(f"\n[UPLOAD SUCCESS] Document ID: {doc_model.documentId}, Pages: {doc_model.pageCount}, Company: {doc_model.companyName}")

    # Step 2: Query RAG engine for Revenue
    rag = RAGService()
    res1 = rag.answer_question(
        user_id=user_id,
        document_id=doc_model.documentId,
        question="What were the key drivers of revenue growth and operating margin this fiscal year?"
    )

    print("\n--- RAG ANSWER 1 (Revenue & Growth) ---")
    print("Answer:", res1["answer"])
    print("Pages:", res1["pages"])
    print("Sections:", res1["sections"])

    # Step 3: Query RAG engine for Cash Flow
    res2 = rag.answer_question(
        user_id=user_id,
        document_id=doc_model.documentId,
        question="Summarize cash flows from operating activities and free cash flow."
    )

    print("\n--- RAG ANSWER 2 (Cash Flow) ---")
    print("Answer:", res2["answer"])
    print("Pages:", res2["pages"])
    print("Sections:", res2["sections"])

if __name__ == "__main__":
    test_full_pipeline()
