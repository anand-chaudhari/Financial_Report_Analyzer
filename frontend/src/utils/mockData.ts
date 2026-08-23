export interface MockReport {
  id: string;
  filename: string;
  company: string;
  ticker: string;
  filingType: '10-K' | '10-Q' | 'Earnings' | 'Annual';
  uploadDate: string;
  totalPages: number;
  fileSize: number;
  status: 'ready' | 'processing' | 'error';
  revenue?: string;
  netIncome?: string;
  growth?: string;
  tags: string[];
}

export interface MockConversation {
  id: string;
  reportId: string;
  reportName: string;
  ticker: string;
  question: string;
  answer: string;
  timestamp: string;
  citations: Array<{
    page_number: number;
    snippet: string;
    section?: string;
  }>;
}

export interface MockNotification {
  id: string;
  title: string;
  description: string;
  timestamp: string;
  read: boolean;
  type: 'success' | 'info' | 'warning';
}

export const MOCK_REPORTS: MockReport[] = [
  {
    id: 'rep_aapl_2024_10k',
    filename: 'Apple_Inc_FY2024_10K_Annual_Report.pdf',
    company: 'Apple Inc.',
    ticker: 'AAPL',
    filingType: '10-K',
    uploadDate: '2024-10-31T14:20:00Z',
    totalPages: 124,
    fileSize: 14889790, // ~14.2 MB
    status: 'ready',
    revenue: '$391.0B',
    netIncome: '$93.7B',
    growth: '+2.0%',
    tags: ['Services Growth', 'iPhone 16 Cycle', 'Gross Margin 46.2%'],
  },
  {
    id: 'rep_msft_q3_10q',
    filename: 'Microsoft_Corp_Q3_FY24_Form_10Q.pdf',
    company: 'Microsoft Corp',
    ticker: 'MSFT',
    filingType: '10-Q',
    uploadDate: '2024-10-24T09:15:00Z',
    totalPages: 56,
    fileSize: 7130316, // ~6.8 MB
    status: 'ready',
    revenue: '$65.6B',
    netIncome: '$24.7B',
    growth: '+16.0%',
    tags: ['Azure AI +33%', 'Cloud Revenue', 'Copilot Monetization'],
  },
  {
    id: 'rep_nvda_q4_earnings',
    filename: 'NVIDIA_Q4_FY24_Financial_Results.pdf',
    company: 'NVIDIA Corporation',
    ticker: 'NVDA',
    filingType: 'Earnings',
    uploadDate: '2024-11-15T18:45:00Z',
    totalPages: 32,
    fileSize: 3565158, // ~3.4 MB
    status: 'ready',
    revenue: '$35.1B',
    netIncome: '$19.3B',
    growth: '+94.0%',
    tags: ['Hopper & Blackwell', 'Data Center 88%', 'Gross Margin 74.6%'],
  },
  {
    id: 'rep_googl_2024_10k',
    filename: 'Alphabet_Inc_2024_Annual_Filing_10K.pdf',
    company: 'Alphabet Inc.',
    ticker: 'GOOGL',
    filingType: '10-K',
    uploadDate: '2024-11-02T11:30:00Z',
    totalPages: 98,
    fileSize: 12058624, // ~11.5 MB
    status: 'ready',
    revenue: '$88.3B',
    netIncome: '$26.3B',
    growth: '+15.1%',
    tags: ['Google Cloud +35%', 'Search Advertising', 'YouTube Subs'],
  },
  {
    id: 'rep_tsla_q2_10q',
    filename: 'Tesla_Inc_Q2_2024_Quarterly_10Q.pdf',
    company: 'Tesla Inc.',
    ticker: 'TSLA',
    filingType: '10-Q',
    uploadDate: '2024-07-25T16:10:00Z',
    totalPages: 44,
    fileSize: 5347737, // ~5.1 MB
    status: 'ready',
    revenue: '$25.5B',
    netIncome: '$1.48B',
    growth: '+2.3%',
    tags: ['Energy Storage 9.4 GWh', 'Auto Gross Margin 14.6%', 'FSD v12'],
  },
  {
    id: 'rep_amzn_2024_10k',
    filename: 'Amazon_com_Inc_2024_Annual_Report.pdf',
    company: 'Amazon.com, Inc.',
    ticker: 'AMZN',
    filingType: 'Annual',
    uploadDate: '2024-11-18T10:05:00Z',
    totalPages: 112,
    fileSize: 13421772, // ~12.8 MB
    status: 'processing',
    revenue: '$158.9B',
    netIncome: '$15.3B',
    growth: '+11.0%',
    tags: ['AWS Growth +19%', 'Operating Income $17.4B', 'Ads Revenue'],
  },
];

