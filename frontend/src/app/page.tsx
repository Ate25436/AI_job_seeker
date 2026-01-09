'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { api } from '@/lib/api';
import type { ChatMessage } from '@/types/api';
import ConversationHistoryPanel from '@/components/ConversationHistory';
import QuestionForm from '@/components/QuestionForm';

const STORAGE_KEY = 'ai-job-seeker-chat';

const createId = () => {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `local-${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

export default function Home() {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const chatScrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      return;
    }

    try {
      const parsed = JSON.parse(stored) as ChatMessage[];
      if (Array.isArray(parsed)) {
        const hasLegacyPairs = parsed.some(
          (item) =>
            typeof (item as { question?: string }).question === 'string' &&
            typeof (item as { answer?: string }).answer === 'string'
        );

        if (hasLegacyPairs) {
          const legacy = parsed as unknown as {
            id: string;
            question: string;
            answer: string;
            timestamp: string;
          }[];

          const migrated: ChatMessage[] = legacy
            .slice()
            .sort((a, b) => a.timestamp.localeCompare(b.timestamp))
            .flatMap((item) => [
              {
                id: `${item.id}-q`,
                role: 'user',
                content: item.question,
                timestamp: item.timestamp,
              },
              {
                id: `${item.id}-a`,
                role: 'assistant',
                content: item.answer,
                timestamp: item.timestamp,
              },
            ]);
          setMessages(migrated);
        } else {
          setMessages(parsed);
        }
      }
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    if (!chatScrollRef.current) {
      return;
    }
    chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
  }, [messages]);

  const handleSubmit = async () => {
    if (isLoading) {
      return;
    }

    const trimmed = question.trim();
    if (!trimmed) {
      setErrorMessage('質問を入力してください。');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    const historyPayload = messages
      .slice(-6)
      .map((item) => ({
        role: item.role,
        content: item.content,
      }));

    const userMessage: ChatMessage = {
      id: createId(),
      role: 'user',
      content: trimmed,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setQuestion('');

    try {
      const response = await api.askQuestion(trimmed, historyPayload);
      const assistantMessage: ChatMessage = {
        id: createId(),
        role: 'assistant',
        content: response.answer,
        timestamp: response.timestamp,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch {
      setErrorMessage('回答の取得に失敗しました。時間をおいて再試行してください。');
      const assistantMessage: ChatMessage = {
        id: createId(),
        role: 'assistant',
        content: '回答の取得に失敗しました。時間をおいて再試行してください。',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearHistory = () => {
    setMessages([]);
  };

  const statusNote = useMemo(() => {
    if (isLoading) {
      return 'RAGが回答を生成しています';
    }
    if (messages.length > 0) {
      return 'AI就活生と会話を続けられます';
    }
    return '質問を送信して会話を始めてください';
  }, [isLoading, messages.length]);

  return (
    <main className="min-h-screen px-6 py-10 lg:px-12">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-8">
        <header className="flex flex-col gap-4">
          <span className="text-xs uppercase tracking-[0.35em] text-[color:var(--teal)]">
            AI Job Seeker
          </span>
          <h1 className="font-display text-4xl leading-tight sm:text-5xl">
            会話しながら、
            <span className="text-[color:var(--accent)]">就活の視点</span>
            を磨く。
          </h1>
          <p className="max-w-2xl text-base text-[color:var(--muted)]">
            Markdownの知識ベースを検索し、根拠のある回答を返すAI就活生です。
            連続した質問でも、文脈に沿って丁寧に回答します。
          </p>
        </header>

        <div className="rounded-3xl border border-black/10 bg-white/70 p-6 shadow-[0_28px_70px_rgba(30,26,22,0.16)] backdrop-blur">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-display text-2xl">チャット</h2>
              <p className="text-xs text-[color:var(--muted)]">{statusNote}</p>
            </div>
            {isLoading ? (
              <span className="inline-flex items-center gap-2 rounded-full bg-[color:var(--accent)]/10 px-3 py-1 text-xs text-[color:var(--accent)]">
                <span className="h-2 w-2 animate-pulse rounded-full bg-[color:var(--accent)]" />
                生成中
              </span>
            ) : null}
          </div>

          <div
            ref={chatScrollRef}
            className="mt-6 max-h-[55vh] space-y-4 overflow-y-auto pr-2"
          >
            <ConversationHistoryPanel items={messages} onClear={handleClearHistory} />
          </div>

          <div className="mt-6 rounded-2xl border border-black/10 bg-[color:var(--paper)] p-4">
            <QuestionForm
              question={question}
              onQuestionChange={setQuestion}
              onSubmit={handleSubmit}
              isLoading={isLoading}
              errorMessage={errorMessage}
            />
          </div>
        </div>
      </div>
    </main>
  );
}
