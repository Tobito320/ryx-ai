// Model configuration for GitHub Copilot Pro+
// Cost units are relative (0x = free, 1x = standard, 3x = premium)

export const MODELS = {
  chat: {
    model: "gpt-4o-mini",
    cost: 0,
    maxTokens: 2048,
    description: "Chat, planning, general questions - free tier",
  },
  coding: {
    model: "gpt-4o",
    cost: 1,
    maxTokens: 4096,
    description: "Code generation, module implementation",
  },
  codingAlt: {
    model: "claude-3-5-sonnet-20241022",
    cost: 1,
    maxTokens: 4096,
    description: "Alternative coding model (Claude)",
  },
  emergency: {
    model: "claude-sonnet-4-20250514",
    cost: 3,
    maxTokens: 8192,
    description: "Emergency complex reasoning, critical fixes only",
  },
} as const;

export type ModelType = keyof typeof MODELS;

// Model selection helper
export function selectModel(task: 'plan' | 'code' | 'fix' | 'complex'): ModelType {
  switch (task) {
    case 'plan':
      return 'chat';
    case 'code':
      return 'coding';
    case 'fix':
      return 'codingAlt';
    case 'complex':
      return 'emergency';
    default:
      return 'coding';
  }
}
