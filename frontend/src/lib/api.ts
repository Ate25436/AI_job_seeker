import axios from 'axios';
import {
  AnswerResponse,
  ChatHistoryItem,
  GameAnswerResponse,
  GameEndRequest,
  GameEndResponse,
  GameQuestionRequest,
  GameResultResponse,
  GameSessionResponse,
  GameStartRequest,
  HealthResponse,
  QuestionRequest,
  ScoreSubmissionRequest,
  ScoreSubmissionResponse,
} from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  async askQuestion(
    question: string,
    history: ChatHistoryItem[] = []
  ): Promise<AnswerResponse> {
    const response = await apiClient.post<AnswerResponse>('/api/ask', {
      question,
      history,
    } as QuestionRequest);
    return response.data;
  },

  async healthCheck(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>('/api/health');
    return response.data;
  },

  async startGameSession(
    payload: GameStartRequest = { scenario_mode: 'fixed' }
  ): Promise<GameSessionResponse> {
    const response = await apiClient.post<GameSessionResponse>('/api/game/start', payload);
    return response.data;
  },

  async askGameQuestion(payload: GameQuestionRequest): Promise<GameAnswerResponse> {
    const response = await apiClient.post<GameAnswerResponse>('/api/game/ask', payload);
    return response.data;
  },

  async endGameSession(payload: GameEndRequest): Promise<GameEndResponse> {
    const response = await apiClient.post<GameEndResponse>('/api/game/end', payload);
    return response.data;
  },

  async submitGameScore(payload: ScoreSubmissionRequest): Promise<ScoreSubmissionResponse> {
    const response = await apiClient.post<ScoreSubmissionResponse>('/api/game/score', payload);
    return response.data;
  },

  async getGameResult(sessionId: string): Promise<GameResultResponse> {
    const response = await apiClient.get<GameResultResponse>(`/api/game/result/${sessionId}`);
    return response.data;
  },
};
