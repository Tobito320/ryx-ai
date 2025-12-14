import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { MessageVariant } from "@/types/ryxhub";

interface VariantSelectorProps {
  originalTimestamp: string;
  variants: MessageVariant[];
  activeVariant: number; // 0 = original, 1+ = variant index
  onSelectVariant: (index: number) => void;
}

export function VariantSelector({ 
  originalTimestamp,
  variants, 
  activeVariant, 
  onSelectVariant 
}: VariantSelectorProps) {
  const totalCount = variants.length + 1; // +1 for original
  const currentIndex = activeVariant;

  const handlePrev = () => {
    if (currentIndex > 0) {
      onSelectVariant(currentIndex - 1);
    }
  };

  const handleNext = () => {
    if (currentIndex < totalCount - 1) {
      onSelectVariant(currentIndex + 1);
    }
  };

  // Get label for current variant
  const getVariantLabel = (index: number) => {
    if (index === 0) return "v1";
    const variant = variants[index - 1];
    if (variant.modifier) {
      return `v${index + 1} (${variant.modifier})`;
    }
    return `v${index + 1}`;
  };

  if (variants.length === 0) {
    return null;
  }

  return (
    <div className="flex items-center gap-1 text-[10px] text-muted-foreground select-none">
      <Button
        variant="ghost"
        size="icon"
        className="h-5 w-5 p-0 hover:bg-muted"
        onClick={handlePrev}
        disabled={currentIndex === 0}
      >
        <ChevronLeft className="w-3 h-3" />
      </Button>

      <div className="flex items-center gap-0.5">
        {Array.from({ length: totalCount }).map((_, i) => (
          <button
            key={i}
            onClick={() => onSelectVariant(i)}
            className={cn(
              "min-w-[18px] h-5 px-1 rounded text-[10px] transition-colors",
              currentIndex === i
                ? "bg-primary/20 text-primary font-medium"
                : "hover:bg-muted text-muted-foreground"
            )}
            title={getVariantLabel(i)}
          >
            {i + 1}
          </button>
        ))}
      </div>

      <Button
        variant="ghost"
        size="icon"
        className="h-5 w-5 p-0 hover:bg-muted"
        onClick={handleNext}
        disabled={currentIndex === totalCount - 1}
      >
        <ChevronRight className="w-3 h-3" />
      </Button>

      <span className="ml-1 opacity-60">
        {currentIndex + 1}/{totalCount}
      </span>
    </div>
  );
}
