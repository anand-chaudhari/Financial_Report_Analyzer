from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FinancialMetricSeries(BaseModel):
    period: str  # e.g., "2023 Q1", "FY 2022"
    value: float
    unit: str = "USD Millions"


class KeyRatio(BaseModel):
    name: str
    value: str
    description: Optional[str] = None


class FinancialSummaryResponse(BaseModel):
    report_id: str
    company_name: Optional[str] = "Unknown"
    fiscal_period: Optional[str] = "N/A"
    currency: str = "USD"
    executive_summary: str
    key_highlights: List[str] = Field(default_factory=list)
    risks_and_challenges: List[str] = Field(default_factory=list)


class FinancialChartDataResponse(BaseModel):
    report_id: str
    company_name: str
    revenue_chart: List[FinancialMetricSeries] = Field(default_factory=list)
    net_income_chart: List[FinancialMetricSeries] = Field(default_factory=list)
    operating_expenses_chart: List[FinancialMetricSeries] = Field(default_factory=list)
    key_ratios: List[KeyRatio] = Field(default_factory=list)
    raw_metrics: Dict[str, Any] = Field(default_factory=dict)
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
