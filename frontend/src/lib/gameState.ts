import {
  DEFAULT_SCORE_SUBMISSION,
  type ChatMessage,
  type CompetencyId,
  type GameResultResponse,
  type GameSessionResponse,
} from '@/types/api';

export type GamePhase = 'title' | 'setup' | 'interview' | 'scoring' | 'result';

export type StoredGameState = {
  game: {
    phase: GamePhase;
    session: GameSessionResponse | null;
    messages: ChatMessage[];
    scores: Record<CompetencyId, number>;
    result: GameResultResponse | null;
  };
};

export const STORAGE_KEY = 'ai-job-seeker-game';

export const readStoredGameState = (): StoredGameState | null => {
  if (typeof window === 'undefined') {
    return null;
  }

  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as StoredGameState;
    if (!parsed?.game) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
};

export const readStoredScores = (): Record<CompetencyId, number> => {
  const stored = readStoredGameState();
  return {
    ...DEFAULT_SCORE_SUBMISSION,
    ...(stored?.game.scores ?? {}),
  };
};

export const updateStoredScores = (scores: Record<CompetencyId, number>) => {
  if (typeof window === 'undefined') {
    return;
  }

  const stored = readStoredGameState();
  if (!stored?.game) {
    return;
  }

  const nextState: StoredGameState = {
    game: {
      ...stored.game,
      scores: {
        ...DEFAULT_SCORE_SUBMISSION,
        ...scores,
      },
    },
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(nextState));
};
