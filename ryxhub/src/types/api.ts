import type { UUID, StudySpace, Chat, Message, Snippet, Summary, Flashcard, SnippetType } from './study-space';

// API response types based on ryx_study_space_spec.json

export interface CreateStudySpaceRequest {
  title: string;
  subject: string;
  color?: string;
  description?: string;
}

export interface CreateStudySpaceResponse {
  id: UUID;
  title: string;
  subject: string;
  createdAt: string;
}

export type ListStudySpacesResponse = Array<{
  id: UUID;
  title: string;
  subject: string;
  snippetCount: number;
  chatCount: number;
  lastUpdated: string;
}>;

export interface GetStudySpaceResponse {
  space: Pick<StudySpace, 'id' | 'title' | 'subject' | 'color'>;
  snippets: Snippet[];
  summary: Summary | null;
  chats: Chat[]; // summaries only assumed in Phase 1
  stats: {
    totalMessages: number;
    totalSnippets: number;
    types: Record<SnippetType, number>;
  };
}

export interface CreateChatRequest { title?: string }
export interface CreateChatResponse { id: UUID; spaceId: UUID; title: string; createdAt: string }

export type GetMessagesResponse = Message[];

export interface SendMessageRequest {
  content: string;
  model?: string; // optional
}

export interface SendMessageResponse {
  id: UUID;
  role: 'assistant';
  content: string;
}

export interface CreateSnippetRequest {
  type: SnippetType;
  title?: string;
  content: string;
  tags?: string[];
  sourceMessageId?: UUID;
}

export interface CreateSnippetResponse {
  id: UUID;
  spaceId: UUID;
  type: SnippetType;
  title: string;
  tags: string[];
  createdAt: string;
}

export type ListSnippetsResponse = Array<{
  id: UUID;
  type: SnippetType;
  title: string;
  content: string; // truncated to 200 chars on server
  tags: string[];
  createdAt: string;
}>;

export type GroupedSnippetsResponse = {
  definitions: Snippet[];
  code: Snippet[];
  examples: Snippet[];
  images: Snippet[];
  phrases: Snippet[];
  formulas: Snippet[];
};

export interface UpdateSnippetRequest {
  content?: string;
  tags?: string[];
  isFavorite?: boolean;
}

export interface GenerateSummaryRequest {
  scope?: 'all' | 'last-session' | 'last-24h';
  includeSnippets?: boolean;
}

export interface GenerateSummaryResponse extends Summary {}

export type ListFlashcardsResponse = Flashcard[];
export type ListDueFlashcardsResponse = Flashcard[];

export interface ReviewFlashcardRequest { result: 'easy' | 'medium' | 'hard' }
export interface ReviewFlashcardResponse {
  id: UUID;
  difficulty: 'easy' | 'medium' | 'hard';
  reviewCount: number;
  nextReviewAt: string;
}
