import { useState } from 'react';
import { BookMarked, BookOpen, FileText, Lightbulb, Image as ImageIcon } from 'lucide-react';
import SnippetsList from './SnippetsList';
import DefinitionsList from './DefinitionsList';
import SummaryPanel from './SummaryPanel';
import FlashcardsPanel from './FlashcardsPanel';
import type { Snippet } from '../../types/study-space';

type Tab = 'snippets' | 'definitions' | 'summary' | 'flashcards' | 'images';

interface Props {
  spaceId: string | null;
  snippets: Snippet[];
  onSnippetsChange: (snippets: Snippet[]) => void;
}

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'snippets', label: 'Snippets', icon: <BookMarked className="w-4 h-4" /> },
  { id: 'definitions', label: 'Definitions', icon: <FileText className="w-4 h-4" /> },
  { id: 'summary', label: 'Summary', icon: <Lightbulb className="w-4 h-4" /> },
  { id: 'flashcards', label: 'Flashcards', icon: <BookOpen className="w-4 h-4" /> },
  { id: 'images', label: 'Images', icon: <ImageIcon className="w-4 h-4" /> },
];

export default function KnowledgePanel({ spaceId, snippets, onSnippetsChange }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('snippets');

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Tab Bar */}
      <div className="border-b border-border px-3 py-0 flex gap-0 overflow-x-auto">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors border-b-2 whitespace-nowrap ${
              activeTab === tab.id
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
            title={tab.label}
          >
            {tab.icon}
            <span className="hidden sm:inline">{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {activeTab === 'snippets' && <SnippetsList spaceId={spaceId} snippets={snippets} onSnippetsChange={onSnippetsChange} />}
        {activeTab === 'definitions' && <DefinitionsList spaceId={spaceId} snippets={snippets} />}
        {activeTab === 'summary' && <SummaryPanel spaceId={spaceId} />}
        {activeTab === 'flashcards' && <FlashcardsPanel spaceId={spaceId} />}
        {activeTab === 'images' && (
          <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
            <div className="text-center">
              <ImageIcon className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No images yet</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
