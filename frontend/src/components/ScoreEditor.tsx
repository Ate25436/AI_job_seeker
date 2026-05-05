'use client';

import { COMPETENCY_FIELDS, type CompetencyId } from '@/types/api';

type ScoreEditorProps = {
  title: string;
  description: string;
  scores: Record<CompetencyId, number>;
  onScoreChange: (competencyId: CompetencyId, value: number) => void;
  primaryActionLabel?: string;
  secondaryActionLabel?: string;
  onPrimaryAction?: () => void;
  onSecondaryAction?: () => void;
  primaryActionDisabled?: boolean;
};

export default function ScoreEditor({
  title,
  description,
  scores,
  onScoreChange,
  primaryActionLabel,
  secondaryActionLabel,
  onPrimaryAction,
  onSecondaryAction,
  primaryActionDisabled = false,
}: ScoreEditorProps) {
  return (
    <section className="rounded-[2rem] border border-black/10 bg-white/75 p-6 shadow-[0_18px_50px_rgba(30,26,22,0.10)]">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">Score Editor</p>
          <h2 className="mt-2 font-display text-3xl">{title}</h2>
        </div>
        <p className="max-w-xl text-sm leading-7 text-[color:var(--muted)]">{description}</p>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {COMPETENCY_FIELDS.map((field) => (
          <label
            key={field.id}
            className="rounded-[1.5rem] border border-black/10 bg-[color:var(--paper)] px-4 py-4 text-sm shadow-inner"
          >
            <span className="block font-medium text-[color:var(--ink)]">{field.label}</span>
            <span className="mt-1 block text-xs text-[color:var(--muted)]">{field.id}</span>
            <select
              value={scores[field.id]}
              onChange={(event) => onScoreChange(field.id, Number(event.target.value))}
              className="mt-3 w-full rounded-xl border border-black/10 bg-white px-3 py-2 text-sm"
            >
              {[1, 2, 3, 4, 5].map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
        ))}
      </div>

      {primaryActionLabel || secondaryActionLabel ? (
        <div className="mt-6 flex flex-wrap gap-3">
          {primaryActionLabel && onPrimaryAction ? (
            <button
              type="button"
              onClick={onPrimaryAction}
              disabled={primaryActionDisabled}
              className="rounded-full bg-[color:var(--accent)] px-6 py-3 text-sm font-semibold text-white transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {primaryActionLabel}
            </button>
          ) : null}
          {secondaryActionLabel && onSecondaryAction ? (
            <button
              type="button"
              onClick={onSecondaryAction}
              className="rounded-full border border-black/10 px-6 py-3 text-sm font-semibold text-[color:var(--muted)] transition hover:bg-white"
            >
              {secondaryActionLabel}
            </button>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
