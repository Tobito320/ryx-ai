/**
 * RyxHub Smoke Tests
 *
 * Minimal tests to verify key flows work correctly.
 * Run with: npm test
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock components for isolated testing
import { cn } from '@/lib/utils';
import { mockApi } from '@/lib/api/mock';
import { ryxService } from '@/services/ryxService';

// ============ Utility Tests ============

describe('cn() utility', () => {
  it('merges class names correctly', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('handles conditional classes', () => {
    expect(cn('base', true && 'active', false && 'hidden')).toBe('base active');
  });

  it('deduplicates Tailwind classes', () => {
    expect(cn('p-4', 'p-6')).toBe('p-6');
  });
});

// ============ Mock API Tests ============

describe('Mock API', () => {
  it('returns health status', async () => {
    const health = await mockApi.getHealth();
    expect(health.status).toBe('healthy');
    expect(health.vllm_status).toBe('online');
  });

  it('returns models list', async () => {
    const models = await mockApi.listModels();
    expect(models.length).toBeGreaterThan(0);
    expect(models[0].provider).toBe('vLLM');
  });

  it('returns sessions list', async () => {
    const sessions = await mockApi.listSessions();
    expect(sessions.length).toBeGreaterThan(0);
  });

  it('handles sendMessage correctly', async () => {
    const response = await mockApi.sendMessage('session-1', 'Test message');
    expect(response.role).toBe('assistant');
    expect(response.content.length).toBeGreaterThan(0);
  });

  it('returns RAG status', async () => {
    const ragStatus = await mockApi.getRagStatus();
    expect(ragStatus.indexed).toBeGreaterThan(0);
    expect(['idle', 'syncing', 'error']).toContain(ragStatus.status);
  });

  it('triggers RAG sync', async () => {
    const result = await mockApi.triggerRagSync();
    expect(result.success).toBe(true);
    expect(result.queued_files).toBeGreaterThan(0);
  });

  it('returns workflows list', async () => {
    const workflows = await mockApi.listWorkflows();
    expect(workflows.length).toBeGreaterThan(0);
  });

  it('returns agents list', async () => {
    const agents = await mockApi.listAgents();
    expect(agents.length).toBeGreaterThan(0);
    expect(agents.some(a => a.model.includes('Qwen') || a.model.includes('Llama'))).toBe(true);
  });

  it('returns tools list', async () => {
    const tools = await mockApi.listTools();
    expect(tools.length).toBeGreaterThan(0);
    expect(tools.some(t => t.name.includes('RAG'))).toBe(true);
  });
});

// ============ Service Layer Tests ============

describe('RyxService', () => {
  it('uses mock API in test environment', async () => {
    // Service should be using mock API since VITE_USE_MOCK_API defaults to true
    const models = await ryxService.listModels();
    expect(models.length).toBeGreaterThan(0);
  });

  it('provides stream URL', () => {
    const url = ryxService.getStreamUrl('test-session');
    expect(url).toContain('chat/completions');
  });
});

// ============ Data Integrity Tests ============

describe('Mock Data Integrity', () => {
  it('models use vLLM provider (no Ollama)', async () => {
    const models = await mockApi.listModels();
    models.forEach(model => {
      expect(model.provider).toBe('vLLM');
      expect(model.name).not.toContain('GPT');
      expect(model.name).not.toContain('Claude');
      expect(model.name).not.toContain('Gemini');
    });
  });

  it('sessions reference vLLM models', async () => {
    const session = await mockApi.getSession('session-1');
    expect(session.model).not.toContain('GPT');
    expect(session.model).not.toContain('Claude');
  });
});
