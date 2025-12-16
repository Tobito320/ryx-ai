import { useMemo } from 'react';
import type { Chat } from '../../types/study-space';

interface Props {
  spaceId: string | null;
  activeChatId: string | null;
  onSelectChat: (chatId: string) => void;
  chats: Chat[];
  onCreateChat: () => void;
}

export default function ChatsList({ spaceId, activeChatId, onSelectChat, chats, onCreateChat }: Props) {
  if (!spaceId) return <div className="p-2 text-sm text-muted-foreground">Select a space.</div>;

  return (
    <div className="border-b border-border px-3 py-2 flex items-center justify-between gap-2 bg-card">
      <div className="flex-1 overflow-x-auto">
        <div className="flex gap-1.5">
          {chats.map(c => (
            <button
              key={c.id}
              onClick={() => onSelectChat(c.id)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${activeChatId===c.id? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:bg-background/50'}`}
              title={new Date(c.updatedAt || c.createdAt).toLocaleString()}
            >
              {c.title}
            </button>
          ))}
        </div>
      </div>
      <button onClick={onCreateChat} className="shrink-0 px-2.5 py-1.5 text-xs font-medium bg-primary text-primary-foreground rounded-md hover:opacity-90 transition-opacity">
        + New
      </button>
    </div>
  );
}
