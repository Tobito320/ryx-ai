// Auto-generated TypeScript types aligned with ryx_study_space_spec.json
// Mirrors FastAPI/Pydantic models on backend Phase 1

export type UUID = string;

export interface StudySpace {
  id: UUID;
  userId?: UUID; // optional if omitted in backend response
  title: string;
  subject: string;
  color?: string | null;
  description?: string | null;
  createdAt: string; // ISO timestamp
  updatedAt?: string; // ISO timestamp
  archivedAt?: string | null;
}

export interface Chat {
  id: UUID;
  spaceId: UUID;
  title: string;
  createdAt: string;
  updatedAt?: string;
  archivedAt?: string | null;
}

export type MessageRole = 'user' | 'assistant';

export interface MessageMetadata {
  model?: string;
  inputTokens?: number;
  outputTokens?: number;
  responseTime?: number; // ms
}

export interface Message {
  id: UUID;
  chatId: UUID;
  role: MessageRole;
  content: string; // markdown supported
  metadata?: MessageMetadata;
  createdAt: string;
}

export type SnippetType = 'definition' | 'code' | 'example' | 'image' | 'phrase' | 'formula';

export interface SnippetSource {
  messageId?: UUID;
  chatId?: UUID;
}

export interface Snippet {
  id: UUID;
  spaceId: UUID;
  sourceMessageId?: UUID | null;
  type: SnippetType;
  title: string;
  content: string; // or URL for images
  tags: string[];
  source?: SnippetSource;
  createdAt: string;
  isFavorite?: boolean;
}

export interface SummaryGeneratedFrom {
  snippetCount: number;
  messageCount: number;
  timeRange?: string;
}

export interface Summary {
  id: UUID;
  spaceId: UUID;
  sessionId?: UUID | null;
  content: string; // markdown
  bullets: string[];
  keyTerms: string[];
  generatedFrom?: SummaryGeneratedFrom;
  createdAt: string;
  regeneratedAt?: string | null;
}

export type Difficulty = 'easy' | 'medium' | 'hard';

export interface Flashcard {
  id: UUID;
  spaceId: UUID;
  snippetId: UUID;
  front: string;
  back: string;
  difficulty: Difficulty;
  reviewCount: number;
  lastReviewedAt?: string | null;
  nextReviewAt?: string | null;
}
