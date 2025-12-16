import { useMemo } from 'react';
import type { Snippet } from '../../types/study-space';

interface Props {
  spaceId: string | null;
  snippets: Snippet[];
}

export default function DefinitionsList({ spaceId, snippets }: Props) {
  const definitions = useMemo(() => snippets.filter(s => s.type === 'definition'), [snippets]);

  if (!spaceId) return <div className="p-4 text-sm text-muted-foreground">Select a space.</div>;
  if (!definitions.length) {
    return (
      <div className="h-full flex items-center justify-center p-4 text-center">
        <div className="text-muted-foreground">
          <p className="text-sm">No definitions yet</p>
          <p className="text-xs mt-1">Create definition snippets from messages</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      {definitions.map(def => (
        <div
          key={def.id}
          className={`px-4 py-3 border-b border-border transition-colors ${
            (def as any).justCreated ? 'bg-green-500/10' : 'hover:bg-accent/10'
          }`}
        >
          <div className="font-medium text-sm text-foreground">{def.title}</div>
          <div className="text-sm text-muted-foreground mt-1 line-clamp-3">{def.content}</div>
          {def.tags?.length ? (
            <div className="flex flex-wrap gap-1 mt-2">
              {def.tags.map(t => (
                <span key={t} className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
                  {t}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
