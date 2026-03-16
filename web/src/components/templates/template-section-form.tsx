"use client";

import { useState } from "react";
import { useAutoComplete } from "@/hooks/use-templates";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkles, Loader2 } from "lucide-react";
import type { TemplateSchemaSection } from "@/types";

interface TemplateSectionFormProps {
  section: TemplateSchemaSection;
  templateId: string;
  values: Record<string, string>;
  onChange: (key: string, value: string) => void;
  encounterContext?: Record<string, unknown>;
}

export function TemplateSectionForm({
  section,
  templateId,
  values,
  onChange,
  encounterContext,
}: TemplateSectionFormProps) {
  const autoComplete = useAutoComplete();
  const [loadingField, setLoadingField] = useState<string | null>(null);

  const handleAutoComplete = async (fieldKey: string) => {
    setLoadingField(fieldKey);
    try {
      const result = await autoComplete.mutateAsync({
        templateId,
        data: {
          section_key: section.key,
          field_key: fieldKey,
          encounter_context: encounterContext || {},
          partial_content: values[fieldKey] || "",
        },
      });
      onChange(fieldKey, result.content);
    } catch {
      // Error handled by mutation
    } finally {
      setLoadingField(null);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{section.label}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {section.fields.map((field) => (
          <div key={field.key} className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor={`${section.key}-${field.key}`}>
                {field.label}
                {field.required && (
                  <span className="text-destructive ml-1">*</span>
                )}
              </Label>
              {field.ai_prompt && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs"
                  disabled={loadingField === field.key}
                  onClick={() => handleAutoComplete(field.key)}
                >
                  {loadingField === field.key ? (
                    <>
                      <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-3 w-3 mr-1" />
                      AI Fill
                    </>
                  )}
                </Button>
              )}
            </div>

            {field.type === "text" && (
              <Input
                id={`${section.key}-${field.key}`}
                value={values[field.key] || ""}
                onChange={(e) => onChange(field.key, e.target.value)}
                placeholder={`Enter ${field.label.toLowerCase()}`}
              />
            )}

            {field.type === "textarea" && (
              <Textarea
                id={`${section.key}-${field.key}`}
                value={values[field.key] || ""}
                onChange={(e) => onChange(field.key, e.target.value)}
                placeholder={`Enter ${field.label.toLowerCase()}`}
                className="min-h-[100px]"
              />
            )}

            {field.type === "checklist" && field.options && (
              <div className="grid grid-cols-2 gap-2">
                {field.options.map((option) => {
                  const currentValues = (values[field.key] || "")
                    .split(",")
                    .filter(Boolean);
                  const isChecked = currentValues.includes(option);
                  return (
                    <label
                      key={option}
                      className="flex items-center gap-2 text-sm cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => {
                          const updated = isChecked
                            ? currentValues.filter((v) => v !== option)
                            : [...currentValues, option];
                          onChange(field.key, updated.join(","));
                        }}
                        className="rounded border-input"
                      />
                      {option}
                    </label>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
