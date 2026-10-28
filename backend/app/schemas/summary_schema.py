from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class SummarySectionItem(BaseModel):
    text: str = ""
    pages: List[int] = Field(default_factory=list)
    value: Optional[str] = None

    @field_validator("text", mode="before")
    @classmethod
    def sanitize_text(cls, v):
        if v is None:
            return ""
        return str(v)


class KpiCardItem(BaseModel):
    label: str = "Financial Metric"
    value: Optional[str] = "Not disclosed"
    change: Optional[str] = None
    icon: Optional[str] = None

    @field_validator("value", mode="before")
    @classmethod
    def sanitize_value(cls, v):
        if v is None or str(v).strip().lower() in ("none", "null", ""):
            return "Not disclosed"
        return str(v).strip()

    @field_validator("label", mode="before")
    @classmethod
    def sanitize_label(cls, v):
        if not v or str(v).strip().lower() in ("none", "null", ""):
            return "Financial Metric"
        return str(v).strip()


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
