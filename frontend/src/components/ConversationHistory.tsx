import type { ChatMessage } from '@/types/api';

const formatter = new Intl.DateTimeFormat('ja-JP', {
  dateStyle: 'medium',
  timeStyle: 'short',
});

type ConversationHistoryPanelProps = {
  items: ChatMessage[];
  onClear: () => void;
};

export default function ConversationHistoryPanel({
  items,
  onClear,
}: ConversationHistoryPanelProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)]">
          Messages
        </h3>
        <button
          type="button"
          onClick={onClear}
          className="text-xs uppercase tracking-[0.25em] text-[color:var(--muted)] transition hover:text-[color:var(--accent)]"
        >
          Clear
        </button>
      </div>

      {items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-black/20 bg-[color:var(--paper)] px-4 py-6 text-center text-sm text-[color:var(--muted)]">
          まだ履歴がありません。最初の質問を送信してみましょう。
        </div>
      ) : (
        items.map((item) => {
          const isUser = item.role === 'user';
          return (
            <article key={item.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[85%] space-y-2 rounded-2xl border px-4 py-3 text-sm shadow-sm ${
                  isUser
                    ? 'border-[color:var(--accent)]/30 bg-[color:var(--accent)]/10 text-[color:var(--ink)]'
                    : 'border-black/10 bg-white text-[color:var(--ink)]'
                }`}
              >
                <div className="text-[0.65rem] uppercase tracking-[0.25em] text-[color:var(--muted)]">
                  {isUser ? 'You' : 'AI'} ・ {formatter.format(new Date(item.timestamp))}
                </div>
                <p className="whitespace-pre-wrap leading-relaxed">{item.content}</p>
              </div>
            </article>
          );
        })
      )}
    </div>
  );
}
