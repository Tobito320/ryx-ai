/**
 * Exam Evaluation Dashboard - Complete 3-column layout
 * 
 * Combines all 3 visualization levels:
 * - Left: Agent steps (Level 2)
 * - Center: Token streaming (Level 1)  
 * - Right: Results + Browser preview (Level 3)
 */

import { useState, useEffect, useRef, useCallback } from 'react';

interface AgentStep {
  step: string;
  message: string;
  data: Record<string, unknown>;
  timestamp: string;
}

interface EvaluationResult {
  overall_grade: number;
  grade_text: string;
  total_points: number;
  max_points: number;
  percentage: number;
  evaluations: unknown[];
  feedback: string;
}

interface ExamEvaluationDashboardProps {
  wsUrl?: string;
  filePath?: string;
  examId?: string;
  useSandbox?: boolean;
  sandboxType?: 'docker' | 'e2b';
}

const STEP_ICONS: Record<string, string> = {
  planning: "🧠", searching: "🔎", scraping: "📄", processing: "⚙️",
  synthesizing: "🧩", responding: "✍️", complete: "✅", error: "❌",
  ingestion: "📥", ocr: "📸", rubric: "📋", evaluation: "🔍",
  feedback: "✍️", aggregation: "📊", report: "📄",
  parallel_start: "⚡", parallel_complete: "✅", evaluating: "🔍",
  sandbox_init: "🔒", sandbox_ready: "✅", sandbox_executing: "⚙️",
  sandbox_cleanup: "🗑️", sandbox_destroyed: "✅"
};

