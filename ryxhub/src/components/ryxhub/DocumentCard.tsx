/**
 * Document Card - Compact, clean card style
 * Minimal, informative, no overflow
 * Single click: select, Double click: open
 */

import { cn } from "@/lib/utils";
import { FileText, Clock, CheckCircle2, AlertTriangle, Image, FileType, File, ExternalLink } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

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
  onDoubleClick?: () => void;
  onPreview?: () => void;
}

const CATEGORY_COLORS: Record<string, string> = {
  familie: "border-l-purple-500",
  aok: "border-l-green-500",
  sparkasse: "border-l-blue-500",
  auto: "border-l-red-500",
  azubi: "border-l-orange-500",
  arbeit: "border-l-violet-500",
  sonstige: "border-l-gray-400",
  other: "border-l-gray-400",
};

const TYPE_ICONS: Record<string, { icon: React.ReactNode; color: string }> = {
  pdf: { icon: <FileText className="w-4 h-4" />, color: "text-red-500 bg-red-500/10" },
  png: { icon: <Image className="w-4 h-4" />, color: "text-green-500 bg-green-500/10" },
  jpg: { icon: <Image className="w-4 h-4" />, color: "text-green-500 bg-green-500/10" },
  jpeg: { icon: <Image className="w-4 h-4" />, color: "text-green-500 bg-green-500/10" },
  doc: { icon: <FileType className="w-4 h-4" />, color: "text-blue-500 bg-blue-500/10" },
  docx: { icon: <FileType className="w-4 h-4" />, color: "text-blue-500 bg-blue-500/10" },
  txt: { icon: <File className="w-4 h-4" />, color: "text-gray-500 bg-gray-500/10" },
};

export function DocumentCard({ document, selected, onClick, onDoubleClick, onPreview }: DocumentCardProps) {
  const isUrgent = document.deadlineDays !== undefined && document.deadlineDays < 7;
  const isCompleted = document.status === "completed";
  const typeInfo = TYPE_ICONS[document.type] || { icon: <File className="w-4 h-4" />, color: "text-gray-400 bg-gray-400/10" };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            onClick={onClick}
            onDoubleClick={onDoubleClick}
            className={cn(
              "cursor-pointer rounded p-2 transition-all duration-100",
              "bg-card/80 border border-border/30",
              "hover:border-border hover:bg-accent/20",
              "border-l-2 min-w-0 group relative",
              CATEGORY_COLORS[document.category] || CATEGORY_COLORS.other,
              selected && "ring-1 ring-primary bg-accent/40",
              isUrgent && "bg-destructive/5",
            )}
          >
            {/* Open button - visible on hover */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDoubleClick?.();
              }}
              className="absolute top-1 right-1 p-0.5 rounded bg-primary/10 opacity-0 group-hover:opacity-100 transition-opacity"
              title="Öffnen"
            >
              <ExternalLink className="w-3 h-3 text-primary" />
            </button>

            {/* Icon + Type Row */}
            <div className="flex items-center justify-between mb-1">
              <div className={cn("p-1 rounded", typeInfo.color)}>
                {isCompleted ? <CheckCircle2 className="w-4 h-4 text-green-500" /> :
                 isUrgent ? <AlertTriangle className="w-4 h-4 text-destructive" /> :
                 typeInfo.icon}
              </div>
              <span className="text-[9px] uppercase font-medium text-muted-foreground/70">
                {document.type}
              </span>
            </div>

            {/* Name - Truncated */}
            <p className="text-[11px] font-medium leading-tight truncate">
              {document.name.replace(/\.[^/.]+$/, "")}
            </p>

            {/* Deadline if urgent */}
            {document.deadlineDays !== undefined && document.deadlineDays < 14 && (
              <div className={cn(
                "mt-1 flex items-center gap-0.5 text-[9px]",
                isUrgent ? "text-destructive" : "text-muted-foreground"
              )}>
                <Clock className="w-2.5 h-2.5" />
                <span>{document.deadlineDays}d</span>
              </div>
            )}
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="max-w-xs">
          <p className="font-medium text-sm">{document.name}</p>
          <p className="text-xs text-muted-foreground capitalize">{document.category} • {document.type.toUpperCase()}</p>
          <p className="text-[10px] text-muted-foreground/70 mt-1">Doppelklick zum Öffnen</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
