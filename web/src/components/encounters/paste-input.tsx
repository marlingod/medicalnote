"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { MAX_PASTE_LENGTH } from "@/lib/constants";

const pasteSchema = z.object({
  text: z
    .string()
    .min(10, "Text must be at least 10 characters")
    .max(MAX_PASTE_LENGTH, `Text must be under ${MAX_PASTE_LENGTH.toLocaleString()} characters`),
});

type PasteFormData = z.infer<typeof pasteSchema>;

interface PasteInputProps {
  onSubmit: (text: string) => void;
  isSubmitting?: boolean;
}

export function PasteInput({ onSubmit, isSubmitting }: PasteInputProps) {
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<PasteFormData>({
    resolver: zodResolver(pasteSchema),
  });

  const textValue = watch("text", "");

  return (
    <Card>
      <CardContent className="py-6">
        <form onSubmit={handleSubmit((data) => onSubmit(data.text))} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="paste-text">Paste Clinical Notes</Label>
            <Textarea
              id="paste-text"
              placeholder="Paste your clinical notes here..."
              className="min-h-[200px] font-mono text-sm"
              {...register("text")}
            />
            <div className="flex justify-between">
              {errors.text && (
                <p className="text-sm text-destructive">{errors.text.message}</p>
              )}
              <p className="text-sm text-muted-foreground ml-auto">
                {textValue.length.toLocaleString()} / {MAX_PASTE_LENGTH.toLocaleString()}
              </p>
            </div>
          </div>
          <Button type="submit" disabled={isSubmitting} className="w-full">
            {isSubmitting ? "Submitting..." : "Submit Notes"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
