import { useState, useRef, useEffect } from "react";
import { 
  Copy, RotateCcw, Minus, Plus, BookOpen, Edit2, Trash2, Brain, Check
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface MessageActionsMenuProps {
  messageId: string;
  messageContent: string;
  isUser: boolean;
  position: { x: number; y: number };
  onClose: () => void;
  onRegenerate?: () => void;
  onMakeShorter?: () => void;
  onMakeLonger?: () => void;
  onExplainMore?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  onAddToMemory?: () => void;
}

export function MessageActionsMenu({
  messageId,
  messageContent,
  isUser,
  position,
  onClose,
  onRegenerate,
  onMakeShorter,
  onMakeLonger,
  onExplainMore,
  onEdit,
  onDelete,
  onAddToMemory
}: MessageActionsMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [onClose]);

  // Adjust position to keep menu on screen
  const adjustedPosition = {
    x: Math.min(position.x, window.innerWidth - 200),
    y: Math.min(position.y, window.innerHeight - 300)
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText(messageContent);
    setCopied(true);
    toast.success('Copied to clipboard');
    setTimeout(() => {
      setCopied(false);
      onClose();
    }, 500);
  };

  const handleAddToMemory = () => {
    // Store as persona fact
    fetch('http://localhost:8420/api/memory', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        fact: messageContent.slice(0, 200),
        category: 'persona',
        relevance_score: 0.85
      })
    }).then(() => {
      toast.success('Added to memory');
    }).catch(() => {
      toast.error('Failed to add to memory');
    });
    onClose();
    if (onAddToMemory) onAddToMemory();
  };

  const actions = [
    { icon: copied ? Check : Copy, label: 'Copy', onClick: handleCopy, show: true },
    { divider: true, show: !isUser },
    { icon: RotateCcw, label: 'Regenerate', onClick: () => { onRegenerate?.(); onClose(); }, show: !isUser && !!onRegenerate },
    { icon: Minus, label: 'Make shorter', onClick: () => { onMakeShorter?.(); onClose(); }, show: !isUser && !!onMakeShorter },
    { icon: Plus, label: 'Make longer', onClick: () => { onMakeLonger?.(); onClose(); }, show: !isUser && !!onMakeLonger },
    { icon: BookOpen, label: 'Explain more', onClick: () => { onExplainMore?.(); onClose(); }, show: !isUser && !!onExplainMore },
    { divider: true, show: true },
    { icon: Edit2, label: 'Edit', onClick: () => { onEdit?.(); onClose(); }, show: isUser && !!onEdit },
    { icon: Brain, label: 'Add to memory', onClick: handleAddToMemory, show: true },
    { icon: Trash2, label: 'Delete', onClick: () => { onDelete?.(); onClose(); }, show: !!onDelete, danger: true },
  ];

  return (
    <div
      ref={menuRef}
      className="fixed z-50 min-w-[180px] bg-popover border border-border rounded-lg shadow-lg py-1 animate-in fade-in-0 zoom-in-95"
      style={{ 
        left: adjustedPosition.x, 
        top: adjustedPosition.y 
      }}
    >
      {actions.filter(a => a.show).map((action, idx) => 
        'divider' in action && action.divider ? (
          <div key={`divider-${idx}`} className="h-px bg-border my-1" />
        ) : (
          <button
            key={action.label}
            onClick={action.onClick}
            className={cn(
              "w-full flex items-center gap-2.5 px-3 py-1.5 text-sm transition-colors text-left",
              action.danger 
                ? "text-destructive hover:bg-destructive/10" 
                : "hover:bg-muted"
            )}
          >
            {action.icon && <action.icon className="w-4 h-4" />}
            {action.label}
          </button>
        )
      )}
    </div>
  );
}
