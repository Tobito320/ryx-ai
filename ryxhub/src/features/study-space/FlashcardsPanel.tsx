import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import type { Flashcard } from '../../types/study-space';

interface Props {
  spaceId: string | null;
}

export default function FlashcardsPanel({ spaceId }: Props) {
  const [cards, setCards] = useState<Flashcard[]>([]);
  const [idx, setIdx] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!spaceId) return;
    (async () => {
      try {
        setLoading(true);
        const data = await api.get<Flashcard[]>(`/study-spaces/${spaceId}/flashcards`);
        setCards(data);
        setIdx(0);
        setFlipped(false);
      } catch {
        setCards([]);
      } finally {
        setLoading(false);
      }
    })();
  }, [spaceId]);

  if (!spaceId) return <div className="p-3 text-sm text-muted-foreground">Select a space.</div>;
  if (loading) return <div className="p-3 text-sm text-muted-foreground">Loading flashcards…</div>;
  if (!cards.length) return <div className="p-3 text-sm text-muted-foreground">No flashcards yet. Create definition snippets to auto-generate cards.</div>;

  const current = cards[idx];

  async function review(result: 'easy' | 'medium' | 'hard') {
    try {
      const updated = await api.post(`/study-spaces/${spaceId}/flashcards/${current.id}/review`, { result });
      setCards(prev => prev.map(c => c.id === current.id ? { ...c, ...updated } : c));
      setIdx(i => Math.min(prevNext(i, cards.length), cards.length - 1));
      setFlipped(false);
    } catch {
      // ignore errors for now
    }
  }

  function prevNext(i: number, length: number) {
    return Math.min(i + 1, length - 1);
  }

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <div className="font-semibold text-sm">Flashcards</div>
        <div className="text-xs text-muted-foreground">{idx + 1} / {cards.length}</div>
      </div>
      <div className="flex-1 flex flex-col p-4 gap-4">
        <div
          className="flex-1 border border-border rounded-lg p-6 flex items-center justify-center text-center cursor-pointer select-none bg-card shadow-sm hover:shadow-md transition-shadow"
          onClick={() => setFlipped(f => !f)}
        >
          <div className="max-w-lg whitespace-pre-wrap text-base text-foreground">
            {flipped ? current.back : current.front}
          </div>
        </div>
        <div className="flex items-center justify-between gap-2">
          <button className="px-3 py-1.5 border border-border rounded-md text-sm font-medium hover:bg-accent/20 transition-colors disabled:opacity-50" onClick={() => setIdx(i => Math.max(i - 1, 0))} disabled={idx === 0}>Previous</button>
          <div className="flex gap-1.5">
            <button className="px-2.5 py-1.5 rounded-md bg-green-600 text-white text-xs font-medium hover:opacity-90 transition-opacity" onClick={() => review('easy')}>Easy</button>
            <button className="px-2.5 py-1.5 rounded-md bg-yellow-500 text-white text-xs font-medium hover:opacity-90 transition-opacity" onClick={() => review('medium')}>Medium</button>
            <button className="px-2.5 py-1.5 rounded-md bg-red-600 text-white text-xs font-medium hover:opacity-90 transition-opacity" onClick={() => review('hard')}>Hard</button>
          </div>
          <button className="px-3 py-1.5 border border-border rounded-md text-sm font-medium hover:bg-accent/20 transition-colors disabled:opacity-50" onClick={() => setIdx(i => Math.min(i + 1, cards.length - 1))} disabled={idx === cards.length - 1}>Next</button>
        </div>
      </div>
    </div>
  );
}
