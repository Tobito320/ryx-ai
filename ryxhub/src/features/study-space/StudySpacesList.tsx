import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import type { ListStudySpacesResponse, CreateStudySpaceRequest } from '../../types/api';

interface Props {
  onSelect: (spaceId: string) => void;
  selectedId?: string;
}

export default function StudySpacesList({ onSelect, selectedId }: Props) {
  const [spaces, setSpaces] = useState<ListStudySpacesResponse>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setLoading(true);
      const data = await api.get<ListStudySpacesResponse>('/study-spaces');
      setSpaces(data);
    } catch (e: any) {
      setError(e.message);
    } finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  async function createSpace() {
    const title = prompt('Title (e.g., IPv6 Grundlagen)');
    const subject = prompt('Subject (e.g., LF8 - Netzwerke)');
    if (!title || !subject) return;
    const body: CreateStudySpaceRequest = { title, subject };
    try {
      await api.post('/study-spaces', body);
      await load();
    } catch (e: any) { alert(e.message); }
  }

  if (loading) return <div className="p-3 text-sm text-muted-foreground">Loading spaces…</div>;
  if (error) return <div className="p-3 text-sm text-destructive">{error}</div>;

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-4 border-b border-border flex items-center justify-between">
        <h2 className="text-xs font-semibold text-foreground uppercase tracking-wide">Spaces</h2>
        <button className="px-2 py-1 text-sm bg-primary text-primary-foreground rounded hover:opacity-90 transition-opacity" onClick={createSpace}>+ New</button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {spaces.map(s => (
          <button
            key={s.id}
            onClick={() => onSelect(s.id)}
            className={`w-full text-left px-3 py-2.5 border-b border-border hover:bg-accent/30 transition-colors ${selectedId===s.id? 'bg-accent/50 border-l-2 border-l-primary' : ''}`}
          >
            <div className="text-sm font-medium text-foreground">{s.title}</div>
            <div className="text-xs text-muted-foreground mt-1">{s.subject}</div>
            <div className="text-xs text-muted-foreground/60 mt-1">{s.chatCount} chats • {s.snippetCount} snippets</div>
          </button>
        ))}
      </div>
    </div>
  );
}
