"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useUpdateNote, useApproveNote } from "@/hooks/use-notes";
import type { ClinicalNote } from "@/types";
import { CheckCircle2, Edit3, Save } from "lucide-react";
import { useState } from "react";

const noteSchema = z.object({
  subjective: z.string().min(1, "Subjective is required"),
  objective: z.string().min(1, "Objective is required"),
  assessment: z.string().min(1, "Assessment is required"),
  plan: z.string().min(1, "Plan is required"),
});

type NoteFormData = z.infer<typeof noteSchema>;

interface NoteEditorProps {
  note: ClinicalNote;
  encounterId: string;
  onApproved?: () => void;
}

export function NoteEditor({ note, encounterId, onApproved }: NoteEditorProps) {
  const [isEditing, setIsEditing] = useState(false);
  const updateNote = useUpdateNote();
  const approveNote = useApproveNote();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<NoteFormData>({
    resolver: zodResolver(noteSchema),
    defaultValues: {
      subjective: note.subjective,
      objective: note.objective,
      assessment: note.assessment,
      plan: note.plan,
    },
  });

  const onSave = async (data: NoteFormData) => {
    await updateNote.mutateAsync({
      encounterId,
      data: { ...data, doctor_edited: true },
    });
    setIsEditing(false);
  };

  const onApprove = async () => {
    await approveNote.mutateAsync(encounterId);
    onApproved?.();
  };

  const isApproved = !!note.approved_at;

  const soapSections = [
    { key: "subjective" as const, label: "Subjective", field: "subjective" as const },
    { key: "objective" as const, label: "Objective", field: "objective" as const },
    { key: "assessment" as const, label: "Assessment", field: "assessment" as const },
    { key: "plan" as const, label: "Plan", field: "plan" as const },
  ];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="space-y-1">
          <CardTitle className="text-lg">SOAP Note</CardTitle>
          <div className="flex gap-2">
            {note.ai_generated && <Badge variant="secondary">AI Generated</Badge>}
            {note.doctor_edited && <Badge variant="outline">Doctor Edited</Badge>}
            {isApproved && <Badge className="bg-green-100 text-green-800">Approved</Badge>}
          </div>
        </div>
        {!isApproved && (
          <div className="flex gap-2">
            {!isEditing ? (
              <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
                <Edit3 className="mr-2 h-4 w-4" />
                Edit
              </Button>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  reset();
                  setIsEditing(false);
                }}
              >
                Cancel
              </Button>
            )}
          </div>
        )}
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSave)} className="space-y-4">
          {soapSections.map((section) => (
            <div key={section.key} className="space-y-2">
              <Label className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {section.label}
              </Label>
              {isEditing ? (
                <>
                  <Textarea
                    className="min-h-[80px]"
                    {...register(section.field)}
                  />
                  {errors[section.field] && (
                    <p className="text-sm text-destructive">
                      {errors[section.field]?.message}
                    </p>
                  )}
                </>
              ) : (
                <p className="text-sm whitespace-pre-wrap">{note[section.field]}</p>
              )}
              <Separator />
            </div>
          ))}

          {(note.icd10_codes.length > 0 || note.cpt_codes.length > 0) && (
            <div className="flex gap-8">
              {note.icd10_codes.length > 0 && (
                <div>
                  <Label className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                    ICD-10 Codes
                  </Label>
                  <div className="flex gap-1 mt-1">
                    {note.icd10_codes.map((code) => (
                      <Badge key={code} variant="outline">{code}</Badge>
                    ))}
                  </div>
                </div>
              )}
              {note.cpt_codes.length > 0 && (
                <div>
                  <Label className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                    CPT Codes
                  </Label>
                  <div className="flex gap-1 mt-1">
                    {note.cpt_codes.map((code) => (
                      <Badge key={code} variant="outline">{code}</Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {isEditing && isDirty && (
            <Button type="submit" disabled={updateNote.isPending}>
              <Save className="mr-2 h-4 w-4" />
              {updateNote.isPending ? "Saving..." : "Save Changes"}
            </Button>
          )}
        </form>

        {!isApproved && !isEditing && (
          <div className="mt-6 pt-4 border-t">
            <Button
              onClick={onApprove}
              disabled={approveNote.isPending}
              className="w-full"
              size="lg"
            >
              <CheckCircle2 className="mr-2 h-5 w-5" />
              {approveNote.isPending ? "Approving..." : "Approve Note"}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
