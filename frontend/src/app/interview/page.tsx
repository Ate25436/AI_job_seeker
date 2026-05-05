'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import ConversationHistory from '@/components/ConversationHistory';
import QuestionForm from '@/components/QuestionForm';
import ScoreEditor from '@/components/ScoreEditor';
import { api, isApiNotFoundError } from '@/lib/api';
import { readStoredGameState, readStoredScores, STORAGE_KEY, type GamePhase, type StoredGameState } from '@/lib/gameState';
import { GAME_FLOW_TEST_IDS } from '@/lib/timer_flow_test_support';
import {
  COMPETENCY_LABELS,
  DEFAULT_SCORE_SUBMISSION,
  type ChatMessage,
  type CompetencyId,
  type GameResultResponse,
  type GameSessionResponse,
} from '@/types/api';

const createId = () => {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `local-${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

const formatRemainingSeconds = (remaining_seconds: number) => {
  const safeSeconds = Math.max(0, remaining_seconds);
  const minutes = Math.floor(safeSeconds / 60);
  const seconds = safeSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, '0')}`;
};

const formatScore = (score?: number | null) => {
  if (typeof score !== 'number') {
    return '--';
  }
  return score.toFixed(1);
};

export default function Home() {
  const router = useRouter();
  const [phase, setPhase] = useState<GamePhase>('title');
  const [session, setSession] = useState<GameSessionResponse | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [scores, setScores] = useState<Record<CompetencyId, number>>(DEFAULT_SCORE_SUBMISSION);
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState<GameResultResponse | null>(null);
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const [isBusy, setIsBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [restoreNote, setRestoreNote] = useState<string | null>(null);
  const [hasLoadedStoredState, setHasLoadedStoredState] = useState(false);
  const chatScrollRef = useRef<HTMLDivElement | null>(null);
  const autoEndingRef = useRef(false);

  const openBriefingPage = (path: string) => {
    window.open(`${path}?from=interview`, '_blank');
  };

  const resetGameState = useCallback((note: string | null = null) => {
    setPhase('title');
    setSession(null);
    setMessages([]);
    setScores(DEFAULT_SCORE_SUBMISSION);
    setQuestion('');
    setResult(null);
    setRemainingSeconds(0);
    setErrorMessage(null);
    setRestoreNote(note);
    autoEndingRef.current = false;
    if (typeof window !== 'undefined') {
      localStorage.removeItem(STORAGE_KEY);
      if (note) {
        sessionStorage.setItem('ai-job-seeker-home-note', note);
      }
    }
    router.push('/');
  }, [router]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const parsed = readStoredGameState();
    if (!parsed) {
      resetGameState('面接セッションがないため、ホーム画面に戻しました。');
      return;
    }

    try {
      setPhase(parsed.game.phase ?? 'title');
      setSession(parsed.game.session ?? null);
      setMessages(Array.isArray(parsed.game.messages) ? parsed.game.messages : []);
      setScores({ ...DEFAULT_SCORE_SUBMISSION, ...(parsed.game.scores ?? {}) });
      setResult(parsed.game.result ?? null);
      setRestoreNote('前回の面接セッション状態を復元しました。');
      setHasLoadedStoredState(true);

      const restoredSessionId = parsed.game.session?.session_id;
      if (restoredSessionId) {
        void api.getGameResult(restoredSessionId).catch((error) => {
          if (isApiNotFoundError(error)) {
            resetGameState('前回の面接セッションは無効になったため、タイトル画面に戻しました。');
            return;
          }
          setErrorMessage('前回セッションの確認に失敗しました。バックエンドの起動状態を確認してください。');
        });
      }
    } catch {
      localStorage.removeItem(STORAGE_KEY);
      resetGameState('面接セッションの復元に失敗したため、ホーム画面に戻しました。');
    }
  }, [resetGameState]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    if (!hasLoadedStoredState) {
      return;
    }

    const hasActiveState =
      phase !== 'title' || session !== null || messages.length > 0 || result !== null;

    if (!hasActiveState) {
      localStorage.removeItem(STORAGE_KEY);
      return;
    }

    const snapshot: StoredGameState = {
      game: {
        phase,
        session,
        messages,
        scores,
        result,
      },
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
  }, [hasLoadedStoredState, messages, phase, result, scores, session]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const handleStorage = (event: StorageEvent) => {
      if (event.key !== STORAGE_KEY) {
        return;
      }

      setScores((previous) => {
        const nextScores = readStoredScores();
        const previousJson = JSON.stringify(previous);
        const nextJson = JSON.stringify(nextScores);
        return previousJson === nextJson ? previous : nextScores;
      });
    };

    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  useEffect(() => {
    if (!chatScrollRef.current) {
      return;
    }
    chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
  }, [messages]);

  useEffect(() => {
    if (!session || phase !== 'interview') {
      if (phase !== 'interview') {
        setRemainingSeconds(0);
      }
      return;
    }

    const updateRemaining = () => {
      const expiresAt = new Date(session.expires_at).getTime();
      const nextSeconds = Math.max(0, Math.floor((expiresAt - Date.now()) / 1000));
      setRemainingSeconds(nextSeconds);
      if (nextSeconds === 0 && !autoEndingRef.current) {
        autoEndingRef.current = true;
        void handleEndInterview('timeout');
      }
    };

    updateRemaining();
    const timer = window.setInterval(updateRemaining, 1000);
    return () => window.clearInterval(timer);
  }, [phase, session]);

  const handleAskQuestion = async () => {
    if (!session || isBusy) {
      return;
    }

    const trimmed = question.trim();
    if (!trimmed) {
      setErrorMessage('質問を入力してください。');
      return;
    }

    const userMessage: ChatMessage = {
      id: createId(),
      role: 'user',
      content: trimmed,
      timestamp: new Date().toISOString(),
    };

    setIsBusy(true);
    setErrorMessage(null);
    setMessages((previous) => [...previous, userMessage]);
    setQuestion('');

    try {
      const response = await api.askGameQuestion({
        session_id: session.session_id,
        question: trimmed,
      });
      setMessages((previous) => [
        ...previous,
        {
          id: createId(),
          role: 'assistant',
          content: response.answer,
          timestamp: response.timestamp,
        },
      ]);
      setRemainingSeconds(response.remaining_seconds);
    } catch (error) {
      if (isApiNotFoundError(error)) {
        resetGameState('面接セッションが見つからないため、タイトル画面に戻しました。');
        return;
      }
      setErrorMessage('回答取得に失敗しました。面接セッションを確認して再試行してください。');
    } finally {
      setIsBusy(false);
    }
  };

  const handleEndInterview = async (reason: 'manual' | 'timeout' = 'manual') => {
    if (!session) {
      return;
    }

    setIsBusy(true);
    setErrorMessage(null);

    try {
      await api.endGameSession({ session_id: session.session_id });
      setPhase('scoring');
      setRemainingSeconds(0);
      if (reason === 'timeout') {
        setRestoreNote('10分経過のため面接を終了し、採点画面へ移動しました。');
      }
    } catch (error) {
      if (isApiNotFoundError(error)) {
        resetGameState('面接セッションが見つからないため、タイトル画面に戻りました。');
        return;
      }
      setErrorMessage('面接終了に失敗しました。結果取得前に再試行してください。');
    } finally {
      setIsBusy(false);
    }
  };

  const handleScoreChange = (competencyId: CompetencyId, value: number) => {
    setScores((previous) => ({
      ...previous,
      [competencyId]: value,
    }));
  };

  const handleSubmitScores = async () => {
    if (!session) {
      return;
    }

    setIsBusy(true);
    setErrorMessage(null);

    try {
      await api.submitGameScore({
        session_id: session.session_id,
        scores,
      });
      const nextResult = await api.getGameResult(session.session_id);
      setResult(nextResult);
      setPhase('result');
    } catch (error) {
      if (isApiNotFoundError(error)) {
        resetGameState('面接セッションが見つからないため、タイトル画面に戻りました。');
        return;
      }
      setErrorMessage('採点結果の送信に失敗しました。入力内容を確認してください。');
    } finally {
      setIsBusy(false);
    }
  };

  const handleReset = () => {
    resetGameState();
  };

  const interviewStatus = useMemo(() => {
    if (!session) {
      return '面接セッションを開始してください。';
    }
    if (phase === 'interview') {
      return `${session.company_name} の面接中です。会話ログを確認しながら深掘りしてください。`;
    }
    if (phase === 'scoring') {
      return '面接は終了しました。12項目を1から5で採点してください。';
    }
    if (phase === 'result') {
      return '結果とフィードバックを確認し、次の質問設計に活かしてください。';
    }
    return '就活生の見極めゲームを開始してください。';
  }, [phase, session]);

  const scoreSummary = useMemo(() => {
    if (!result) {
      return null;
    }

    return [
      { label: '表示成績', value: formatScore(result.display_score) },
      { label: '基本成績', value: formatScore(result.base_score) },
      { label: '絶対差分合計', value: `${result.total_absolute_diff ?? '--'}` },
      { label: '回答数', value: `${result.answer_count}` },
    ];
  }, [result]);

  return (
    <main className="min-h-screen px-4 py-8 sm:px-6 lg:px-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <header className="grid gap-4 rounded-[2rem] border border-black/10 bg-white/70 p-6 shadow-[0_24px_60px_rgba(30,26,22,0.12)] backdrop-blur lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-4">
            <span className="text-xs uppercase tracking-[0.35em] text-[color:var(--teal)]">
              Interview Game
            </span>
            <h1 className="font-display text-4xl leading-tight sm:text-5xl">
              <span className="text-[color:var(--accent)]">AI就活生</span>
            </h1>
            <p className="max-w-2xl text-sm leading-7 text-[color:var(--muted)] sm:text-base">
              10分間面接を行って，就活生を12項目で採点してください。
            </p>
            <p className="max-w-2xl text-sm leading-7 text-[color:var(--muted)] sm:text-base">
              採点を送信した後，フィードバックを確認できます
            </p>
          </div>

          <div className="grid gap-3 rounded-[1.5rem] bg-[color:var(--ink)] px-5 py-4 text-white">
            <p className="text-xs uppercase tracking-[0.28em] text-white/60">Interview Phase</p>
            <p className="font-display text-3xl capitalize">{phase}</p>
            <p className="text-sm text-white/80">{interviewStatus}</p>
            {restoreNote ? (
              <p className="rounded-2xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-white/80">
                {restoreNote}
              </p>
            ) : null}
          </div>
        </header>

        {errorMessage ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {errorMessage}
          </div>
        ) : null}

        {phase === 'title' || phase === 'setup' ? (
          <section className="rounded-[2rem] border border-black/10 bg-white/75 p-6 shadow-[0_18px_50px_rgba(30,26,22,0.10)]">
            <p className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">No Active Session</p>
            <h2 className="mt-3 font-display text-3xl">面接セッションがありません</h2>
            <p className="mt-4 text-sm leading-7 text-[color:var(--muted)]">
              ホーム画面からゲームを開始してください。古いセッション情報が残っている場合は、自動的に破棄されます。
            </p>
            <button
              type="button"
              onClick={() => resetGameState('ホーム画面から新しい面接を開始してください。')}
              className="mt-6 inline-flex rounded-full bg-[color:var(--accent)] px-6 py-3 text-sm font-semibold text-white transition hover:brightness-105"
            >
              ホームへ戻る
            </button>
          </section>
        ) : null}

        {phase === 'interview' && session ? (
          <section className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
            <aside className="space-y-5 rounded-[2rem] border border-black/10 bg-white/75 p-6 shadow-[0_18px_50px_rgba(30,26,22,0.10)]">
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">Interview</p>
                <h2 className="font-display text-3xl">{session.candidate_name}</h2>
                <p className="text-sm text-[color:var(--muted)]">{session.scenario_title}</p>
              </div>

              <div
                data-testid={GAME_FLOW_TEST_IDS.timer}
                className="rounded-[1.5rem] bg-[color:var(--ink)] p-5 text-white"
              >
                <p className="text-xs uppercase tracking-[0.28em] text-white/60">Timer</p>
                <p className="mt-3 font-display text-5xl">{formatRemainingSeconds(remainingSeconds)}</p>
                <p className="mt-2 text-sm text-white/75">
                  10分経過までに面接を進めてください。時間切れになると、自動的に採点画面へ移動します。
                </p>
              </div>

              <dl className="grid gap-3 text-sm text-[color:var(--muted)]">
                <div>
                  <dt className="text-xs uppercase tracking-[0.2em]">Company</dt>
                  <dd className="text-base text-[color:var(--ink)]">{session.company_name}</dd>
                </div>
              </dl>

              <div className="rounded-[1.5rem] border border-black/10 bg-[color:var(--paper)] px-4 py-4">
                <p className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)]">
                  Briefing Pages
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => openBriefingPage('/briefing/entry-sheet')}
                    className="rounded-full border border-black/10 bg-white px-3 py-2 text-xs text-[color:var(--ink)] transition hover:bg-[color:var(--accent)]/10"
                  >
                    学生のES
                  </button>
                  <button
                    type="button"
                    onClick={() => openBriefingPage('/briefing/company')}
                    className="rounded-full border border-black/10 bg-white px-3 py-2 text-xs text-[color:var(--ink)] transition hover:bg-[color:var(--accent)]/10"
                  >
                    企業の概要
                  </button>
                  <button
                    type="button"
                    onClick={() => openBriefingPage('/briefing/evaluation')}
                    className="rounded-full border border-black/10 bg-white px-3 py-2 text-xs text-[color:var(--ink)] transition hover:bg-[color:var(--accent)]/10"
                  >
                    評価基準
                  </button>
                </div>
              </div>

              <button
                type="button"
                data-testid={GAME_FLOW_TEST_IDS.endButton}
                onClick={() => void handleEndInterview('manual')}
                disabled={isBusy}
                className="w-full rounded-full border border-[color:var(--accent)] px-5 py-3 text-sm font-semibold text-[color:var(--accent)] transition hover:bg-[color:var(--accent)]/10 disabled:cursor-not-allowed disabled:opacity-60"
              >
                面接を終了して採点へ進む
              </button>
              <button
                type="button"
                onClick={handleReset}
                disabled={isBusy}
                className="w-full rounded-full border border-black/10 px-5 py-3 text-sm font-semibold text-[color:var(--muted)] transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
              >
                セッションを破棄してホームへ戻る
              </button>
            </aside>

            <div className="rounded-[2rem] border border-black/10 bg-white/75 p-6 shadow-[0_18px_50px_rgba(30,26,22,0.10)]">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">
                    ConversationHistory
                  </p>
                  <h2 className="mt-2 font-display text-3xl">面接画面</h2>
                </div>
                <div className="rounded-full bg-[color:var(--accent)]/10 px-4 py-2 text-xs text-[color:var(--accent)]">
                  質問数: {Math.ceil(messages.length / 2)}
                </div>
              </div>

              <div
                ref={chatScrollRef}
                className="mt-6 max-h-[50vh] space-y-4 overflow-y-auto pr-1"
              >
                <ConversationHistory items={messages} onClear={() => setMessages([])} />
              </div>

              <div className="mt-6 rounded-[1.5rem] border border-black/10 bg-[color:var(--paper)] p-4">
                <QuestionForm
                  question={question}
                  onQuestionChange={setQuestion}
                  onSubmit={() => void handleAskQuestion()}
                  isLoading={isBusy}
                  errorMessage={errorMessage}
                />
              </div>
            </div>
          </section>
        ) : null}

        {phase === 'scoring' && session ? (
          <div data-testid={GAME_FLOW_TEST_IDS.scoreForm}>
            <ScoreEditor
              title="12項目の採点入力"
              description="面接中に付けたメモと同期された数値を確認し、各項目を 1 から 5 で採点してください。採点送信後に submitted_scores と結果フィードバックを表示します。"
              scores={scores}
              onScoreChange={handleScoreChange}
              primaryActionLabel={isBusy ? '採点を送信しています...' : '採点を送信する'}
              secondaryActionLabel="セッションを破棄"
              onPrimaryAction={() => void handleSubmitScores()}
              onSecondaryAction={handleReset}
              primaryActionDisabled={isBusy}
            />
          </div>
        ) : null}

        {phase === 'result' && result ? (
          <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
            <article
              data-testid={GAME_FLOW_TEST_IDS.resultPanel}
              className="rounded-[2rem] border border-black/10 bg-white/75 p-6 shadow-[0_18px_50px_rgba(30,26,22,0.10)]"
            >
              <p className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">Result</p>
              <h2 className="mt-2 font-display text-3xl">結果表示画面</h2>

              <div className="mt-6 grid gap-4 sm:grid-cols-2">
                {scoreSummary?.map((item) => (
                  <div key={item.label} className="rounded-[1.5rem] bg-[color:var(--paper)] px-4 py-4">
                    <p className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)]">{item.label}</p>
                    <p className="mt-2 font-display text-4xl">{item.value}</p>
                  </div>
                ))}
              </div>

              <div className="mt-6 space-y-3 text-sm leading-7 text-[color:var(--muted)]">
                <p>候補者: {result.candidate_name}</p>
                <p>会社: {result.company_name}</p>
                <p>フィードバックモード: {result.feedback_mode ?? 'rule_based'}</p>
                <p>面接終了理由: {result.end_reason ?? 'manual'}</p>
              </div>

              <div className="mt-6 rounded-[1.5rem] border border-black/10 bg-[color:var(--ink)] px-5 py-4 text-white">
                <p className="text-xs uppercase tracking-[0.25em] text-white/60">Feedback Summary</p>
                <p className="mt-3 text-sm leading-7 text-white/85">{result.feedback_summary}</p>
              </div>

              <button
                type="button"
                onClick={handleReset}
                className="mt-6 rounded-full bg-[color:var(--accent)] px-6 py-3 text-sm font-semibold text-white transition hover:brightness-105"
              >
                新しい面接を始める
              </button>
            </article>

            <article
              data-testid={GAME_FLOW_TEST_IDS.feedbackPanel}
              className="rounded-[2rem] border border-black/10 bg-white/75 p-6 shadow-[0_18px_50px_rgba(30,26,22,0.10)]"
            >
              <p className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">Feedback</p>
              <h2 className="mt-2 font-display text-3xl">フィードバック表示画面</h2>

              <div className="mt-6 grid gap-5">
                <div className="rounded-[1.5rem] bg-[color:var(--paper)] px-4 py-4">
                  <h3 className="text-sm font-semibold">見抜けた評価項目</h3>
                  <p className="mt-2 text-sm text-[color:var(--muted)]">
                    {(result.detected_competencies ?? []).map((item) => COMPETENCY_LABELS[item as CompetencyId]).join('、') || '該当なし'}
                  </p>
                </div>

                <div className="rounded-[1.5rem] bg-[color:var(--paper)] px-4 py-4">
                  <h3 className="text-sm font-semibold">見抜けなかった評価項目</h3>
                  <p className="mt-2 text-sm text-[color:var(--muted)]">
                    {(result.missed_competencies ?? []).map((item) => COMPETENCY_LABELS[item as CompetencyId]).join('、') || '該当なし'}
                  </p>
                </div>

                <div className="rounded-[1.5rem] bg-[color:var(--paper)] px-4 py-4">
                  <h3 className="text-sm font-semibold">不足していた質問観点</h3>
                  <div className="mt-3 space-y-4 text-sm text-[color:var(--muted)]">
                    {Object.entries(result.question_angle_gaps ?? {}).map(([competencyId, gaps]) => (
                      <div key={competencyId}>
                        <p className="font-medium text-[color:var(--ink)]">
                          {COMPETENCY_LABELS[competencyId as CompetencyId] ?? competencyId}
                        </p>
                        <ul className="mt-2 list-disc space-y-1 pl-5">
                          {gaps.map((gap) => (
                            <li key={gap}>{gap}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-[1.5rem] bg-[color:var(--paper)] px-4 py-4">
                  <h3 className="text-sm font-semibold">深掘り不足の指摘</h3>
                  <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-[color:var(--muted)]">
                    {(result.shallow_follow_up_flags ?? []).map((flag) => (
                      <li key={flag}>{flag}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </article>
          </section>
        ) : null}
      </div>
    </main>
  );
}
