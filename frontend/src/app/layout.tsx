import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AI Job Seeker',
  description: 'RAG-based Q&A system for job seekers',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body className="font-body antialiased text-[color:var(--ink)]">
        {children}
      </body>
    </html>
  );
}
