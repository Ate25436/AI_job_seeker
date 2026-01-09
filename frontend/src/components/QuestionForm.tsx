import React from 'react';

type QuestionFormProps = {
  question: string;
  onQuestionChange: (value: string) => void;
  onSubmit: () => void;
  isLoading: boolean;
  errorMessage: string | null;
};

export default function QuestionForm({
  question,
  onQuestionChange,
  onSubmit,
  isLoading,
  errorMessage,
}: QuestionFormProps) {
  const isDisabled = isLoading || question.trim().length === 0;

  return (
    <form
      className="space-y-4"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div className="space-y-2">
        <label className="text-sm font-medium" htmlFor="question">
          質問内容
        </label>
        <textarea
          id="question"
          name="question"
          rows={5}
          maxLength={1000}
          className="w-full resize-none rounded-2xl border border-black/10 bg-white px-4 py-3 text-sm shadow-inner focus:border-[color:var(--accent)] focus:outline-none focus:ring-2 focus:ring-[color:var(--accent-soft)]"
          placeholder="例: 面接で自己PRを効果的に伝えるには？"
          value={question}
          onChange={(event) => onQuestionChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              onSubmit();
            }
          }}
          required
        />
        <div className="flex items-center justify-between text-xs text-[color:var(--muted)]">
          <span>Shift + Enter で改行、Enter で送信</span>
          <span>{question.length}/1000</span>
        </div>
      </div>

      {errorMessage ? (
        <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {errorMessage}
        </p>
      ) : null}

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={isDisabled}
          className="inline-flex items-center gap-2 rounded-full bg-[color:var(--accent)] px-6 py-3 text-sm font-semibold text-white transition hover:brightness-105 disabled:cursor-not-allowed disabled:bg-black/30"
        >
          {isLoading ? (
            <span className="flex items-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
              生成中...
            </span>
          ) : (
            '質問を送信'
          )}
        </button>
        {isLoading ? (
          <span className="text-xs text-[color:var(--teal)]">
            RAGが回答を生成しています
          </span>
        ) : null}
      </div>
    </form>
  );
}
