export interface Citation {
  page_number: number;
  snippet: string;
  chunk_id?: string;
  similarity_score?: number;
  section?: string;
  document_name?: string;
  is_verified?: boolean;
}

export interface ChatMessage {
  id?: string;
  sender: 'user' | 'assistant' | 'system';
  content: string;
  citations: Citation[];
  is_grounded: boolean;
  timestamp: string;
}

export interface ChatQueryRequest {
  report_id: string;
  question: string;
  top_k?: number;
}

export interface ChatQueryResponse {
  answer: string;
  citations: Citation[];
  is_grounded: boolean;
  source_found: boolean;
}
