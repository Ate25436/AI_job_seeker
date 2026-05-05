'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import ScoreEditor from '@/components/ScoreEditor';
import { api } from '@/lib/api';
import { readStoredScores, STORAGE_KEY, updateStoredScores } from '@/lib/gameState';
import { DEFAULT_SCORE_SUBMISSION, type CompetencyId, type EvaluationCriterionResponse, type GameBriefingResponse } from '@/types/api';

type BriefingSectionKind = 'entry-sheet' | 'company' | 'evaluation';

type BriefingSectionPageProps = {
  section: BriefingSectionKind;
};

const SECTION_META: Record<
  BriefingSectionKind,
  { eyebrow: string; title: string; description: string }
> = {
  'entry-sheet': {
    eyebrow: 'Entry Sheet',
    title: '学生のエントリーシート',
    description: '就活生の基本情報とエントリーシートの回答を確認してください。',
  },
  company: {
    eyebrow: 'Company Overview',
    title: '企業の概要',
    description: '企業理解に必要な理念、事業、求める人物像、適合ポイントを確認してください。',
  },
  evaluation: {
    eyebrow: 'Evaluation Criteria',
    title: '評価基準一覧',
    description: '12項目の観察ポイントをカテゴリ別に確認してください。',
  },
};

const SECTION_LINKS: Array<{ href: string; label: string; section: BriefingSectionKind }> = [
  { href: '/briefing/entry-sheet', label: 'ES', section: 'entry-sheet' },
  { href: '/briefing/company', label: '企業概要', section: 'company' },
  { href: '/briefing/evaluation', label: '評価基準', section: 'evaluation' },
];

