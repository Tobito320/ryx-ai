import { useMemo, useState } from 'react';
import { api } from '../../lib/api';
import type { ListSnippetsResponse } from '../../types/api';
import { useToast } from "@/components/ui/use-toast";

interface Props {
  spaceId: string | null;
  snippets: ListSnippetsResponse;
  onSnippetsChange: (snippets: ListSnippetsResponse) => void;
}

const FILTERS = ['All','Definitions','Code','Examples','Images','Phrases','Formulas'] as const;

export default function SnippetsList({ spaceId, snippets, onSnippetsChange }: Props) {
  const { toast } = useToast();
  const [filter, setFilter] = useState<typeof FILTERS[number]>('All');
  const [search, setSearch] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const typeFilter = filter === 'All' ? null : filter.toLowerCase();
    return snippets.filter(sn => {
      const matchesType = typeFilter ? sn.type === typeFilter : true;
      const q = search.trim().toLowerCase();
      const matchesSearch = q ? (sn.content.toLowerCase().includes(q) || sn.title.toLowerCase().includes(q) || sn.tags.some(t => t.toLowerCase().includes(q))) : true;
      return matchesType && matchesSearch;
    });
  }, [snippets, filter, search]);

  if (!spaceId) return <div className="p-3 text-sm text-muted-foreground">Select a space.</div>;

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-2 border-b border-border space-y-2">
        <div className="flex gap-1 flex-wrap">
          {FILTERS.map(f => (
            <button key={f} onClick={() => setFilter(f)} className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${filter===f ? 'bg-foreground text-background' : 'bg-muted text-muted-foreground hover:bg-accent/30'}`}>{f}</button>
          ))}
        </div>
        <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search…" className="w-full border border-border rounded-md px-3 py-1.5 text-sm placeholder:text-muted-foreground bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary" />
      </div>
      <div className="flex-1 overflow-y-auto">
        {filtered.map(sn => (
          <div
            key={sn.id}
            className={`px-4 py-3 border-b border-border transition-colors ${
              (sn as any).justCreated ? 'bg-green-500/10 border-l-2 border-l-green-500' : 'hover:bg-accent/10'
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm text-foreground">{sn.title}</div>
                <div className="text-xs text-muted-foreground mt-1 line-clamp-2">{sn.content}</div>
              </div>
              <span className="text-xs px-2 py-1 rounded-md bg-accent/20 text-accent-foreground font-medium shrink-0 capitalize">{sn.type}</span>
            </div>
            {sn.tags?.length ? (
              <div className="flex flex-wrap gap-1 mt-2">
                {sn.tags.map(t => <span key={t} className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground">{t}</span>)}
              </div>
            ) : null}
            <div className="mt-3 flex gap-1.5">
              <button className="text-xs px-2 py-1 text-muted-foreground hover:bg-accent/20 rounded-md transition-colors">⭐</button>
              <button className="text-xs px-2 py-1 text-muted-foreground hover:bg-accent/20 rounded-md transition-colors">✎</button>
              <button className="text-xs px-2 py-1 text-muted-foreground hover:bg-accent/20 rounded-md transition-colors" onClick={()=>navigator.clipboard.writeText(sn.content)}>📋</button>
              <button
                className="text-xs px-2 py-1 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-md transition-colors flex items-center gap-1"
                disabled={deletingId === sn.id}
                onClick={async()=>{
                  try {
                    setDeletingId(sn.id);
                    await api.del(`/study-spaces/${spaceId}/snippets/${sn.id}`);
                    onSnippetsChange(snippets.filter(i=>i.id!==sn.id));
                    toast({ description: 'Snippet deleted' });
                  } catch(e:any){
                    toast({ description: 'Delete failed', variant: 'destructive' });
                  } finally {
                    setDeletingId(null);
                  }
                }}
              >
                {deletingId === sn.id && <span className="animate-spin inline-block w-3 h-3 border border-current border-t-transparent rounded-full" />}
                🗑
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
