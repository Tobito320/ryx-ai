/**
 * Document Card - Compact, clean card style
 * Minimal, informative, no overflow
 */

import { cn } from "@/lib/utils";
import { FileText, Clock, CheckCircle2, AlertTriangle, Image, FileType } from "lucide-react";

interface Document {
  name: string;
  path: string;
  type: string;
  category: string;
  modifiedAt?: string;
  priority?: string;
  deadlineDays?: number;
  status?: string;
}

interface DocumentCardProps {
  document: Document;
  selected?: boolean;
  onClick?: () => void;
}

const CATEGORY_COLORS: Record<string, string> = {
  familie: "border-l-purple-500",
  aok: "border-l-green-500",
  sparkasse: "border-l-blue-500",
  auto: "border-l-red-500",
  azubi: "border-l-orange-500",
  arbeit: "border-l-violet-500",
  other: "border-l-gray-500",
};

const TYPE_ICONS: Record<string, React.ReactNode> = {
  pdf: <FileText className="w-3.5 h-3.5" />,
  png: <Image className="w-3.5 h-3.5" />,
  jpg: <Image className="w-3.5 h-3.5" />,
  jpeg: <Image className="w-3.5 h-3.5" />,
  doc: <FileType className="w-3.5 h-3.5" />,
  docx: <FileType className="w-3.5 h-3.5" />,
  txt: <FileText className="w-3.5 h-3.5" />,
};

export function DocumentCard({ document, selected, onClick }: DocumentCardProps) {
  const isUrgent = document.deadlineDays !== undefined && document.deadlineDays < 7;
  const isCompleted = document.status === "completed";
  
  // Truncate filename properly
  const maxLen = 22;
  const ext = document.name.split('.').pop() || '';
  const nameWithoutExt = document.name.slice(0, document.name.length - ext.length - 1);
  const displayName = nameWithoutExt.length > maxLen 
    ? nameWithoutExt.slice(0, maxLen) + "…" 
    : nameWithoutExt;

  return (
    <div
      onClick={onClick}
      className={cn(
        "group cursor-pointer rounded-md p-2.5 transition-all duration-150",
        "bg-card border border-border/40 shadow-sm",
        "hover:shadow-md hover:border-border hover:bg-accent/30",
        "border-l-2",
        CATEGORY_COLORS[document.category] || CATEGORY_COLORS.other,
        selected && "ring-1 ring-primary shadow-md bg-accent/50",
        isUrgent && "bg-destructive/5",
      )}
    >
      {/* Top row: Icon + Type badge */}
      <div className="flex items-center justify-between mb-1.5">
        <div className={cn(
          "p-1.5 rounded",
          isCompleted ? "bg-green-500/10 text-green-500" : 
          isUrgent ? "bg-destructive/10 text-destructive" : 
          "bg-primary/10 text-primary"
        )}>
          {isCompleted ? <CheckCircle2 className="w-3.5 h-3.5" /> :
           isUrgent ? <AlertTriangle className="w-3.5 h-3.5" /> :
           TYPE_ICONS[document.type] || <FileText className="w-3.5 h-3.5" />}
        </div>
        <span className="text-[10px] uppercase font-medium text-muted-foreground bg-muted/50 px-1.5 py-0.5 rounded">
          {document.type}
        </span>
      </div>

      {/* Name - with proper truncation */}
      <h4 className="text-xs font-medium leading-snug mb-1 truncate" title={document.name}>
        {displayName}
      </h4>

      {/* Category - small */}
      <span className="text-[10px] text-muted-foreground capitalize">
        {document.category}
      </span>

      {/* Deadline if urgent */}
      {document.deadlineDays !== undefined && document.deadlineDays < 14 && (
        <div className={cn(
          "mt-1.5 flex items-center gap-1 text-[10px]",
          isUrgent ? "text-destructive" : "text-muted-foreground"
        )}>
          <Clock className="w-2.5 h-2.5" />
          <span>{document.deadlineDays}d</span>
        </div>
      )}
    </div>
  );
}
