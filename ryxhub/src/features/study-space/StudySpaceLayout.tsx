import { useEffect, useState, useCallback } from 'react';
import StudySpacesList from './StudySpacesList';
import MessageThread from './MessageThread';
import ChatsList from './ChatsList';
import KnowledgePanel from './KnowledgePanel';
import { api } from '../../lib/api';
import type { GetStudySpaceResponse, ListStudySpacesResponse, CreateChatResponse } from '../../types/api';
import type { Chat, Snippet } from '../../types/study-space';

export default function StudySpaceLayout() {
  const [spaceId, setSpaceId] = useState<string | null>(null);
  const [chatId, setChatId] = useState<string | null>(null);
  const [spaceMeta, setSpaceMeta] = useState<GetStudySpaceResponse | null>(null);
  const [chats, setChats] = useState<Chat[]>([]);
  const [snippets, setSnippets] = useState<Snippet[]>([]);

  const refreshChats = useCallback(async (currentSpaceId: string) => {
    const data = await api.get<GetStudySpaceResponse>(`/study-spaces/${currentSpaceId}`);
    setSpaceMeta(data);
    setChats(data.chats || []);
    try {
      const sn = await api.get<Snippet[]>(`/study-spaces/${currentSpaceId}/snippets`);
      setSnippets(sn as any);
    } catch {
      setSnippets([]);
    }
    let latest: Chat | null = null;
    if (data.chats && data.chats.length > 0) {
      latest = [...data.chats].sort((a: any, b: any) => new Date(b.updatedAt || b.createdAt).getTime() - new Date(a.updatedAt || a.createdAt).getTime())[0];
    }
    if (latest) {
      setChatId(latest.id);
    } else {
      try {
        const created = await api.post<CreateChatResponse>(`/study-spaces/${currentSpaceId}/chats`, {});
        setChats([{ id: created.id, spaceId: currentSpaceId, title: created.title, createdAt: created.createdAt, updatedAt: created.createdAt } as Chat]);
        setChatId(created.id);
      } catch {
        setChatId(null);
      }
    }
  }, []);

  useEffect(() => {
    // On first load, auto-select first space if available
    (async () => {
      if (spaceId) return;
      try {
        const list = await api.get<ListStudySpacesResponse>('/study-spaces');
        if (list.length > 0) {
          setSpaceId(list[0].id);
        }
      } catch {
        // ignore
      }
    })();
  }, [spaceId]);

  useEffect(() => {
    if (!spaceId) return;
    refreshChats(spaceId);
  }, [spaceId, refreshChats]);

  const handleCreateChat = useCallback(async () => {
    if (!spaceId) return;
    const title = `Session ${chats.length + 1}`;
    try {
      const created = await api.post<CreateChatResponse>(`/study-spaces/${spaceId}/chats`, { title });
      const nextChat: Chat = { id: created.id, spaceId, title: created.title, createdAt: created.createdAt, updatedAt: created.createdAt } as Chat;
      setChats(prev => [...prev, nextChat]);
      setChatId(created.id);
    } catch {
      // ignore
    }
  }, [spaceId, chats.length]);

  const handleChatTitleUpdate = useCallback((id: string, title: string) => {
    setChats(prev => prev.map(c => c.id === id ? { ...c, title } : c));
  }, [spaceId, refreshChats]);

  const handleSnippetCreated = useCallback((sn: Snippet) => {
    setSnippets(prev => [{ ...sn, justCreated: true } as Snippet & { justCreated?: boolean }, ...prev]);
    setTimeout(() => {
      setSnippets(current => current.map(s => s.id === sn.id ? { ...s, justCreated: false } : s));
    }, 1800);
  }, []);

  return (
    <div className="h-full grid grid-cols-12 bg-background">
      {/* Left Sidebar: Study Spaces - 2 cols on md+, full on mobile */}
      <div className="col-span-12 md:col-span-2 border-r border-border bg-card min-h-0 flex flex-col">
        <StudySpacesList onSelect={setSpaceId} selectedId={spaceId ?? undefined} />
      </div>

      {/* Center Column: Chats & Messages - 5 cols on md+, full on mobile */}
      <div className="col-span-12 md:col-span-5 border-r border-border min-h-0 flex flex-col bg-background">
        {/* Space Header */}
        <div className="px-4 py-3 border-b border-border">
          <h2 className="text-sm font-semibold text-foreground">{spaceMeta?.space.title ?? 'Select a space'}</h2>
          {spaceMeta?.space.subject && <p className="text-xs text-muted-foreground mt-1">{spaceMeta.space.subject}</p>}
        </div>

        {/* Chats Bar */}
        <ChatsList
          spaceId={spaceId}
          chats={chats}
          activeChatId={chatId}
          onSelectChat={setChatId}
          onCreateChat={handleCreateChat}
        />

        {/* Messages Thread */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <MessageThread
            spaceId={spaceId}
            chatId={chatId}
            onChatTitleUpdate={handleChatTitleUpdate}
            onSnippetCreated={handleSnippetCreated}
          />
        </div>
      </div>

      {/* Right Sidebar: Knowledge Panel - 5 cols on md+, full on mobile */}
      <div className="col-span-12 md:col-span-5 min-h-0 flex flex-col border-r border-border">
        <KnowledgePanel spaceId={spaceId} snippets={snippets as any} onSnippetsChange={setSnippets as any} />
      </div>
    </div>
  );
}
