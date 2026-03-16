"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useCreateTemplate } from "@/hooks/use-templates";
import { TemplateSchemaBuilder } from "@/components/templates/template-schema-builder";
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
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";
import { SPECIALTY_LABELS } from "@/lib/constants";
import type {
  TemplateSchema,
  MedicalSpecialty,
  NoteType,
  TemplateVisibility,
  TemplateStatus,
} from "@/types";

const templateFormSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional(),
  specialty: z.string().min(1, "Specialty is required"),
  note_type: z.string().min(1, "Note type is required"),
  visibility: z.string().optional(),
  status: z.string().optional(),
  tags: z.string().optional(),
});

type TemplateFormData = z.infer<typeof templateFormSchema>;

export function NewTemplateForm() {
  const router = useRouter();
  const createTemplate = useCreateTemplate();
  const [error, setError] = useState<string | null>(null);
  const [schema, setSchema] = useState<TemplateSchema>({
    sections: [
      {
        key: "subjective",
        label: "Subjective",
        fields: [
          { key: "chief_complaint", label: "Chief Complaint", type: "text", required: true },
          {
            key: "hpi",
            label: "History of Present Illness",
            type: "textarea",
            required: true,
            ai_prompt: "Generate HPI based on chief complaint",
          },
        ],
      },
      {
        key: "objective",
        label: "Objective",
        fields: [
          {
            key: "physical_exam",
            label: "Physical Examination",
            type: "textarea",
            required: true,
          },
        ],
      },
      {
        key: "assessment",
        label: "Assessment",
        fields: [
          { key: "assessment", label: "Assessment", type: "textarea", required: true },
        ],
      },
      {
        key: "plan",
        label: "Plan",
        fields: [
          { key: "plan", label: "Plan", type: "textarea", required: true },
        ],
      },
    ],
  });

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<TemplateFormData>({
    resolver: zodResolver(templateFormSchema),
    defaultValues: {
      specialty: "general",
      note_type: "soap",
      visibility: "private",
      status: "draft",
    },
  });

  const onSubmit = async (data: TemplateFormData) => {
    setError(null);
    try {
      const tags = data.tags
        ? data.tags
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean)
        : [];

      const template = await createTemplate.mutateAsync({
        name: data.name,
        description: data.description || "",
        specialty: data.specialty as MedicalSpecialty,
        note_type: data.note_type as NoteType,
        visibility: (data.visibility || "private") as TemplateVisibility,
        status: (data.status || "draft") as TemplateStatus,
        tags,
        schema,
      });
      router.push(`/templates/${template.id}`);
    } catch {
      setError("Failed to create template. Please try again.");
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/templates">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <h1 className="text-2xl font-bold">New Template</h1>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Basic Info */}
        <Card>
          <CardHeader>
            <CardTitle>Template Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                {...register("name")}
                placeholder="e.g., Primary Care - Annual Physical"
              />
              {errors.name && (
                <p className="text-sm text-destructive">{errors.name.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                {...register("description")}
                placeholder="Describe what this template is used for..."
                className="min-h-[80px]"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Specialty</Label>
                <Select
                  defaultValue="general"
                  onValueChange={(v) => {
                    if (v != null) setValue("specialty", String(v));
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select specialty" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(SPECIALTY_LABELS).map(([value, label]) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.specialty && (
                  <p className="text-sm text-destructive">
                    {errors.specialty.message}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label>Note Type</Label>
                <Select
                  defaultValue="soap"
                  onValueChange={(v) => {
                    if (v != null) setValue("note_type", String(v));
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select note type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="soap">SOAP</SelectItem>
                    <SelectItem value="free_text">Free Text</SelectItem>
                    <SelectItem value="h_and_p">H&P</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Visibility</Label>
                <Select
                  defaultValue="private"
                  onValueChange={(v) => {
                    if (v != null) setValue("visibility", String(v));
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select visibility" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="private">Private</SelectItem>
                    <SelectItem value="practice">Practice</SelectItem>
                    <SelectItem value="public">Public (Marketplace)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Status</Label>
                <Select
                  defaultValue="draft"
                  onValueChange={(v) => {
                    if (v != null) setValue("status", String(v));
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="draft">Draft</SelectItem>
                    <SelectItem value="published">Published</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="tags">Tags (comma-separated)</Label>
              <Input
                id="tags"
                {...register("tags")}
                placeholder="e.g., follow-up, initial-visit, annual-physical"
              />
            </div>
          </CardContent>
        </Card>

        {/* Schema Builder */}
        <Card>
          <CardHeader>
            <CardTitle>Template Schema</CardTitle>
          </CardHeader>
          <CardContent>
            <TemplateSchemaBuilder schema={schema} onChange={setSchema} />
          </CardContent>
        </Card>

        {/* Submit */}
        <div className="flex justify-end gap-2">
          <Link href="/templates">
            <Button variant="outline" type="button">
              Cancel
            </Button>
          </Link>
          <Button type="submit" disabled={createTemplate.isPending}>
            {createTemplate.isPending && (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            )}
            Create Template
          </Button>
        </div>
      </form>
    </div>
  );
}
