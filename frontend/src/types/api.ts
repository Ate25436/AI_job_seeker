export interface QuestionRequest {
  question: string;
  history?: ChatHistoryItem[];
}

export interface AnswerResponse {
  answer: string;
  sources?: string[];
  timestamp: string;
  processing_time_ms?: number;
}

export interface ConversationHistory {
  id: string;
  question: string;
  answer: string;
  timestamp: string;
}

export type ChatRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp: string;
}

export interface ChatHistoryItem {
  role: ChatRole;
  content: string;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  database_status?: string;
  openai_status?: string;
}

export interface ErrorResponse {
  error: string;
  message: string;
  timestamp: string;
}
