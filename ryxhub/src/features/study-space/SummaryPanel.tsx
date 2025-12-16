import { useEffect, useRef, useState } from 'react';
import { api } from '../../lib/api';
import { connectWS } from '../../lib/ws';
import type { Summary } from '../../types/study-space';
import type { GenerateSummaryRequest } from '../../types/api';

interface Props {
  spaceId: string | null;
}

export default function SummaryPanel({ spaceId }: Props) {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState('');
  const [bullets, setBullets] = useState<string[]>([]);
  const [keyTerms, setKeyTerms] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!spaceId) return;
    (async () => {
      try {
        setLoading(true);
        const res = await api.get<Summary | { error: string }>(`/study-spaces/${spaceId}/summary`);
        if ((res as any)?.error) {
          setSummary(null);
        } else {
          setSummary(res as Summary);
          setBullets((res as Summary).bullets || []);
          setKeyTerms((res as Summary).keyTerms || []);
        }
      } catch {
        setSummary(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [spaceId]);

  useEffect(() => () => { wsRef.current?.close(); }, []);

  async function regenerate() {
    if (!spaceId) return;
    wsRef.current?.close();
    setStreaming(true);
    setStreamText('');
    setBullets([]);
    setKeyTerms([]);
    // Connect for streaming
    wsRef.current = connectWS(`/ws/generate-summary/${spaceId}`, {
      onMessage: (data) => {
        if (!data || typeof data !== 'object' || !data.type) return;
        switch (data.type) {
          case 'status':
            break;
          case 'token':
            setStreamText(prev => prev + data.content);
            break;
          case 'bullet_complete':
            setBullets(prev => [...prev, data.bullet]);
            break;
          case 'summary_complete':
            setSummary({
              id: data.summaryId,
              spaceId,
              content: data.content ?? streamText,
              bullets: data.bullets ?? bullets,
              keyTerms: data.keyTerms ?? [],
              generatedFrom: data.generatedFrom,
              createdAt: new Date().toISOString(),
            });
            setKeyTerms(data.keyTerms ?? []);
            setStreaming(false);
            wsRef.current?.close();
            break;
        }
      },
      onClose: () => setStreaming(false),
      onError: () => setStreaming(false),
    });
    // Kick off generation via REST in case server expects it
    const body: GenerateSummaryRequest = { scope: 'all', includeSnippets: true };
    try {
      await api.post(`/study-spaces/${spaceId}/generate-summary`, body);
    } catch {
      // ignore; ws may still stream
    }
  }

  if (!spaceId) return <div className="p-3 text-sm text-muted-foreground">Select a space.</div>;
  if (loading) return <div className="p-3 text-sm text-muted-foreground">Loading summary…</div>;

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <div className="font-semibold text-sm">Summary</div>
        <button onClick={regenerate} className="px-3 py-1.5 text-xs font-medium bg-primary text-primary-foreground rounded-md hover:opacity-90 transition-opacity disabled:opacity-50" disabled={streaming}>
          {streaming ? 'Generating…' : 'Regenerate'}
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {streaming && (
          <div className="p-3 border border-border rounded-md bg-card whitespace-pre-wrap text-sm text-foreground">
            {streamText || 'Generating…'}
          </div>
        )}
        {summary && !streaming && (
          <div className="space-y-3">
            <div className="text-sm text-foreground whitespace-pre-wrap">{summary.content}</div>
            {summary.bullets?.length ? (
              <ul className="list-disc list-inside text-sm space-y-1 text-foreground">
                {summary.bullets.map((b, idx) => <li key={idx} className="text-sm">{b}</li>)}
              </ul>
            ) : null}
            {keyTerms?.length ? (
              <div className="flex flex-wrap gap-2">
                {keyTerms.map(term => <span key={term} className="text-xs px-2.5 py-1 rounded-full bg-accent/20 text-accent-foreground font-medium">{term}</span>)}
              </div>
            ) : null}
          </div>
        )}
        {!summary && !streaming && (
          <div className="flex items-center justify-center h-full text-center">
            <div className="text-muted-foreground">
              <p className="text-sm">No summary yet</p>
              <p className="text-xs mt-1">Click "Regenerate" to create one</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