export const MOCK_CONVERSATIONS: MockConversation[] = [
  {
    id: 'conv_1',
    reportId: 'rep_aapl_2024_10k',
    reportName: 'Apple Inc. FY24 10-K',
    ticker: 'AAPL',
    question: 'What is Apple’s total Services revenue and gross margin for FY2024?',
    answer:
      'Apple reported total Services revenue of $96.17 billion for fiscal year 2024, up 12.9% year-over-year from $85.20 billion in FY2023. Services gross margin reached 74.2%, driven by growth in App Store, Cloud Services, and Apple Pay transactions.',
    timestamp: '15 mins ago',
    citations: [
      {
        page_number: 34,
        section: 'Item 7 - MD&A Services Segment',
        snippet: 'Services net sales increased 13% or $10.97 billion during 2024 compared to 2023, primarily due to higher net sales from advertising, cloud services and payment services.',
      },
      {
        page_number: 38,
        section: 'Gross Margin Breakdown',
        snippet: 'Services gross margin was $71.3 billion (74.2%) compared to $60.3 billion (70.8%) in 2023.',
      },
    ],
  },
  {
    id: 'conv_2',
    reportId: 'rep_msft_q3_10q',
    reportName: 'Microsoft Corp Q3 10-Q',
    ticker: 'MSFT',
    question: 'What are Microsoft’s primary risk disclosures regarding AI infrastructure and GPU supplies?',
    answer:
      'Microsoft disclosed that scaling Azure AI infrastructure is subject to semiconductor supply chain lead times, high-density power constraints in Tier-1 data center locations, and third-party accelerator allocations.',
    timestamp: '1 hour ago',
    citations: [
      {
        page_number: 22,
        section: 'Part II Item 1A - Risk Factors',
        snippet: 'We continue to experience high demand for our AI services and data center capacity. If we are unable to scale our infrastructure, including acquiring necessary compute GPUs and data center real estate, our cloud revenue growth could be constrained.',
      },
    ],
  },
  {
    id: 'conv_3',
    reportId: 'rep_nvda_q4_earnings',
    reportName: 'NVIDIA Corp Q4 Earnings',
    ticker: 'NVDA',
    question: 'What was NVIDIA’s Data Center revenue breakdown and sequential growth rate?',
    answer:
      'Data Center revenue reached a record $30.8 billion in the quarter, representing 88% of total revenue and a 112% increase year-over-year, propelled by Hopper architecture demand and initial Blackwell sampling shipments.',
    timestamp: '3 hours ago',
    citations: [
      {
        page_number: 8,
        section: 'Segment Performance - Data Center',
        snippet: 'Fourth quarter Data Center revenue of $30.8 billion was up 17% from the previous quarter and up 112% from a year ago.',
      },
    ],
  },
  {
    id: 'conv_4',
    reportId: 'rep_tsla_q2_10q',
    reportName: 'Tesla Inc. Q2 10-Q',
    ticker: 'TSLA',
    question: 'Summarize Tesla’s Energy Storage deployment growth and automotive gross margin.',
    answer:
      'Tesla deployed 9.4 GWh of Megapack and Powerwall storage in Q2, a new all-time quarterly record and more than double the prior quarter. Automotive gross margin excluding regulatory credits was 14.6%.',
    timestamp: 'Yesterday',
    citations: [
      {
        page_number: 17,
        section: 'Energy Generation and Storage',
        snippet: 'Energy storage deployments reached 9.4 GWh in Q2 2024, resulting in record quarterly profit for the Energy business.',
      },
    ],
  },
];

export const MOCK_STATS = {
  totalReports: 18,
  totalReportsChange: '+4 this month',
  reportsProcessed: 18,
  processingSuccessRate: '100%',
  questionsAsked: 142,
  questionsChange: '+28% this week',
  avgRetrievalTime: '0.8s',
  totalStorageBytes: 44564480, // ~42.5 MB
};

export const MOCK_NOTIFICATIONS: MockNotification[] = [
  {
    id: 'notif_1',
    title: 'Report Indexing Complete',
    description: 'Apple_Inc_FY2024_10K_Annual_Report.pdf (124 pages) is indexed and ready for Q&A.',
    timestamp: '5 mins ago',
    read: false,
    type: 'success',
  },
  {
    id: 'notif_2',
    title: 'Financial Tables Extracted',
    description: 'Extracted balance sheet & cash flow statements for Microsoft Corp Q3 10-Q.',
    timestamp: '1 hour ago',
    read: false,
    type: 'info',
  },
  {
    id: 'notif_3',
    title: 'New AI Insight Available',
    description: 'Automated executive summary generated for NVIDIA Q4 Earnings.',
    timestamp: '3 hours ago',
    read: true,
    type: 'info',
  },
];
