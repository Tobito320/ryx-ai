/**
 * Form Filling Modal - AI-powered form field suggestions
 * 
 * Shows detected form fields and AI-suggested values
 * User can review and apply suggestions
 */

import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Check, X, RefreshCw } from "lucide-react";

interface FormField {
  id: string;
  name: string;
  type: string;
  label?: string;
  placeholder?: string;
  required?: boolean;
}

interface FormSuggestion {
  fieldId: string;
  suggestedValue: string;
  confidence: number;
  reason?: string;
}

interface FormFillingModalProps {
  isOpen: boolean;
  onClose: () => void;
  fields: FormField[];
  suggestions: FormSuggestion[];
  onApply: (values: Record<string, string>) => void;
  onRefresh?: () => Promise<void>;
  documentName?: string;
}

export function FormFillingModal({
  isOpen,
  onClose,
  fields,
  suggestions,
  onApply,
  onRefresh,
  documentName,
}: FormFillingModalProps) {
  // Map suggestions to field values
  const initialValues: Record<string, string> = {};
  suggestions.forEach((s) => {
    initialValues[s.fieldId] = s.suggestedValue;
  });

  const [values, setValues] = useState<Record<string, string>>(initialValues);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleValueChange = (fieldId: string, value: string) => {
    setValues((prev) => ({ ...prev, [fieldId]: value }));
  };

  const handleApply = () => {
    onApply(values);
    onClose();
  };

  const handleRefresh = async () => {
    if (onRefresh) {
      setIsRefreshing(true);
      try {
        await onRefresh();
      } finally {
        setIsRefreshing(false);
      }
    }
  };

  const getSuggestionForField = (fieldId: string) => {
    return suggestions.find((s) => s.fieldId === fieldId);
  };

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.8) {
      return <Badge className="bg-green-500">Hoch</Badge>;
    } else if (confidence >= 0.5) {
      return <Badge className="bg-yellow-500">Mittel</Badge>;
    }
    return <Badge className="bg-red-500">Niedrig</Badge>;
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-purple-500" />
            AI Formular-Ausfüllung
          </DialogTitle>
          <DialogDescription>
            {documentName && (
              <span className="font-medium">{documentName}</span>
            )}
            <br />
            KI-generierte Vorschläge für {fields.length} Felder. Überprüfen und
            anpassen Sie die Werte.
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="max-h-[50vh] pr-4">
          <div className="space-y-4">
            {fields.map((field) => {
              const suggestion = getSuggestionForField(field.id);
              return (
                <div
                  key={field.id}
                  className="p-3 rounded-lg bg-zinc-900/50 border border-zinc-800"
                >
                  <div className="flex items-center justify-between mb-2">
                    <Label htmlFor={field.id} className="text-sm font-medium">
                      {field.label || field.name}
                      {field.required && (
                        <span className="text-red-500 ml-1">*</span>
                      )}
                    </Label>
                    {suggestion && getConfidenceBadge(suggestion.confidence)}
                  </div>

                  <Input
                    id={field.id}
                    type={field.type === "password" ? "password" : "text"}
                    value={values[field.id] || ""}
                    onChange={(e) => handleValueChange(field.id, e.target.value)}
                    placeholder={field.placeholder || `Wert für ${field.name}`}
                    className="bg-zinc-800 border-zinc-700"
                  />

                  {suggestion?.reason && (
                    <p className="text-xs text-zinc-500 mt-1">
                      💡 {suggestion.reason}
                    </p>
                  )}
                </div>
              );
            })}

            {fields.length === 0 && (
              <div className="text-center py-8 text-zinc-500">
                Keine Formularfelder erkannt.
              </div>
            )}
          </div>
        </ScrollArea>

        <DialogFooter className="flex gap-2">
          {onRefresh && (
            <Button
              variant="outline"
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw
                className={`w-4 h-4 mr-2 ${isRefreshing ? "animate-spin" : ""}`}
              />
              Neu analysieren
            </Button>
          )}
          <Button variant="ghost" onClick={onClose}>
            <X className="w-4 h-4 mr-2" />
            Abbrechen
          </Button>
          <Button onClick={handleApply} disabled={fields.length === 0}>
            <Check className="w-4 h-4 mr-2" />
            Anwenden
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default FormFillingModal;
