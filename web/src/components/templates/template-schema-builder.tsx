"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Trash2, GripVertical, ChevronDown, ChevronUp } from "lucide-react";
import type { TemplateSchema, TemplateSchemaSection, TemplateSchemaField } from "@/types";

interface TemplateSchemaBuilderProps {
  schema: TemplateSchema;
  onChange: (schema: TemplateSchema) => void;
}

function emptyField(): TemplateSchemaField {
  return {
    key: `field_${Date.now()}`,
    label: "",
    type: "text",
    required: false,
  };
}

function emptySection(): TemplateSchemaSection {
  return {
    key: `section_${Date.now()}`,
    label: "",
    fields: [emptyField()],
    default_content: "",
  };
}

export function TemplateSchemaBuilder({
  schema,
  onChange,
}: TemplateSchemaBuilderProps) {
  const [expandedSections, setExpandedSections] = useState<Set<number>>(
    new Set([0])
  );

  const toggleSection = (index: number) => {
    const next = new Set(expandedSections);
    if (next.has(index)) {
      next.delete(index);
    } else {
      next.add(index);
    }
    setExpandedSections(next);
  };

  const addSection = () => {
    const updated: TemplateSchema = {
      ...schema,
      sections: [...schema.sections, emptySection()],
    };
    onChange(updated);
    setExpandedSections(new Set([...expandedSections, schema.sections.length]));
  };

  const removeSection = (index: number) => {
    const updated: TemplateSchema = {
      ...schema,
      sections: schema.sections.filter((_, i) => i !== index),
    };
    onChange(updated);
  };

  const updateSection = (
    index: number,
    updates: Partial<TemplateSchemaSection>
  ) => {
    const updated: TemplateSchema = {
      ...schema,
      sections: schema.sections.map((s, i) =>
        i === index ? { ...s, ...updates } : s
      ),
    };
    onChange(updated);
  };

  const addField = (sectionIndex: number) => {
    const section = schema.sections[sectionIndex];
    updateSection(sectionIndex, {
      fields: [...section.fields, emptyField()],
    });
  };

  const removeField = (sectionIndex: number, fieldIndex: number) => {
    const section = schema.sections[sectionIndex];
    updateSection(sectionIndex, {
      fields: section.fields.filter((_, i) => i !== fieldIndex),
    });
  };

  const updateField = (
    sectionIndex: number,
    fieldIndex: number,
    updates: Partial<TemplateSchemaField>
  ) => {
    const section = schema.sections[sectionIndex];
    updateSection(sectionIndex, {
      fields: section.fields.map((f, i) =>
        i === fieldIndex ? { ...f, ...updates } : f
      ),
    });
  };

  const updateAiInstructions = (instructions: string) => {
    onChange({ ...schema, ai_instructions: instructions });
  };

  return (
    <div className="space-y-4">
      {schema.sections.map((section, sIdx) => (
        <Card key={sIdx}>
          <CardHeader
            className="cursor-pointer"
            onClick={() => toggleSection(sIdx)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <GripVertical className="h-4 w-4 text-muted-foreground" />
                <CardTitle className="text-sm">
                  {section.label || `Section ${sIdx + 1}`}
                </CardTitle>
                <span className="text-xs text-muted-foreground">
                  ({section.fields.length} field
                  {section.fields.length !== 1 ? "s" : ""})
                </span>
              </div>
              <div className="flex items-center gap-1">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeSection(sIdx);
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5 text-destructive" />
                </Button>
                {expandedSections.has(sIdx) ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </div>
            </div>
          </CardHeader>

          {expandedSections.has(sIdx) && (
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Section Key</Label>
                  <Input
                    value={section.key}
                    onChange={(e) =>
                      updateSection(sIdx, { key: e.target.value })
                    }
                    placeholder="e.g., subjective"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Section Label</Label>
                  <Input
                    value={section.label}
                    onChange={(e) =>
                      updateSection(sIdx, { label: e.target.value })
                    }
                    placeholder="e.g., Subjective"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Default Content</Label>
                <Textarea
                  value={section.default_content || ""}
                  onChange={(e) =>
                    updateSection(sIdx, { default_content: e.target.value })
                  }
                  placeholder="Default content for this section (optional)"
                  className="min-h-[60px]"
                />
              </div>

              <div className="space-y-3">
                <Label className="text-sm font-medium">Fields</Label>
                {section.fields.map((field, fIdx) => (
                  <div
                    key={fIdx}
                    className="rounded-md border p-3 space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-muted-foreground">
                        Field {fIdx + 1}
                      </span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0"
                        onClick={() => removeField(sIdx, fIdx)}
                      >
                        <Trash2 className="h-3 w-3 text-destructive" />
                      </Button>
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                      <div className="space-y-1">
                        <Label className="text-xs">Key</Label>
                        <Input
                          value={field.key}
                          onChange={(e) =>
                            updateField(sIdx, fIdx, { key: e.target.value })
                          }
                          placeholder="field_key"
                          className="h-8 text-sm"
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">Label</Label>
                        <Input
                          value={field.label}
                          onChange={(e) =>
                            updateField(sIdx, fIdx, { label: e.target.value })
                          }
                          placeholder="Field Label"
                          className="h-8 text-sm"
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">Type</Label>
                        <Select
                          value={field.type}
                          onValueChange={(v) => {
                            if (v != null)
                              updateField(sIdx, fIdx, {
                                type: String(v) as TemplateSchemaField["type"],
                              });
                          }}
                        >
                          <SelectTrigger className="h-8 text-sm">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="text">Text</SelectItem>
                            <SelectItem value="textarea">Textarea</SelectItem>
                            <SelectItem value="checklist">Checklist</SelectItem>
                            <SelectItem value="select">Select</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={field.required || false}
                          onChange={(e) =>
                            updateField(sIdx, fIdx, {
                              required: e.target.checked,
                            })
                          }
                          className="rounded border-input"
                        />
                        <Label className="text-xs">Required</Label>
                      </div>
                    </div>

                    <div className="space-y-1">
                      <Label className="text-xs">AI Prompt (optional)</Label>
                      <Input
                        value={field.ai_prompt || ""}
                        onChange={(e) =>
                          updateField(sIdx, fIdx, {
                            ai_prompt: e.target.value || undefined,
                          })
                        }
                        placeholder="Prompt for AI auto-fill"
                        className="h-8 text-sm"
                      />
                    </div>

                    {(field.type === "checklist" || field.type === "select") && (
                      <div className="space-y-1">
                        <Label className="text-xs">
                          Options (comma-separated)
                        </Label>
                        <Input
                          value={(field.options || []).join(", ")}
                          onChange={(e) =>
                            updateField(sIdx, fIdx, {
                              options: e.target.value
                                .split(",")
                                .map((o) => o.trim())
                                .filter(Boolean),
                            })
                          }
                          placeholder="Option 1, Option 2, Option 3"
                          className="h-8 text-sm"
                        />
                      </div>
                    )}
                  </div>
                ))}

                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => addField(sIdx)}
                  className="w-full"
                >
                  <Plus className="h-3.5 w-3.5 mr-1" />
                  Add Field
                </Button>
              </div>
            </CardContent>
          )}
        </Card>
      ))}

      <Button
        type="button"
        variant="outline"
        onClick={addSection}
        className="w-full"
      >
        <Plus className="h-4 w-4 mr-2" />
        Add Section
      </Button>

      <div className="space-y-2">
        <Label>AI Instructions (optional)</Label>
        <Textarea
          value={schema.ai_instructions || ""}
          onChange={(e) => updateAiInstructions(e.target.value)}
          placeholder="Special instructions for AI when filling this template, e.g., 'Focus on dermatological terminology'"
          className="min-h-[80px]"
        />
      </div>
    </div>
  );
}
