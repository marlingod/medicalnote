"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useTemplate, useUpdateTemplate } from "@/hooks/use-templates";
import { TemplateSchemaBuilder } from "@/components/templates/template-schema-builder";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
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

interface EditTemplateFormProps {
  templateId: string;
}

export function EditTemplateForm({ templateId }: EditTemplateFormProps) {
  const router = useRouter();
  const { data: template, isLoading: templateLoading } = useTemplate(templateId);
  const updateTemplate = useUpdateTemplate();
  const [error, setError] = useState<string | null>(null);
  const [schema, setSchema] = useState<TemplateSchema>({ sections: [] });
  const [initialized, setInitialized] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors },
  } = useForm<TemplateFormData>({
    resolver: zodResolver(templateFormSchema),
  });

  useEffect(() => {
    if (template && !initialized) {
      reset({
        name: template.name,
        description: template.description,
        specialty: template.specialty,
        note_type: template.note_type,
        visibility: template.visibility,
        status: template.status,
        tags: template.tags.join(", "),
      });
      setSchema(template.schema);
      setInitialized(true);
    }
  }, [template, initialized, reset]);

  const onSubmit = async (data: TemplateFormData) => {
    setError(null);
    try {
      const tags = data.tags
        ? data.tags
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean)
        : [];

      await updateTemplate.mutateAsync({
        id: templateId,
        data: {
          name: data.name,
          description: data.description || "",
          specialty: data.specialty as MedicalSpecialty,
          note_type: data.note_type as NoteType,
          visibility: (data.visibility || "private") as TemplateVisibility,
          status: (data.status || "draft") as TemplateStatus,
          tags,
          schema,
        },
      });
      router.push(`/templates/${templateId}`);
    } catch {
      setError("Failed to update template. Please try again.");
    }
  };

  if (templateLoading) {
    return (
      <div className="max-w-3xl mx-auto space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!template) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-muted-foreground">Template not found.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Link href={`/templates/${templateId}`}>
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <h1 className="text-2xl font-bold">Edit Template</h1>
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
                  value={template.specialty}
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
              </div>

              <div className="space-y-2">
                <Label>Note Type</Label>
                <Select
                  value={template.note_type}
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
                  value={template.visibility}
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
                  value={template.status}
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
                    <SelectItem value="archived">Archived</SelectItem>
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
          <Link href={`/templates/${templateId}`}>
            <Button variant="outline" type="button">
              Cancel
            </Button>
          </Link>
          <Button type="submit" disabled={updateTemplate.isPending}>
            {updateTemplate.isPending && (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            )}
            Save Changes
          </Button>
        </div>
      </form>
    </div>
  );
}
