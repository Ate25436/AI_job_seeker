'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { GAME_FLOW_TEST_IDS } from '@/lib/timer_flow_test_support';
import { DEFAULT_SCORE_SUBMISSION, type ChatMessage, type CompetencyId, type GameResultResponse, type GameSessionResponse } from '@/types/api';
import { api } from '@/lib/api';

type GamePhase = 'title' | 'setup' | 'interview' | 'scoring' | 'result';

type StoredGameState = {
  game: {
    phase: GamePhase;
    session: GameSessionResponse | null;
    messages: ChatMessage[];
    scores: Record<CompetencyId, number>;
    result: GameResultResponse | null;
  };
};

const STORAGE_KEY = 'ai-job-seeker-game';

export default function Home() {
  const router = useRouter();
  const [isBusy, setIsBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [noticeMessage, setNoticeMessage] = useState<string | null>(null);

  useEffect(() => {
    const note = sessionStorage.getItem('ai-job-seeker-home-note');
    if (!note) {
      return;
    }
    sessionStorage.removeItem('ai-job-seeker-home-note');
    setNoticeMessage(note);
  }, []);

  const startGame = async () => {
    setIsBusy(true);
    setErrorMessage(null);
    setNoticeMessage(null);

    try {
      const session = await api.startGameSession({ scenario_mode: 'fixed' });
      const snapshot: StoredGameState = {
        game: {
          phase: 'interview',
          session,
          messages: [],
          scores: DEFAULT_SCORE_SUBMISSION,
          result: null,
        },
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
      router.push('/interview');
    } catch {
      setErrorMessage('ゲーム開始に失敗しました。バックエンドの起動状態を確認してください。');
    } finally {
      setIsBusy(false);
    }
  };

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
          </div>

          <div className="grid gap-3 rounded-[1.5rem] bg-[color:var(--ink)] px-5 py-4 text-white">
            <p className="text-xs uppercase tracking-[0.28em] text-white/60">Current Page</p>
            <p className="font-display text-3xl">Home</p>
            <p className="text-sm text-white/80">
              面接前の準備ページです。まず資料を確認してから、ゲームを開始してください。
            </p>
          </div>
        </header>

        {errorMessage ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {errorMessage}
          </div>
        ) : null}

        {noticeMessage ? (
          <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">
            {noticeMessage}
          </div>
        ) : null}

        <section className="grid gap-5 lg:grid-cols-[1fr_1fr]">
          <article className="rounded-[2rem] border border-black/10 bg-white/75 p-6 shadow-[0_18px_50px_rgba(30,26,22,0.10)]">
            <p className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">Briefing</p>
            <h2 className="mt-3 font-display text-3xl">面接前ブリーフィング</h2>
            <div className="mt-4 space-y-3 text-sm leading-7 text-[color:var(--muted)]">
              <p>1. 学生のESで、学生時代の経験や志望理由を確認してください。</p>
              <p>2. 企業概要で、何を見たい会社なのかを確認してください。</p>
              <p>3. 評価基準一覧で、12項目の観察ポイントを確認してください。</p>
              <p>4. 「ゲームを開始」ボタンをクリックしてください。</p>
            </div>
          </article>

          <article className="rounded-[2rem] border border-black/10 bg-[color:var(--paper)] p-6 shadow-[0_18px_50px_rgba(30,26,22,0.10)]">
            <p className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">Game Start</p>
            <h2 className="mt-3 font-display text-3xl">ゲーム開始</h2>
            <button
              type="button"
              data-testid={GAME_FLOW_TEST_IDS.startButton}
              onClick={startGame}
              disabled={isBusy}
              className="mt-6 inline-flex rounded-full bg-[color:var(--accent)] px-6 py-3 text-sm font-semibold text-white transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isBusy ? '開始しています...' : 'ゲームを開始'}
            </button>
          </article>
        </section>

        <section className="grid gap-5 md:grid-cols-3">
          <Link
            href="/briefing/entry-sheet"
            className="rounded-[2rem] border border-black/10 bg-white/75 p-6 shadow-[0_18px_50px_rgba(30,26,22,0.10)] transition hover:-translate-y-1 hover:shadow-[0_24px_56px_rgba(30,26,22,0.14)]"
          >
            <p className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">Entry Sheet</p>
            <h2 className="mt-3 font-display text-3xl">学生のES</h2>
            <p className="mt-4 text-sm leading-7 text-[color:var(--muted)]">
              志望動機、学生時代に力を入れたこと、チームワークを発揮した経験が確認できます。
            </p>
          </Link>

          <Link
            href="/briefing/company"
            className="rounded-[2rem] border border-black/10 bg-white/75 p-6 shadow-[0_18px_50px_rgba(30,26,22,0.10)] transition hover:-translate-y-1 hover:shadow-[0_24px_56px_rgba(30,26,22,0.14)]"
          >
            <p className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">Company Overview</p>
            <h2 className="mt-3 font-display text-3xl">企業の概要</h2>
            <p className="mt-4 text-sm leading-7 text-[color:var(--muted)]">
              企業理念、事業領域、求める人物像、候補者との適合ポイントが確認できます。
            </p>
          </Link>

          <Link
            href="/briefing/evaluation"
            className="rounded-[2rem] border border-black/10 bg-white/75 p-6 shadow-[0_18px_50px_rgba(30,26,22,0.10)] transition hover:-translate-y-1 hover:shadow-[0_24px_56px_rgba(30,26,22,0.14)]"
          >
            <p className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">Evaluation Criteria</p>
            <h2 className="mt-3 font-display text-3xl">評価基準一覧</h2>
            <p className="mt-4 text-sm leading-7 text-[color:var(--muted)]">
              12項目の観察ポイントがカテゴリ別に確認できます。
            </p>
          </Link>
        </section>
      </div>
    </main>
  );
}
