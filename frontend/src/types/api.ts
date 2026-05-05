export type ChatRole = 'user' | 'assistant';
export type FeedbackMode = 'rule_based' | 'llm';

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

export interface GameStartRequest {
  scenario_mode?: 'fixed' | 'generated';
  scenario_file?: string;
  seed?: number;
}

export interface GameSessionResponse {
  session_id: string;
  status: string;
  started_at: string;
  expires_at: string;
  candidate_name: string;
  company_name: string;
  scenario_title: string;
  remaining_seconds: number;
}

export interface CandidateBriefingSection {
  title: string;
  summary: string;
}

export interface CandidateBriefingResponse {
  full_name: string;
  age: number;
  university: string;
  faculty_type: string;
  grade: number;
  desired_industry: string;
  desired_job_family: string;
  current_status_summary: string;
  personality_summary: string;
  entry_sheet_sections: CandidateBriefingSection[];
}

export interface CompanyBriefingResponse {
  company_name: string;
  industry: string;
  philosophy: string;
  business_areas: string[];
  job_role: string;
  ideal_candidate_traits: string[];
  candidate_fit_points: string[];
}

export interface EvaluationCriterionResponse {
  competency_id: string;
  label: string;
  category_id: string;
  category_label: string;
  question_tags: string[];
  high_signal: string;
  low_signal: string;
}

export interface GameBriefingResponse {
  scenario_title: string;
  candidate_profile: CandidateBriefingResponse;
  company_profile: CompanyBriefingResponse;
  evaluation_criteria: EvaluationCriterionResponse[];
}

export interface GameQuestionRequest {
  session_id: string;
  question: string;
}

export interface GameAnswerResponse extends AnswerResponse {
  session_id: string;
  status: string;
  remaining_seconds: number;
}

export interface GameEndRequest {
  session_id: string;
}

export interface GameEndResponse {
  session_id: string;
  status: string;
  ended_at: string;
  end_reason: string;
  remaining_seconds: number;
}

export interface ScoreSubmissionRequest {
  session_id: string;
  scores: Record<string, number>;
}

export interface ScoreSubmissionResponse {
  session_id: string;
  status: string;
  submitted_at: string;
}

export interface GameResultResponse {
  session_id: string;
  status: string;
  started_at: string;
  expires_at: string;
  ended_at?: string | null;
  end_reason?: string | null;
  candidate_name: string;
  company_name: string;
  scenario_title: string;
  answer_count: number;
  remaining_seconds: number;
  score_submitted: boolean;
  submitted_scores?: Record<string, number> | null;
  correct_scores?: Record<string, number> | null;
  score_diffs?: Record<string, number> | null;
  total_absolute_diff?: number | null;
  base_score?: number | null;
  display_score?: number | null;
  feedback_mode?: FeedbackMode | null;
  feedback_summary?: string | null;
  detected_competencies?: string[] | null;
  missed_competencies?: string[] | null;
  question_angle_gaps?: Record<string, string[]> | null;
  shallow_follow_up_flags?: string[] | null;
  category_balance?: Record<string, string> | null;
}

export const COMPETENCY_FIELDS = [
  { id: 'initiative', label: '主体性' },
  { id: 'influence', label: '働きかけ力' },
  { id: 'execution', label: '実行力' },
  { id: 'issue_finding', label: '課題発見力' },
  { id: 'planning', label: '計画力' },
  { id: 'creativity', label: '創造力' },
  { id: 'communication', label: '発信力' },
  { id: 'listening', label: '傾聴力' },
  { id: 'flexibility', label: '柔軟性' },
  { id: 'situational_awareness', label: '状況把握力' },
  { id: 'discipline', label: '規律性' },
  { id: 'stress_control', label: 'ストレスコントロール' },
] as const;

export type CompetencyId = (typeof COMPETENCY_FIELDS)[number]['id'];

export const COMPETENCY_LABELS: Record<CompetencyId, string> = Object.fromEntries(
  COMPETENCY_FIELDS.map((field) => [field.id, field.label])
) as Record<CompetencyId, string>;

export const DEFAULT_SCORE_SUBMISSION: Record<CompetencyId, number> = Object.fromEntries(
  COMPETENCY_FIELDS.map((field) => [field.id, 3])
) as Record<CompetencyId, number>;
