import type {
  Session,
  Model,
  RAGStatus,
  DashboardStats,
  Message,
  Board,
} from "@/types/ryxhub";

// No hardcoded sessions - all sessions should come from the API
export const mockSessions: Session[] = [];

// No hardcoded models - all models should come from the API
export const mockModels: Model[] = [];

// RAG Status
export const mockRAGStatus: RAGStatus = {
  indexed: 1247,
  pending: 23,
  lastSync: "5m ago",
  status: "idle",
};

// Dashboard Stats
export const mockDashboardStats: DashboardStats = {
  activeAgents: { value: 12, change: "+3 today" },
  workflowsRunning: { value: 4, queued: 2 },
  ragDocuments: { value: 1247, pending: 23 },
  apiCalls: { value: "8.2K", period: "Last 24h" },
};

// Default Boards
export const mockBoards: Board[] = [
  {
    id: "default-board",
    name: "Mein Board",
    description: "Hauptboard für Dokumente und Notizen",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    isDefault: true,
    category: "personal",
  },
];

// Recent Activity for Dashboard
export const mockRecentActivity = [
  { id: 1, type: "success" as const, message: "Dokument indiziert: AOK_Bescheid.pdf", time: "2m ago" },
  { id: 2, type: "info" as const, message: "Neue Notiz erstellt", time: "5m ago" },
  { id: 3, type: "success" as const, message: "E-Mail Entwurf gespeichert", time: "12m ago" },
  { id: 4, type: "info" as const, message: "Board synchronisiert", time: "15m ago" },
  { id: 5, type: "success" as const, message: "Brief-Template geladen", time: "20m ago" },
];
