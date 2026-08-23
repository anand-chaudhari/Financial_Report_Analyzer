import os
import requests
try:
    import pymupdf as fitz
except ImportError:
    import fitz

def create_sample_pdf(filename="sample_test_10k.pdf"):
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((50, 50), "UNITED STATES SECURITIES AND EXCHANGE COMMISSION\nWASHINGTON, D.C. 20549\n\nFORM 10-K\n\nANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934\n\nFor the fiscal year ended September 28, 2024\n\nAPPLE INC.\nExact name of registrant as specified in its charter\n\nState of Incorporation: California\n\nItem 1. Business\nApple designs, manufactures and markets smartphones, personal computers, tablets, wearables and accessories, and sells a variety of related services.")
    
    page2 = doc.new_page()
    page2.insert_text((50, 50), "Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations\n\nTotal net sales were $391,035 million in 2024, compared to $383,285 million in 2023.\nServices revenue reached $96,169 million.\n\nGross margin was $180,683 million.")
    
    page3 = doc.new_page()
    page3.insert_text((50, 50), "Item 8. Financial Statements and Supplementary Data\n\nConsolidated Statements of Operations\nNet income: $93,736 million\nDiluted earnings per share: $6.08\n\nEnd of report.")
    
    doc.save(filename)
    doc.close()
    return filename

def test_upload():
    pdf_path = create_sample_pdf()
    
    url = "http://127.0.0.1:8000/api/documents/upload"
    headers = {
        "Authorization": "Bearer mock_dev_token"
    }
    
    with open(pdf_path, "rb") as f:
        files = {"file": (pdf_path, f, "application/pdf")}
        response = requests.post(url, headers=headers, files=files)
        
    print("Response Status Code:", response.status_code)
    try:
        data = response.json()
        print("Response JSON:", data)
    except Exception as e:
        print("Response Text:", response.text)
        
    if os.path.exists(pdf_path):
        os.remove(pdf_path)

if __name__ == "__main__":
    test_upload()