export default function BriefingSectionPage({ section }: BriefingSectionPageProps) {
  const router = useRouter();
  const [briefing, setBriefing] = useState<GameBriefingResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [fromInterview, setFromInterview] = useState(false);
  const [memoScores, setMemoScores] = useState<Record<CompetencyId, number>>(DEFAULT_SCORE_SUBMISSION);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const params = new URLSearchParams(window.location.search);
    setFromInterview(params.get('from') === 'interview');
    setMemoScores(readStoredScores());
  }, []);

  useEffect(() => {
    if (!(fromInterview && section === 'evaluation')) {
      return;
    }
    updateStoredScores(memoScores);
  }, [fromInterview, memoScores, section]);

  useEffect(() => {
    if (!(fromInterview && section === 'evaluation') || typeof window === 'undefined') {
      return;
    }

    const handleStorage = (event: StorageEvent) => {
      if (event.key !== STORAGE_KEY) {
        return;
      }
      setMemoScores(readStoredScores());
    };

    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, [fromInterview, section]);

  useEffect(() => {
    let ignore = false;

    const loadBriefing = async () => {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const response = await api.getGameBriefing();
        if (!ignore) {
          setBriefing(response);
        }
      } catch {
        if (!ignore) {
          setErrorMessage('開始前資料の取得に失敗しました。バックエンドの起動状態を確認してください。');
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    };

    void loadBriefing();

    return () => {
      ignore = true;
    };
  }, []);

  const criteriaByCategory = useMemo(() => {
    return (briefing?.evaluation_criteria ?? []).reduce<Record<string, EvaluationCriterionResponse[]>>(
      (groups, criterion) => {
        if (!groups[criterion.category_label]) {
          groups[criterion.category_label] = [];
        }
        groups[criterion.category_label].push(criterion);
        return groups;
      },
      {}
    );
  }, [briefing]);

  const meta = SECTION_META[section];
  const handleMemoScoreChange = (competencyId: CompetencyId, value: number) => {
    setMemoScores((previous) => ({
      ...previous,
      [competencyId]: value,
    }));
  };
  const handleReturnToInterview = () => {
    window.close();
    window.setTimeout(() => {
      router.push('/interview');
    }, 150);
  };

  return (
    <main className="min-h-screen px-4 py-8 sm:px-6 lg:px-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <header className="grid gap-4 rounded-[2rem] border border-black/10 bg-white/70 p-6 shadow-[0_24px_60px_rgba(30,26,22,0.12)] backdrop-blur lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-4">
            <span className="text-xs uppercase tracking-[0.35em] text-[color:var(--teal)]">
              {meta.eyebrow}
            </span>
            <h1 className="font-display text-4xl leading-tight sm:text-5xl">{meta.title}</h1>
            <p className="max-w-2xl text-sm leading-7 text-[color:var(--muted)] sm:text-base">
              {meta.description}
            </p>
          </div>

          <div className="grid gap-3 rounded-[1.5rem] bg-[color:var(--ink)] px-5 py-4 text-white">
            <p className="text-xs uppercase tracking-[0.28em] text-white/60">Briefing Navigation</p>
            <div className="flex flex-wrap gap-2">
              {SECTION_LINKS.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`rounded-full px-4 py-2 text-sm transition ${
                    item.section === section
                      ? 'bg-white text-[color:var(--ink)]'
                      : 'border border-white/20 text-white/80 hover:bg-white/10'
                  }`}
                >
                  {item.label}
                </Link>
              ))}
            </div>
            <div className="flex flex-wrap gap-2 pt-2">
              <Link
                href="/"
                className="rounded-full border border-white/20 px-4 py-2 text-sm text-white/80 transition hover:bg-white/10"
              >
                ホームへ戻る
              </Link>
              {fromInterview ? (
                <button
                  type="button"
                  onClick={handleReturnToInterview}
                  className="rounded-full border border-white/20 px-4 py-2 text-sm text-white/80 transition hover:bg-white/10"
                >
                  面接画面に戻る
                </button>
              ) : (
                <Link
                  href="/interview"
                  className="rounded-full border border-white/20 px-4 py-2 text-sm text-white/80 transition hover:bg-white/10"
                >
                  面接画面へ進む
                </Link>
              )}
            </div>
            {briefing?.scenario_title ? (
              <p className="text-sm text-white/70">{briefing.scenario_title}</p>
            ) : null}
          </div>
        </header>

        {errorMessage ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {errorMessage}
          </div>
        ) : null}

        {isLoading ? (
          <section className="rounded-[2rem] border border-black/10 bg-white/75 p-6 shadow-[0_18px_50px_rgba(30,26,22,0.10)]">
            <p className="text-sm text-[color:var(--muted)]">資料を読み込んでいます。しばらくお待ちください。</p>
          </section>
        ) : null}

        {!isLoading && briefing && section === 'entry-sheet' ? (
          <section className="rounded-[2rem] border border-black/10 bg-white/75 p-6 shadow-[0_18px_50px_rgba(30,26,22,0.10)]">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-[1.5rem] bg-[color:var(--paper)] px-4 py-4">
                <p className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)]">氏名</p>
                <p className="mt-2 font-display text-2xl">{briefing.candidate_profile.full_name}</p>
              </div>
              <div className="rounded-[1.5rem] bg-[color:var(--paper)] px-4 py-4">
                <p className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)]">大学</p>
                <p className="mt-2 text-sm text-[color:var(--ink)]">
                  {briefing.candidate_profile.university} / {briefing.candidate_profile.faculty_type}
                </p>
              </div>
              <div className="rounded-[1.5rem] bg-[color:var(--paper)] px-4 py-4">
                <p className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)]">学年</p>
                <p className="mt-2 text-sm text-[color:var(--ink)]">
                  {briefing.candidate_profile.grade}年 / {briefing.candidate_profile.age}歳
                </p>
              </div>
              <div className="rounded-[1.5rem] bg-[color:var(--paper)] px-4 py-4">
                <p className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)]">志望</p>
                <p className="mt-2 text-sm text-[color:var(--ink)]">
                  {briefing.candidate_profile.desired_industry}
                  <br />
                  {briefing.candidate_profile.desired_job_family}
                </p>
              </div>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              {briefing.candidate_profile.entry_sheet_sections.map((entry) => (
                <div
                  key={entry.title}
                  className="rounded-[1.5rem] border border-black/10 bg-white px-4 py-4"
                >
                  <p className="text-sm font-semibold text-[color:var(--ink)]">{entry.title}</p>
                  <p className="mt-2 text-sm leading-7 text-[color:var(--muted)]">{entry.summary}</p>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {!isLoading && briefing && section === 'company' ? (
          <section className="rounded-[2rem] border border-black/10 bg-white/75 p-6 shadow-[0_18px_50px_rgba(30,26,22,0.10)]">
            <div className="rounded-[1.5rem] bg-[color:var(--ink)] px-5 py-4 text-white">
              <p className="text-xs uppercase tracking-[0.2em] text-white/60">Company</p>
              <p className="mt-2 font-display text-2xl">{briefing.company_profile.company_name}</p>
              <p className="mt-2 text-sm text-white/80">
                {briefing.company_profile.industry} / {briefing.company_profile.job_role}
              </p>
            </div>

            <div className="mt-6 rounded-[1.5rem] border border-black/10 bg-white px-4 py-4">
              <p className="text-sm font-semibold text-[color:var(--ink)]">企業理念</p>
              <p className="mt-2 text-sm leading-7 text-[color:var(--muted)]">
                {briefing.company_profile.philosophy}
              </p>
            </div>

            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <div className="rounded-[1.5rem] border border-black/10 bg-white px-4 py-4">
                <p className="text-sm font-semibold text-[color:var(--ink)]">事業領域</p>
                <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-[color:var(--muted)]">
                  {briefing.company_profile.business_areas.map((area) => (
                    <li key={area}>{area}</li>
                  ))}
                </ul>
              </div>
              <div className="rounded-[1.5rem] border border-black/10 bg-white px-4 py-4">
                <p className="text-sm font-semibold text-[color:var(--ink)]">求める人物像</p>
                <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-[color:var(--muted)]">
                  {briefing.company_profile.ideal_candidate_traits.map((trait) => (
                    <li key={trait}>{trait}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="mt-6 rounded-[1.5rem] border border-black/10 bg-white px-4 py-4">
              <p className="text-sm font-semibold text-[color:var(--ink)]">候補者との適合ポイント</p>
              <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-[color:var(--muted)]">
                {briefing.company_profile.candidate_fit_points.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
            </div>
          </section>
        ) : null}

        {!isLoading && briefing && section === 'evaluation' ? (
          <section className="grid gap-5">
            {fromInterview ? (
              <ScoreEditor
                title="採点メモ"
                description="面接中の仮評価を 1 から 5 で入力してください。ここで入力した内容は、面接終了後の採点画面にも同期してください。"
                scores={memoScores}
                onScoreChange={handleMemoScoreChange}
                primaryActionLabel="面接画面に戻ってください"
                onPrimaryAction={handleReturnToInterview}
              />
            ) : null}
            {Object.entries(criteriaByCategory).map(([categoryLabel, criteria]) => (
              <article
                key={categoryLabel}
                className="rounded-[2rem] border border-black/10 bg-white/75 p-6 shadow-[0_18px_50px_rgba(30,26,22,0.10)]"
              >
                <p className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">
                  {categoryLabel}
                </p>
                <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {criteria.map((criterion) => (
                    <div
                      key={criterion.competency_id}
                      className="rounded-[1.5rem] border border-black/10 bg-white px-4 py-4"
                    >
                      <p className="font-semibold text-[color:var(--ink)]">{criterion.label}</p>
                      <p className="mt-1 text-xs text-[color:var(--muted)]">{criterion.competency_id}</p>
                      <div className="mt-4 space-y-3 text-sm text-[color:var(--muted)]">
                        <div>
                          <p className="font-medium text-[color:var(--ink)]">
                            {criterion.label}が高い人の特徴
                          </p>
                          <p className="mt-1 leading-6">{criterion.high_signal}</p>
                        </div>
                        <div>
                          <p className="font-medium text-[color:var(--ink)]">
                            {criterion.label}が低い人の特徴
                          </p>
                          <p className="mt-1 leading-6">{criterion.low_signal}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </section>
        ) : null}
      </div>
    </main>
  );
}
