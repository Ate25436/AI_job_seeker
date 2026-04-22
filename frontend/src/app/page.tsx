'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { GAME_FLOW_TEST_IDS } from '@/lib/timer_flow_test_support';
import { DEFAULT_SCORE_SUBMISSION, type ChatMessage, type CompetencyId, type GameResultResponse, type GameSessionResponse } from '@/types/api';

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
              AI就活生を見抜く
              <span className="text-[color:var(--accent)]">面接ゲーム</span>
            </h1>
            <p className="max-w-2xl text-sm leading-7 text-[color:var(--muted)] sm:text-base">
              ホーム画面でルールを確認し、ゲーム開始後は面接専用ページで10分の質問、採点、結果確認までを進めます。
            </p>
          </div>

          <div className="grid gap-3 rounded-[1.5rem] bg-[color:var(--ink)] px-5 py-4 text-white">
            <p className="text-xs uppercase tracking-[0.28em] text-white/60">Current Page</p>
            <p className="font-display text-3xl">Home</p>
            <p className="text-sm text-white/80">
              固定シナリオの就活生を読み込み、面接ページへ移動します。
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
              <p>1. ゲーム開始で `session_id` を発行し、候補者情報を取得します。</p>
              <p>2. 面接ページではタイマーと会話履歴を見ながら質問します。</p>
              <p>3. 面接終了後は 12 項目を採点します。</p>
              <p>4. 採点後に結果とフィードバックを確認します。</p>
            </div>
          </article>

          <article className="rounded-[2rem] border border-black/10 bg-[color:var(--paper)] p-6 shadow-[0_18px_50px_rgba(30,26,22,0.10)]">
            <p className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">Game Start</p>
            <h2 className="mt-3 font-display text-3xl">ゲーム開始</h2>
            <p className="mt-4 text-sm leading-7 text-[color:var(--muted)]">
              開始後は `/interview` に移動します。バックエンドを再起動して古いセッションが無効になった場合は、
              面接ページ側で自動的にホームへ戻します。
            </p>
            <button
              type="button"
              data-testid={GAME_FLOW_TEST_IDS.startButton}
              onClick={startGame}
              disabled={isBusy}
              className="mt-6 inline-flex rounded-full bg-[color:var(--accent)] px-6 py-3 text-sm font-semibold text-white transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isBusy ? '開始中...' : 'ゲームを開始する'}
            </button>
          </article>
        </section>
      </div>
    </main>
  );
}
