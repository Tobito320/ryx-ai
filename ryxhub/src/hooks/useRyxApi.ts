/**
 * React Query Hooks for RyxHub
 * 
 * Pre-built hooks for common data fetching patterns.
 * Uses ryxService under the hood for mock/live switching.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ryxService, queryKeys } from '@/services/ryxService';
import { toast } from 'sonner';

// ============ Health & Status ============

export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: () => ryxService.getHealth(),
    refetchInterval: 30000, // Check every 30s
    staleTime: 10000,
  });
}

export function useStatus() {
  return useQuery({
    queryKey: queryKeys.status,
    queryFn: () => ryxService.getStatus(),
    refetchInterval: 5000, // More frequent updates
    staleTime: 2000,
  });
}

// ============ Models ============

export function useModels() {
  return useQuery({
    queryKey: queryKeys.models,
    queryFn: () => ryxService.listModels(),
    staleTime: 60000,
  });
}

export function useLoadModel() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (modelId: string) => ryxService.loadModel(modelId),
    onSuccess: (_, modelId) => {
      toast.success(`Model ${modelId} loaded`);
      queryClient.invalidateQueries({ queryKey: queryKeys.models });
    },
    onError: (error: Error) => {
      toast.error(`Failed to load model: ${error.message}`);
    },
  });
}

export function useUnloadModel() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (modelId: string) => ryxService.unloadModel(modelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.models });
    },
  });
}

// ============ Sessions ============

export function useSessions() {
  return useQuery({
    queryKey: queryKeys.sessions,
    queryFn: () => ryxService.listSessions(),
    staleTime: 30000,
  });
}

export function useSession(sessionId: string | null) {
  return useQuery({
    queryKey: queryKeys.session(sessionId || ''),
    queryFn: () => ryxService.getSession(sessionId!),
    enabled: !!sessionId,
    staleTime: 10000,
  });
}

export function useCreateSession() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: { name: string; model: string }) => ryxService.createSession(data),
    onSuccess: () => {
      toast.success('Session created');
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions });
    },
    onError: (error: Error) => {
      toast.error(`Failed to create session: ${error.message}`);
    },
  });
}

export function useDeleteSession() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (sessionId: string) => ryxService.deleteSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions });
    },
  });
}

export function useSendMessage() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ sessionId, message, model }: { sessionId: string; message: string; model?: string }) =>
      ryxService.sendMessage(sessionId, message, model),
    onSuccess: (_, { sessionId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.session(sessionId) });
    },
    onError: (error: Error) => {
      toast.error(`Failed to send message: ${error.message}`);
    },
  });
}

// ============ RAG ============

export function useRagStatus() {
  return useQuery({
    queryKey: queryKeys.ragStatus,
    queryFn: () => ryxService.getRagStatus(),
    refetchInterval: 10000,
    staleTime: 5000,
  });
}

export function useTriggerRagSync() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: () => ryxService.triggerRagSync(),
    onSuccess: (data) => {
      toast.success(`RAG sync started: ${data.queued_files} files queued`);
      queryClient.invalidateQueries({ queryKey: queryKeys.ragStatus });
    },
    onError: (error: Error) => {
      toast.error(`Failed to sync RAG: ${error.message}`);
    },
  });
}

export function useRagSearch() {
  return useMutation({
    mutationFn: ({ query, topK }: { query: string; topK?: number }) =>
      ryxService.searchRag(query, topK),
  });
}

// ============ Workflows ============

export function useWorkflows() {
  return useQuery({
    queryKey: queryKeys.workflows,
    queryFn: () => ryxService.listWorkflows(),
    staleTime: 30000,
  });
}

export function useWorkflow(workflowId: string | null) {
  return useQuery({
    queryKey: queryKeys.workflow(workflowId || ''),
    queryFn: () => ryxService.getWorkflow(workflowId!),
    enabled: !!workflowId,
    staleTime: 10000,
  });
}

export function useRunWorkflow() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (workflowId: string) => ryxService.runWorkflow(workflowId),
    onSuccess: (data) => {
      toast.success(`Workflow started: ${data.run_id}`);
      queryClient.invalidateQueries({ queryKey: queryKeys.workflows });
    },
    onError: (error: Error) => {
      toast.error(`Failed to run workflow: ${error.message}`);
    },
  });
}

export function usePauseWorkflow() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (workflowId: string) => ryxService.pauseWorkflow(workflowId),
    onSuccess: () => {
      toast.success('Workflow paused');
      queryClient.invalidateQueries({ queryKey: queryKeys.workflows });
    },
  });
}

// ============ Agents ============

export function useAgents() {
  return useQuery({
    queryKey: queryKeys.agents,
    queryFn: () => ryxService.listAgents(),
    refetchInterval: 5000,
    staleTime: 2000,
  });
}

export function useAgentLogs(agentId: string | null, lines?: number) {
  return useQuery({
    queryKey: queryKeys.agentLogs(agentId || ''),
    queryFn: () => ryxService.getAgentLogs(agentId!, lines),
    enabled: !!agentId,
    refetchInterval: 2000,
    staleTime: 1000,
  });
}

// ============ Tools ============

export function useTools() {
  return useQuery({
    queryKey: queryKeys.tools,
    queryFn: () => ryxService.listTools(),
    staleTime: 60000,
  });
}

export function useExecuteToolDry() {
  return useMutation({
    mutationFn: ({ toolName, params }: { toolName: string; params: Record<string, unknown> }) =>
      ryxService.executeToolDry(toolName, params),
  });
}
