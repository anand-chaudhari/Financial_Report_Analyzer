from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SummarySectionItem(BaseModel):
    text: str
    pages: List[int] = Field(default_factory=list)
    value: Optional[str] = None


class KpiCardItem(BaseModel):
    label: str
    value: str
    change: Optional[str] = None
    icon: Optional[str] = None


class DocumentSummaryResponse(BaseModel):
    success: bool = True
    document_id: str
    company_name: str = "Corporate Entity"
    financial_year: str = "FY2024"
    file_name: str = "Report.pdf"
    
    # 11 Required Grounded Sections
    executive_summary: SummarySectionItem
    key_financial_highlights: SummarySectionItem
    revenue: SummarySectionItem
    profit_loss: SummarySectionItem
    major_expenses: SummarySectionItem
    assets: SummarySectionItem
    liabilities: SummarySectionItem
    cash_flow: SummarySectionItem
    business_risks: SummarySectionItem
    management_discussion: SummarySectionItem
    future_plans: SummarySectionItem

    # KPI summary cards
    kpis: List[KpiCardItem] = Field(default_factory=list)
