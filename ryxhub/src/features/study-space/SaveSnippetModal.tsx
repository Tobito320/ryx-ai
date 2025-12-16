import React, { useState, useEffect } from 'react';
import type { SnippetType } from '../../types/study-space';
import { useToast } from "@/components/ui/use-toast";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  initialContent: string;
  initialType?: SnippetType;
  initialTitle?: string;
  onSave: (payload: { type: SnippetType; title?: string; content: string; tags: string[] }) => Promise<void>;
}

const TYPES: SnippetType[] = ['definition', 'code', 'example', 'image', 'phrase', 'formula'];

export default function SaveSnippetModal({ isOpen, onClose, initialContent, initialType = 'definition', initialTitle = '', onSave }: Props) {
  const { toast } = useToast();
  const [type, setType] = useState<SnippetType>(initialType);
  const [title, setTitle] = useState(initialTitle);
  const [content, setContent] = useState(initialContent);
  const [tags, setTags] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setType(initialType);
      setTitle(initialTitle);
      setContent(initialContent);
      setTags('');
    }
  }, [isOpen, initialContent, initialType, initialTitle]);

  if (!isOpen) return null;

  async function handleSave() {
    setSaving(true);
    try {
      await onSave({ type, title: title || undefined, content, tags: tags.split(',').map(t => t.trim()).filter(Boolean) });
      setTitle('');
      setContent(initialContent);
      setTags('');
      onClose();
      toast({ description: 'Snippet saved ✅' });
    } catch (e) {
      console.error('Saving snippet failed', e);
      toast({ description: 'Saving snippet failed', variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-card w-full max-w-xl rounded shadow-lg p-4 space-y-3 border border-border text-foreground">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">Save as snippet</h3>
          <button onClick={onClose} className="text-sm opacity-60 hover:opacity-100">✕</button>
        </div>
        <div className="space-y-2">
          <label className="block text-sm font-medium">Type</label>
          <select value={type} onChange={e=>setType(e.target.value as SnippetType)} className="w-full border border-border rounded px-2 py-1 text-sm bg-background text-foreground">
            {TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div className="space-y-2">
          <label className="block text-sm font-medium">Title (optional)</label>
          <input value={title} onChange={e=>setTitle(e.target.value)} className="w-full border border-border rounded px-2 py-1 text-sm bg-background text-foreground placeholder:text-muted-foreground" placeholder="Auto-generated" />
        </div>
        <div className="space-y-2">
          <label className="block text-sm font-medium">Content</label>
          <textarea value={content} onChange={e=>setContent(e.target.value)} className="w-full border border-border rounded px-2 py-1 text-sm bg-background text-foreground placeholder:text-muted-foreground" rows={6} />
        </div>
        <div className="space-y-2">
          <label className="block text-sm font-medium">Tags (comma separated)</label>
          <input value={tags} onChange={e=>setTags(e.target.value)} className="w-full border border-border rounded px-2 py-1 text-sm bg-background text-foreground placeholder:text-muted-foreground" placeholder="IPv6, Link-Local" />
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-3 py-1 border border-border rounded text-sm hover:bg-accent/20 transition-colors">Cancel</button>
          <button onClick={handleSave} disabled={saving} className="px-3 py-1 bg-primary text-primary-foreground rounded text-sm flex items-center gap-2 hover:opacity-90 transition-opacity disabled:opacity-50">
            {saving && <span className="animate-spin inline-block w-3 h-3 border-2 border-current border-t-transparent rounded-full" />}
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}
