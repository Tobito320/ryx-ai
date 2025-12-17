import { useState, useRef } from "react";
import { Send, Paperclip } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

type Props = {
  onSendMessage: (message: string) => void;
  isTyping: boolean;
};

export function EmptyChatState({ onSendMessage, isTyping }: Props) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (!input.trim() || isTyping) return;
    onSendMessage(input);
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full items-center justify-center bg-[hsl(var(--background))] px-4">
      <div className="max-w-[720px] w-full space-y-8">
        {/* Headline */}
        <div className="text-center space-y-3">
          <h1 className="text-2xl font-semibold tracking-tight text-[hsl(var(--foreground))]">
            Was möchtest du lernen?
          </h1>
          <p className="text-[hsl(var(--muted-foreground))] text-sm">
            Starte eine Konversation
          </p>
        </div>

        {/* Input box */}
        <div className="relative flex items-end gap-2">
          <div className="flex-1 relative">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message Ryx..."
              disabled={isTyping}
              className="min-h-[52px] max-h-[200px] pr-12 text-sm resize-none rounded-2xl border-[hsl(var(--border))] bg-[hsl(var(--background))] focus:border-[hsl(var(--primary))]"
            />
            <div className="absolute right-2 bottom-2">
              <Button variant="ghost" size="icon" className="h-8 w-8" disabled>
                <Paperclip className="w-4 h-4" />
              </Button>
            </div>
          </div>
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            size="icon"
            className="h-[52px] w-[52px] rounded-full bg-[hsl(var(--primary))] hover:opacity-90 transition-opacity"
          >
            <Send className="w-5 h-5" />
          </Button>
        </div>
      </div>
    </div>
  );
}
