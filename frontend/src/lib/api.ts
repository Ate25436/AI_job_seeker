import axios from 'axios';
import { QuestionRequest, AnswerResponse, HealthResponse } from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  async askQuestion(question: string): Promise<AnswerResponse> {
    const response = await apiClient.post<AnswerResponse>('/api/ask', {
      question,
    } as QuestionRequest);
    return response.data;
  },

  async healthCheck(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>('/api/health');
    return response.data;
  },
};