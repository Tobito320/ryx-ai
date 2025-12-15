/**
 * Agent Step Visualizer - Shows agent thinking process
 * 
 * Level 2 Streaming: Shows step-by-step agent activity
 */

import { useState, useEffect, useRef } from 'react';

interface AgentStep {
  step: string;
  message: string;
  data: Record<string, unknown>;
  timestamp: string;
}

interface AgentStepVisualizerProps {
  wsUrl?: string;
  query?: string;
  onStepUpdate?: (steps: AgentStep[]) => void;
}

const STEP_ICONS: Record<string, string> = {
  planning: "🧠",
  searching: "🔎",
  scraping: "📄",
  processing: "⚙️",
  synthesizing: "🧩",
  responding: "✍️",
  complete: "✅",
  error: "❌",
  ingestion: "📥",
  ocr: "📸",
  rubric: "📋",
  evaluation: "🔍",
  feedback: "✍️",
  aggregation: "📊",
  report: "📄",
  parallel_start: "⚡",
  parallel_complete: "✅",
  evaluating: "🔍",
  sandbox_init: "🔒",
  sandbox_ready: "✅",
  sandbox_executing: "⚙️",
  sandbox_cleanup: "🗑️",
  sandbox_destroyed: "✅"
};

export function AgentStepVisualizer({ 
  wsUrl = "ws://localhost:8420/ws/agent",
  query = "",
  onStepUpdate 
}: AgentStepVisualizerProps) {
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [currentStep, setCurrentStep] = useState<string>("");
  const [isActive, setIsActive] = useState(false);
  const timelineRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!query) return;

    setSteps([]);
    setIsActive(true);

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      ws.send(JSON.stringify({ query }));
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      
      if (msg.type === "agent_step") {
        const newStep: AgentStep = {
          step: msg.step,
          message: msg.message,
          data: msg.data || {},
          timestamp: msg.timestamp
        };
        
        setSteps(prev => {
          const updated = [...prev, newStep];
          onStepUpdate?.(updated);
          return updated;
        });
        setCurrentStep(msg.step);
        
        // Auto-scroll
        setTimeout(() => {
          timelineRef.current?.scrollTo({
            top: timelineRef.current.scrollHeight,
            behavior: 'smooth'
          });
        }, 100);

        if (msg.step === "complete") {
          setIsActive(false);
        }
      }
    };

    ws.onerror = () => {
      setIsActive(false);
    };

    ws.onclose = () => {
      setIsActive(false);
    };

    return () => ws.close();
  }, [query]);

  const getStepIcon = (step: string) => STEP_ICONS[step] || "⚙️";

  const getStepClass = (step: AgentStep, index: number) => {
    const isLast = index === steps.length - 1;
    const isCurrent = step.step === currentStep && isActive;
    
    if (isCurrent) return "border-green-500 bg-green-500/10";
    if (isLast && !isActive) return "border-gray-500";
    return "border-gray-700";
  };

  return (
    <div className="agent-steps-panel flex flex-col h-full bg-gray-900 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-gray-800 border-b border-gray-700">
        <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
          <span>🤖</span>
          Agent Activity
          {isActive && (
            <span className="ml-auto w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          )}
        </h3>
      </div>

      {/* Timeline */}
      <div 
        ref={timelineRef}
        className="timeline flex-1 overflow-y-auto p-4 space-y-3"
      >
        {steps.length === 0 && !isActive && (
          <div className="text-gray-500 text-sm text-center py-8">
            No activity yet
          </div>
        )}
        
        {steps.map((step, idx) => (
          <div
            key={idx}
            className={`step flex gap-3 p-3 rounded-lg border-l-4 transition-all duration-300 ${getStepClass(step, idx)}`}
          >
            {/* Icon */}
            <div className="step-icon text-2xl flex-shrink-0">
              {getStepIcon(step.step)}
            </div>
            
            {/* Content */}
            <div className="step-content flex-1 min-w-0">
              <div className="step-title text-sm font-medium text-gray-200">
                {step.message}
              </div>
              
              {/* Extra details */}
              {step.data.search_query && (
                <div className="text-xs text-gray-500 mt-1">
                  Query: <code className="bg-gray-800 px-1 rounded">{step.data.search_query as string}</code>
                </div>
              )}
              
              {step.data.url && (
                <div className="text-xs text-gray-500 mt-1 truncate">
                  <a 
                    href={step.data.url as string} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-blue-400 hover:underline"
                  >
                    {step.data.url as string}
                  </a>
                </div>
              )}
              
              {step.data.content_preview && (
                <div className="text-xs text-gray-600 mt-1 bg-gray-800 p-2 rounded max-h-20 overflow-hidden">
                  {(step.data.content_preview as string).slice(0, 150)}...
                </div>
              )}
            </div>
            
            {/* Time */}
            <div className="step-time text-xs text-gray-600 flex-shrink-0">
              {new Date(step.timestamp).toLocaleTimeString()}
            </div>
          </div>
        ))}
        
        {isActive && currentStep !== "complete" && (
          <div className="flex items-center gap-2 text-gray-500 text-sm pl-3">
            <span className="animate-spin">⏳</span>
            Processing...
          </div>
        )}
      </div>
    </div>
  );
}

export default AgentStepVisualizer;
