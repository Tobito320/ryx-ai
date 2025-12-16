import { useEffect, useRef, useState } from 'react';
import { api } from '../../lib/api';
import { connectWS } from '../../lib/ws';
import type { GetMessagesResponse, SendMessageRequest } from '../../types/api';
import type { Snippet } from '../../types/study-space';
import SaveSnippetModal from './SaveSnippetModal';

interface Props {
  spaceId: string | null;
  chatId: string | null;
  onChatTitleUpdate?: (chatId: string, title: string) => void;
  onSnippetCreated?: (snippet: Snippet) => void;
}

export default function MessageThread({ spaceId, chatId, onChatTitleUpdate, onSnippetCreated }: Props) {
  const [messages, setMessages] = useState<GetMessagesResponse>([]);
  const [input, setInput] = useState('');
  const [status, setStatus] = useState<string | null>(null);
  const [titleSet, setTitleSet] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const [snippetModalOpen, setSnippetModalOpen] = useState(false);
  const [snippetInitial, setSnippetInitial] = useState<{ content: string; type: any; messageId?: string }>({ content: '', type: 'definition' });

  useEffect(() => {
    if (!spaceId || !chatId) return;
    (async () => {
      const data = await api.get<GetMessagesResponse>(`/study-spaces/${spaceId}/chats/${chatId}/messages`);
      setMessages(data);
    })();
  }, [spaceId, chatId]);

  function openSnippetModal(message: { id: string; role: string; content: string }) {
    // Try to use selected text if available
    let selection = '';
    if (typeof window !== 'undefined') {
      selection = window.getSelection()?.toString() || '';
    }
    const content = selection.trim() || message.content;
    const initialType = message.role === 'assistant' ? 'definition' : 'phrase';
    setSnippetInitial({ content, type: initialType, messageId: message.id });
    setSnippetModalOpen(true);
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  useEffect(() => {
    if (!spaceId || !chatId) return;
    // connect WebSocket
    const ws = connectWS(`/ws/chat/${spaceId}/${chatId}`, {
      onOpen: () => setStatus('Connected'),
      onClose: () => setStatus('Disconnected'),
      onError: () => setStatus('Error'),
      onMessage: (data) => {
        if (typeof data !== 'object' || !data.type) return;
        switch (data.type) {
          case 'status':
            setStatus(data.message);
            break;
          case 'token':
            // Streaming token for the latest assistant message
            setMessages(prev => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (!last || last.role !== 'assistant') {
                next.push({ id: crypto.randomUUID(), chatId: chatId!, role: 'assistant', content: data.content, createdAt: new Date().toISOString() });
              } else {
                last.content += data.content;
              }
              return next;
            });
            break;
          case 'message_complete':
            // message completed; optionally update metadata
            break;
          case 'error':
            setStatus(`Error: ${data.error}`);
            break;
        }
      }
    });
    wsRef.current = ws;
    return () => { ws.close(); wsRef.current = null; };
  }, [spaceId, chatId]);

  async function send() {
    if (!spaceId || !chatId || !input.trim()) return;
    const userMsg = { id: crypto.randomUUID(), chatId: chatId!, role: 'user' as const, content: input, createdAt: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    const payload: SendMessageRequest = { content: userMsg.content };
    // Attempt to set chat title from first prompt if not set yet
    if (!titleSet) {
      const title = generateTitleFromPrompt(userMsg.content);
      try {
        await api.patch(`/study-spaces/${spaceId}/chats/${chatId}`, { title });
        setTitleSet(true);
        onChatTitleUpdate?.(chatId, title);
      } catch {
        // Backend may not support PATCH; ignore failures
      }
    }

    // Prefer WS streaming if available
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'send_message', ...payload }));
    } else {
      // Fallback to REST
      try {
        const resp = await api.post(`/study-spaces/${spaceId}/chats/${chatId}/messages`, payload);
        setMessages(prev => [...prev, { id: resp.id, chatId: chatId!, role: 'assistant', content: resp.content, createdAt: new Date().toISOString() }]);
      } catch (e: any) {
        setStatus(e.message);
      }
    }
  }

  function generateTitleFromPrompt(text: string) {
    const clean = text.replace(/\s+/g, ' ').trim();
    // Keep concise: first sentence or up to 60 chars
    const firstStop = clean.search(/[.!?]/);
    let base = firstStop > 0 ? clean.slice(0, firstStop) : clean.slice(0, 60);
    if (base.length > 60) base = base.slice(0, 57) + '…';
    // Capitalize
    return base.charAt(0).toUpperCase() + base.slice(1);
  }

  return (
    <div className="h-full flex flex-col bg-background">
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map(m => (
          <div key={m.id} className={`flex ${m.role==='user'?'justify-end':'justify-start'}`}>
            <div className={`max-w-md px-4 py-2.5 rounded-lg ${m.role==='user'?'bg-primary text-primary-foreground':'bg-card text-foreground'}`}>
              <div className="text-sm whitespace-pre-wrap">{m.content}</div>
              <div className="mt-2">
                <button
                  className={`text-xs px-2 py-1 rounded transition-colors ${m.role==='user'?'hover:opacity-80':'hover:bg-accent/20'}`}
                  onClick={() => openSnippetModal(m)}
                >
                  Save as snippet
                </button>
              </div>
            </div>
          </div>
        ))}
        {status && <div className="text-xs text-muted-foreground text-center">{status}</div>}
        <div ref={bottomRef} />
      </div>
      <div className="border-t border-border p-4">
        <div className="flex gap-2 items-end">
          <select className="border border-border rounded-md px-2 py-1.5 text-xs bg-card text-foreground">
            <option>Normal</option>
            <option>Kurz & Technisch</option>
            <option>Code-focused</option>
          </select>
          <textarea value={input} onChange={e=>setInput(e.target.value)} placeholder="Ask something…" className="flex-1 border border-border rounded-md px-3 py-1.5 text-sm bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary" rows={2} />
          <button onClick={send} className="px-4 py-1.5 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 transition-opacity">Send</button>
        </div>
      </div>
      <SaveSnippetModal
        isOpen={snippetModalOpen}
        onClose={() => setSnippetModalOpen(false)}
        initialContent={snippetInitial.content}
        initialType={snippetInitial.type}
        onSave={async ({ type, title, content, tags }) => {
          if (!spaceId || !chatId) throw new Error('Missing space or chat');
          const created = await api.post<Snippet>(`/study-spaces/${spaceId}/snippets`, {
            type,
            title,
            content,
            tags,
            sourceMessageId: snippetInitial.messageId,
          });
          onSnippetCreated?.(created);
        }}
      />
    </div>
  );
}
