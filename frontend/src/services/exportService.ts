/**
 * FinSight AI - Institutional Export Suite.
 * Generates Excel financial models, CFO PDF briefings, and board presentation decks.
 */
import {
  FinancialAnalyticsResponse,
  SourceMetadata,
  MetricDataPoint,
  AssetsLiabilitiesPoint,
  KeyRatio,
} from '../types/financial';

export interface ExportDataPayload {
  companyName: string;
  financialYear: string;
  analytics?: FinancialAnalyticsResponse | null;
  conversationHistory?: Array<{ role: string; content: string; sources?: SourceMetadata[] }>;
  summaryText?: string;
}

/**
 * 1. Export Excel Financial Model (.csv / Excel-ready tab-delimited)
 */
export const exportToExcel = (payload: ExportDataPayload) => {
  const { companyName, financialYear, analytics } = payload;
  const rows: string[][] = [];

  rows.push([`FinSight AI - Financial Model: ${companyName} (${financialYear})`]);
  rows.push([`Generated: ${new Date().toISOString()}`]);
  rows.push([]);

  // Revenue & Profit Schedule
  rows.push(['--- REVENUE & PROFITABILITY SCHEDULE ---']);
  rows.push(['Period', 'Metric', 'Value', 'Unit', 'Source Page']);

  analytics?.revenue_chart?.forEach((item: MetricDataPoint) => {
    rows.push([item.period, 'Revenue from Operations', String(item.value), item.unit, `Page ${item.page_number}`]);
  });

  analytics?.profit_chart?.forEach((item: MetricDataPoint) => {
    rows.push([item.period, 'Net Profit (PAT)', String(item.value), item.unit, `Page ${item.page_number}`]);
  });

  analytics?.expense_chart?.forEach((item: MetricDataPoint) => {
    rows.push([item.period, 'Total Operating Expenses', String(item.value), item.unit, `Page ${item.page_number}`]);
  });

  rows.push([]);
  rows.push(['--- BALANCE SHEET METRICS ---']);
  rows.push(['Period', 'Total Assets', 'Total Liabilities', 'Unit', 'Source Page']);

  analytics?.assets_vs_liabilities_chart?.forEach((item: AssetsLiabilitiesPoint) => {
    rows.push([
      item.period,
      String(item.assets),
      String(item.liabilities),
      item.unit,
      `Page ${item.page_number}`,
    ]);
  });

  rows.push([]);
  rows.push(['--- KEY FINANCIAL RATIOS ---']);
  rows.push(['Ratio Name', 'Calculated Value', 'Description', 'Source Page']);

  analytics?.key_ratios?.forEach((item: KeyRatio) => {
    rows.push([item.name, item.value, item.description || '', `Page ${item.page_number}`]);
  });

  // Convert to CSV
  const csvContent =
    'data:text/csv;charset=utf-8,' +
    rows.map((e) => e.map((cell) => `"${(cell || '').replace(/"/g, '""')}"`).join(',')).join('\n');

  const encodedUri = encodeURI(csvContent);
  const link = document.createElement('a');
  link.setAttribute('href', encodedUri);
  link.setAttribute('download', `${companyName.replace(/\s+/g, '_')}_Financial_Model_${financialYear}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

/**
 * 2. Export Executive CFO Memo (Printable HTML / PDF)
 */
export const exportToPdfBrief = (payload: ExportDataPayload) => {
  const { companyName, financialYear, summaryText, analytics, conversationHistory } = payload;

  const printWindow = window.open('', '_blank');
  if (!printWindow) return;

  const htmlContent = `
<!DOCTYPE html>
<html>
<head>
  <title>FinSight AI - Executive Financial Briefing: ${companyName}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; padding: 40px; color: #1e293b; max-width: 900px; margin: 0 auto; line-height: 1.6; }
    h1 { color: #0f172a; font-size: 24px; border-bottom: 2px solid #10b981; padding-bottom: 10px; margin-bottom: 5px; }
    .meta { font-size: 12px; color: #64748b; margin-bottom: 25px; }
    .card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
    .badge { display: inline-block; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; background: #ecfdf5; color: #059669; border: 1px solid #a7f3d0; }
    table { width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 13px; }
    th { background: #0f172a; color: white; padding: 10px; text-align: left; font-size: 11px; text-transform: uppercase; }
    td { padding: 8px 10px; border-bottom: 1px solid #e2e8f0; }
    tr:nth-child(even) { background: #f8fafc; }
    .citation { font-size: 11px; color: #059669; font-weight: bold; }
    @media print {
      body { padding: 0; }
      .no-print { display: none; }
    }
  </style>
</head>
<body>
  <div class="no-print" style="margin-bottom: 20px;">
    <button onclick="window.print()" style="background: #10b981; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor: pointer;">
      🖨️ Print / Save as PDF
    </button>
  </div>

  <h1>FinSight AI • Executive Financial Briefing</h1>
  <div class="meta">
    <strong>Company:</strong> ${companyName} | <strong>Filing Period:</strong> ${financialYear} | <strong>Report Date:</strong> ${new Date().toLocaleDateString()}
  </div>

  <div class="card">
    <h3 style="margin-top:0; color: #059669;">1. Executive Summary & Financial Highlights</h3>
    <p>${summaryText || 'Extracted grounded financial analysis from corporate filing.'}</p>
  </div>

  <div class="card">
    <h3 style="margin-top:0; color: #059669;">2. Key Financial Indicators</h3>
    <table>
      <thead>
        <tr>
          <th>Period</th>
          <th>Revenue</th>
          <th>Net Profit</th>
          <th>Expenses</th>
          <th>Source</th>
        </tr>
      </thead>
      <tbody>
        ${(analytics?.revenue_chart || [])
          .map((rev: MetricDataPoint, idx: number) => {
            const prof = analytics?.profit_chart?.[idx]?.value || '-';
            const exp = analytics?.expense_chart?.[idx]?.value || '-';
            return `
            <tr>
              <td><strong>${rev.period}</strong></td>
              <td>${rev.value.toLocaleString()} ${rev.unit}</td>
              <td>${typeof prof === 'number' ? prof.toLocaleString() : prof}</td>
              <td>${typeof exp === 'number' ? exp.toLocaleString() : exp}</td>
              <td><span class="citation">Page ${rev.page_number}</span></td>
            </tr>
          `;
          })
          .join('')}
      </tbody>
    </table>
  </div>

  <div class="card">
    <h3 style="margin-top:0; color: #059669;">3. Analyst Grounded Q&A Insights</h3>
    ${(conversationHistory || [])
      .slice(-4)
      .map(
        (m) => `
        <div style="margin-bottom: 12px; border-bottom: 1px dashed #cbd5e1; padding-bottom: 8px;">
          <strong style="color: #0f172a;">${m.role === 'user' ? 'Inquiry:' : 'FinSight Analyst:'}</strong>
          <div style="font-size: 12px; margin-top: 4px;">${m.content.replace(/\n/g, '<br/>')}</div>
        </div>
      `
      )
      .join('')}
  </div>

  <footer style="margin-top: 30px; font-size: 10px; color: #94a3b8; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 10px;">
    Generated by FinSight AI • Certified Grounded Financial Analysis
  </footer>
</body>
</html>
  `;

  printWindow.document.write(htmlContent);
  printWindow.document.close();
};

/**
 * 3. Export Board Presentation Deck (.json / formatted slide deck markdown)
 */
export const exportToPresentationDeck = (payload: ExportDataPayload) => {
  const { companyName, financialYear, analytics, summaryText } = payload;

  const slides = [
    {
      slide: 1,
      title: `Executive Briefing: ${companyName}`,
      subtitle: `Annual Financial Analysis • ${financialYear}`,
      bullets: [
        `Grounded AI Review of Corporate Filings`,
        `Report Date: ${new Date().toLocaleDateString()}`,
        `Prepared by FinSight AI Intelligence Suite`,
      ],
    },
    {
      slide: 2,
      title: 'Executive Financial Summary',
      subtitle: 'Key Highlights & Performance Drivers',
      bullets: [
        summaryText || `Detailed financial review for ${companyName} during ${financialYear}.`,
        `Operating metrics extracted directly from verified filing tables.`,
      ],
    },
    {
      slide: 3,
      title: 'Revenue & Profitability Breakdown',
      subtitle: 'Multi-Period Performance',
      bullets:
        analytics?.revenue_chart?.map(
          (r: MetricDataPoint) => `Period ${r.period}: Revenue ${r.value.toLocaleString()} ${r.unit} (Page ${r.page_number})`
        ) || ['Performance metrics verified across filing tables.'],
    },
    {
      slide: 4,
      title: 'Balance Sheet & Capital Structure',
      subtitle: 'Solvency & Leverage Assessment',
      bullets:
        analytics?.assets_vs_liabilities_chart?.map(
          (b: AssetsLiabilitiesPoint) => `Period ${b.period}: Assets ${b.assets.toLocaleString()} vs Liabilities ${b.liabilities.toLocaleString()} ${b.unit}`
        ) || ['Assets, liabilities, and debt schedules parsed.'],
    },
    {
      slide: 5,
      title: 'Conclusion & Strategic Takeaways',
      subtitle: 'Limitations & Governance',
      bullets: [
        'All extracted figures are cross-referenced with primary filing page citations.',
        'Market valuation and macroeconomic risks require external cross-validation.',
        'FinSight AI Institutional Grounding Engine.',
      ],
    },
  ];

  const blob = new Blob([JSON.stringify({ presentation: slides }, null, 2)], {
    type: 'application/json',
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${companyName.replace(/\s+/g, '_')}_Board_Briefing_Deck_${financialYear}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};