export function ExamEvaluationDashboard({
  wsUrl = "ws://localhost:8420/ws/exam-evaluation",
  filePath = "",
  examId = "",
  useSandbox = false,
  sandboxType = "docker"
}: ExamEvaluationDashboardProps) {
  const [status, setStatus] = useState("Ready to start");
  const [progress, setProgress] = useState(0);
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [tokens, setTokens] = useState("");
  const [results, setResults] = useState<EvaluationResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const tokensRef = useRef<HTMLDivElement>(null);
  const stepsRef = useRef<HTMLDivElement>(null);

  const startEvaluation = useCallback(() => {
    if (!filePath) {
      setError("No file path provided");
      return;
    }

    // Reset state
    setSteps([]);
    setTokens("");
    setResults(null);
    setError(null);
    setProgress(0);
    setIsRunning(true);
    setStatus("🔄 Connecting...");

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("📡 Connected, starting evaluation...");
      ws.send(JSON.stringify({
        file_path: filePath,
        exam_id: examId,
        use_sandbox: useSandbox,
        sandbox_type: sandboxType
      }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case "status":
          setStatus(data.message);
          if (data.percent !== undefined) {
            setProgress(data.percent);
          }
          break;

        case "agent_step":
          setSteps(prev => [...prev, {
            step: data.step,
            message: data.message,
            data: data.data || {},
            timestamp: data.timestamp
          }]);
          // Auto-scroll steps
          setTimeout(() => {
            stepsRef.current?.scrollTo({
              top: stepsRef.current.scrollHeight,
              behavior: 'smooth'
            });
          }, 100);
          break;

        case "token":
          setTokens(prev => prev + data.content);
          // Auto-scroll tokens
          if (tokensRef.current) {
            tokensRef.current.scrollTop = tokensRef.current.scrollHeight;
          }
          break;

        case "complete":
          setResults({
            overall_grade: data.overall_grade,
            grade_text: data.grade_text,
            total_points: data.total_points,
            max_points: data.max_points,
            percentage: data.percentage,
            evaluations: data.evaluations,
            feedback: data.feedback
          });
          setStatus("✅ Evaluation complete!");
          setProgress(100);
          setIsRunning(false);
          break;

        case "error":
          setError(data.message);
          setStatus(`❌ Error: ${data.message}`);
          setIsRunning(false);
          break;
      }
    };

    ws.onerror = () => {
      setError("WebSocket connection error");
      setStatus("❌ Connection error");
      setIsRunning(false);
    };

    ws.onclose = () => {
      if (isRunning) {
        setStatus("⚠️ Connection closed");
        setIsRunning(false);
      }
    };
  }, [filePath, examId, useSandbox, sandboxType, wsUrl]);

  useEffect(() => {
    return () => {
      wsRef.current?.close();
    };
  }, []);

  const getGradeColor = (grade: number) => {
    if (grade <= 1.5) return "text-green-400";
    if (grade <= 2.5) return "text-blue-400";
    if (grade <= 3.5) return "text-yellow-400";
    if (grade <= 4.5) return "text-orange-400";
    return "text-red-400";
  };

  return (
    <div className="exam-dashboard flex flex-col h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <div className="header px-6 py-4 bg-gray-900 border-b border-gray-800">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">📝 Exam Evaluation</h1>
            <p className="text-sm text-gray-400 mt-1">{status}</p>
          </div>
          <button
            onClick={startEvaluation}
            disabled={isRunning || !filePath}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              isRunning || !filePath
                ? "bg-gray-700 text-gray-500 cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-500 text-white"
            }`}
          >
            {isRunning ? "Processing..." : "Start Evaluation"}
          </button>
        </div>
        
        {/* Progress Bar */}
        {isRunning && (
          <div className="mt-3">
            <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">{progress}% complete</p>
          </div>
        )}
      </div>

      {/* Main Content - 3 Columns */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Column: Agent Steps */}
        <div className="w-1/4 border-r border-gray-800 flex flex-col">
          <div className="px-4 py-3 bg-gray-900 border-b border-gray-800">
            <h2 className="text-sm font-semibold flex items-center gap-2">
              🤖 Agent Activity
              {isRunning && (
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              )}
            </h2>
          </div>
          <div ref={stepsRef} className="flex-1 overflow-y-auto p-3 space-y-2">
            {steps.length === 0 && !isRunning && (
              <p className="text-gray-500 text-sm text-center py-8">
                No activity yet
              </p>
            )}
            {steps.map((step, idx) => (
              <div
                key={idx}
                className={`flex gap-2 p-2 rounded border-l-2 ${
                  idx === steps.length - 1 && isRunning
                    ? "border-green-500 bg-green-500/10"
                    : "border-gray-700"
                }`}
              >
                <span className="text-lg">{STEP_ICONS[step.step] || "⚙️"}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-200 truncate">{step.message}</p>
                  <p className="text-xs text-gray-600">
                    {new Date(step.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Center Column: Token Stream */}
        <div className="w-1/2 flex flex-col">
          <div className="px-4 py-3 bg-gray-900 border-b border-gray-800">
            <h2 className="text-sm font-semibold">✍️ AI Response</h2>
          </div>
          <div
            ref={tokensRef}
            className="flex-1 overflow-y-auto p-4 font-mono text-sm whitespace-pre-wrap"
          >
            {tokens || (
              <span className="text-gray-500">
                Response will appear here...
              </span>
            )}
            {isRunning && tokens && (
              <span className="text-green-400 font-bold animate-pulse">▊</span>
            )}
          </div>
        </div>

        {/* Right Column: Results */}
        <div className="w-1/4 border-l border-gray-800 flex flex-col">
          <div className="px-4 py-3 bg-gray-900 border-b border-gray-800">
            <h2 className="text-sm font-semibold">📊 Results</h2>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            {error && (
              <div className="bg-red-500/20 border border-red-500 rounded-lg p-3 mb-4">
                <p className="text-red-400 text-sm">{error}</p>
              </div>
            )}
            
            {results ? (
              <div className="space-y-4">
                {/* Grade Display */}
                <div className="text-center py-6 bg-gray-800 rounded-lg">
                  <div className={`text-5xl font-bold ${getGradeColor(results.overall_grade)}`}>
                    {results.overall_grade.toFixed(1)}
                  </div>
                  <div className="text-lg text-gray-300 mt-1">
                    {results.grade_text}
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-gray-800 rounded-lg p-3 text-center">
                    <div className="text-2xl font-semibold text-blue-400">
                      {results.total_points}
                    </div>
                    <div className="text-xs text-gray-500">
                      / {results.max_points} pts
                    </div>
                  </div>
                  <div className="bg-gray-800 rounded-lg p-3 text-center">
                    <div className="text-2xl font-semibold text-purple-400">
                      {results.percentage}%
                    </div>
                    <div className="text-xs text-gray-500">Score</div>
                  </div>
                </div>

                {/* Feedback Preview */}
                {results.feedback && (
                  <div className="bg-gray-800 rounded-lg p-3">
                    <h3 className="text-sm font-medium text-gray-300 mb-2">
                      💬 Feedback
                    </h3>
                    <p className="text-xs text-gray-400 line-clamp-4">
                      {results.feedback.slice(0, 200)}...
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-gray-500 text-sm text-center py-8">
                Results will appear here after evaluation
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ExamEvaluationDashboard;
