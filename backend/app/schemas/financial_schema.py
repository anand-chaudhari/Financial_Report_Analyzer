from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MetricDataPoint(BaseModel):
    period: str  # e.g., "FY2023", "2024", "Q3 2024"
    value: float
    unit: str = "USD Millions"
    page_number: Optional[int] = 1
    metric_name: Optional[str] = None


# Backward compatibility alias
FinancialMetricSeries = MetricDataPoint


class AssetsLiabilitiesPoint(BaseModel):
    period: str
    assets: float
    liabilities: float
    unit: str = "USD Millions"
    page_number: Optional[int] = 1


class CashFlowPoint(BaseModel):
    period: str
    operating: Optional[float] = None
    investing: Optional[float] = None
    financing: Optional[float] = None
    net_cash_flow: Optional[float] = None
    unit: str = "USD Millions"
    page_number: Optional[int] = 1


class YoYComparisonPoint(BaseModel):
    metric_name: str
    previous_year_period: str
    previous_year_value: float
    current_year_period: str
    current_year_value: float
    yoy_change_percent: Optional[float] = None
    unit: str = "USD Millions"
    page_number: Optional[int] = 1


class KeyRatio(BaseModel):
    name: str
    value: str
    description: Optional[str] = None
    page_number: Optional[int] = None


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
    has_data: bool = False
    currency: str = "USD"
    
    # 6 Analytics Dashboard Charts:
    revenue_chart: List[MetricDataPoint] = Field(default_factory=list)
    profit_chart: List[MetricDataPoint] = Field(default_factory=list)
    expense_chart: List[MetricDataPoint] = Field(default_factory=list)
    assets_vs_liabilities_chart: List[AssetsLiabilitiesPoint] = Field(default_factory=list)
    cash_flow_chart: List[CashFlowPoint] = Field(default_factory=list)
    yoy_comparison_chart: List[YoYComparisonPoint] = Field(default_factory=list)
    
    # Key ratios & extras
    key_ratios: List[KeyRatio] = Field(default_factory=list)
    executive_insights: List[str] = Field(default_factory=list)
    executive_overview: Optional[str] = None
    raw_metrics: Dict[str, Any] = Field(default_factory=dict)
    extracted_at: datetime = Field(default_factory=datetime.utcnow)

    # Backward compatibility aliases
    @property
    def net_income_chart(self) -> List[MetricDataPoint]:
        return self.profit_chart

    @property
    def operating_expenses_chart(self) -> List[MetricDataPoint]:
        return self.expense_chart


class OverviewMetricItem(BaseModel):
    name: str
    fy2025_value: Optional[str] = "Not available in the report"
    fy2026_value: Optional[str] = "Not available in the report"
    growth: Optional[str] = "Not available in the report"
    unit: Optional[str] = None
    page_number: Optional[int] = None
    is_available: bool = True


class FinancialOverviewResponse(BaseModel):
    report_id: str
    company_name: str
    currency: str = "USD"
    has_data: bool = True
    reporting_periods: List[str] = Field(default_factory=lambda: ["FY2025", "FY2026"])
    revenue: OverviewMetricItem
    net_profit: OverviewMetricItem
    eps: OverviewMetricItem
    total_assets: OverviewMetricItem
    total_liabilities: OverviewMetricItem
    equity: OverviewMetricItem
    cash_flow: OverviewMetricItem
    important_ratios: List[OverviewMetricItem] = Field(default_factory=list)
    executive_overview: str = ""
    extracted_at: datetime = Field(default_factory=datetime.utcnow)


class RiskItem(BaseModel):
    title: str
    category: str = "Reported Risk"  # "Reported Risk" | "Financial Indicator/Observation"
    severity: str = "Medium"  # "High" | "Medium" | "Low" | "Informational"
    explanation: str
    supporting_evidence: str
    page_number: Optional[int] = 1
    section: Optional[str] = "Notes & MD&A"


class RiskAnalysisResponse(BaseModel):
    report_id: str
    company_name: str
    total_risks_count: int = 0
    reported_risks: List[RiskItem] = Field(default_factory=list)
    financial_indicators: List[RiskItem] = Field(default_factory=list)
    risk_summary: str = ""
    disclaimer: str = "This analysis highlights factual risks and financial indicators disclosed in the financial report. It does not constitute investment advice or recommendations."
    extracted_at: datetime = Field(default_factory=datetime.utcnow)


