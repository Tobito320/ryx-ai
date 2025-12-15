/**
 * Streaming Chat Component - Token-by-token visualization
 * 
 * Level 1 Streaming: Shows AI response appearing letter-by-letter
 */

import { useEffect, useState, useRef } from 'react';

interface StreamingChatProps {
  wsUrl?: string;
  prompt?: string;
  onComplete?: (text: string) => void;
}

export function StreamingChat({ 
  wsUrl = "ws://localhost:8420/ws/stream",
  prompt = "",
  onComplete 
}: StreamingChatProps) {
  const [displayText, setDisplayText] = useState("");
  const [status, setStatus] = useState("Ready");
  const [isStreaming, setIsStreaming] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const textRef = useRef<HTMLDivElement>(null);

  const startStreaming = (userPrompt: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.close();
    }

    setDisplayText("");
    setIsStreaming(true);
    setStatus("🔄 Connecting...");

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("🤔 Thinking...");
      ws.send(JSON.stringify({ prompt: userPrompt }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === "status") {
        setStatus(data.message);
      } else if (data.type === "token") {
        setDisplayText(prev => prev + data.content);
        // Auto-scroll
        if (textRef.current) {
          textRef.current.scrollTop = textRef.current.scrollHeight;
        }
      } else if (data.type === "done") {
        setStatus("✅ Complete");
        setIsStreaming(false);
        onComplete?.(displayText);
      } else if (data.type === "error") {
        setStatus(`❌ Error: ${data.message}`);
        setIsStreaming(false);
      }
    };

    ws.onerror = () => {
      setStatus("❌ Connection error");
      setIsStreaming(false);
    };

    ws.onclose = () => {
      if (isStreaming) {
        setStatus("⚠️ Connection closed");
        setIsStreaming(false);
      }
    };
  };

  useEffect(() => {
    if (prompt) {
      startStreaming(prompt);
    }
    return () => {
      wsRef.current?.close();
    };
  }, [prompt]);

  return (
    <div className="streaming-chat flex flex-col h-full bg-gray-900 rounded-lg overflow-hidden">
      {/* Status Bar */}
      <div className="status-bar px-4 py-2 bg-gray-800 border-b border-gray-700 text-sm">
        <span className={isStreaming ? "text-green-400" : "text-gray-400"}>
          {status}
        </span>
      </div>
      
      {/* Response Text */}
      <div 
        ref={textRef}
        className="response-text flex-1 p-4 overflow-y-auto font-mono text-sm text-gray-100 whitespace-pre-wrap"
      >
        {displayText}
        {isStreaming && (
          <span className="cursor-blink text-green-400 font-bold animate-pulse">▊</span>
        )}
      </div>
    </div>
  );
}

export default StreamingChat;
