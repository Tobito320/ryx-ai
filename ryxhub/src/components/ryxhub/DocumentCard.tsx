/**
 * Document Card - Holographic floating card style
 * Minimal, clean, informative
 */

import { cn } from "@/lib/utils";
import { FileText, Clock, CheckCircle2, AlertTriangle } from "lucide-react";
import { Badge } from "@/components/ui/badge";

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

export function DocumentCard({ document, selected, onClick }: DocumentCardProps) {
  const isUrgent = document.deadlineDays !== undefined && document.deadlineDays < 7;
  const isCompleted = document.status === "completed";
  
  // Shorten filename for display
  const displayName = document.name.length > 30
    ? document.name.substring(0, 27) + "..."
    : document.name;

  return (
    <div
      onClick={onClick}
      className={cn(
        "group relative cursor-pointer rounded-lg p-4 transition-all duration-200",
        "bg-card border border-border/50 shadow-sm",
        "hover:shadow-lg hover:-translate-y-1 hover:border-border",
        "border-l-4",
        CATEGORY_COLORS[document.category] || CATEGORY_COLORS.other,
        selected && "ring-2 ring-primary shadow-lg -translate-y-1",
        isUrgent && "bg-destructive/5",
      )}
    >
      {/* Icon */}
      <div className="flex items-start gap-3 mb-3">
        <div className={cn(
          "p-2 rounded-md",
          isCompleted ? "bg-green-500/10" : "bg-primary/10"
        )}>
          {isCompleted ? (
            <CheckCircle2 className="w-4 h-4 text-green-500" />
          ) : isUrgent ? (
            <AlertTriangle className="w-4 h-4 text-destructive" />
          ) : (
            <FileText className="w-4 h-4 text-primary" />
          )}
        </div>
      </div>

      {/* Name */}
      <h4 className="text-sm font-medium leading-tight mb-2 line-clamp-2">
        {displayName}
      </h4>

      {/* Category */}
      <Badge 
        variant="secondary" 
        className="text-xs capitalize"
      >
        {document.category}
      </Badge>

      {/* Deadline if exists */}
      {document.deadlineDays !== undefined && (
        <div className={cn(
          "mt-2 flex items-center gap-1 text-xs",
          isUrgent ? "text-destructive" : "text-muted-foreground"
        )}>
          <Clock className="w-3 h-3" />
          <span>{document.deadlineDays} Tage</span>
        </div>
      )}

      {/* Hover overlay */}
      <div className="absolute inset-0 rounded-lg bg-primary/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
    </div>
  );
}
