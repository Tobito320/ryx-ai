/**
 * Browser Preview Component - Live browser screenshots
 * 
 * Level 3 Streaming: Shows what the agent sees in the browser
 */

import { useState, useEffect } from 'react';

interface BrowserPreviewProps {
  wsUrl?: string;
  initialUrl?: string;
}

export function BrowserPreview({ 
  wsUrl = "ws://localhost:8420/ws/browser",
  initialUrl = ""
}: BrowserPreviewProps) {
  const [screenshot, setScreenshot] = useState("");
  const [currentUrl, setCurrentUrl] = useState(initialUrl);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!initialUrl) return;

    setIsLoading(true);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      ws.send(JSON.stringify({ url: initialUrl }));
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      
      if (msg.type === "browser_screenshot") {
        setScreenshot(`data:image/png;base64,${msg.image}`);
        setCurrentUrl(msg.url);
        setIsLoading(false);
      } else if (msg.type === "browser_action") {
        setIsLoading(true);
      }
    };

    ws.onerror = () => {
      setIsLoading(false);
    };

    return () => ws.close();
  }, [initialUrl, wsUrl]);

  return (
    <div className="browser-preview flex flex-col h-full bg-gray-900 rounded-lg overflow-hidden">
      {/* URL Bar */}
      <div className="url-bar flex items-center gap-2 px-3 py-2 bg-gray-800 border-b border-gray-700">
        <span className="text-green-500">🔒</span>
        <input
          type="text"
          value={currentUrl}
          readOnly
          className="flex-1 bg-gray-700 text-gray-300 text-sm px-3 py-1 rounded outline-none"
          placeholder="No URL"
        />
        {isLoading && (
          <span className="text-blue-400 animate-spin">⟳</span>
        )}
      </div>

      {/* Viewport */}
      <div className="viewport flex-1 bg-gray-950 flex items-center justify-center overflow-hidden">
        {screenshot ? (
          <img
            src={screenshot}
            alt="Browser view"
            className="live-screenshot max-w-full max-h-full object-contain"
          />
        ) : (
          <div className="text-gray-600 text-sm">
            {isLoading ? (
              <div className="flex flex-col items-center gap-2">
                <span className="animate-spin text-2xl">⟳</span>
                <span>Loading page...</span>
              </div>
            ) : (
              "No browser preview"
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default BrowserPreview;
