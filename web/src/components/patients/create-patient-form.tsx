"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useCreatePatient } from "@/hooks/use-patients";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useState } from "react";

const createPatientSchema = z.object({
  first_name: z.string().min(1, "First name is required"),
  last_name: z.string().min(1, "Last name is required"),
  date_of_birth: z.string().min(1, "Date of birth is required"),
  email: z.string().email("Invalid email").optional().or(z.literal("")),
  phone: z.string().optional().or(z.literal("")),
  language_preference: z.string().optional(),
});

type CreatePatientFormData = z.infer<typeof createPatientSchema>;

interface CreatePatientFormProps {
  onSuccess?: () => void;
}

export function CreatePatientForm({ onSuccess }: CreatePatientFormProps) {
  const createPatient = useCreatePatient();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<CreatePatientFormData>({
    resolver: zodResolver(createPatientSchema),
    defaultValues: { language_preference: "en" },
  });

  const onSubmit = async (data: CreatePatientFormData) => {
    setError(null);
    try {
      await createPatient.mutateAsync(data);
      onSuccess?.();
    } catch {
      setError("Failed to create patient. Please try again.");
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="first_name">First Name</Label>
          <Input id="first_name" {...register("first_name")} />
          {errors.first_name && (
            <p className="text-sm text-destructive">{errors.first_name.message}</p>
          )}
        </div>
        <div className="space-y-2">
          <Label htmlFor="last_name">Last Name</Label>
          <Input id="last_name" {...register("last_name")} />
          {errors.last_name && (
            <p className="text-sm text-destructive">{errors.last_name.message}</p>
          )}
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="date_of_birth">Date of Birth</Label>
        <Input id="date_of_birth" type="date" {...register("date_of_birth")} />
        {errors.date_of_birth && (
          <p className="text-sm text-destructive">{errors.date_of_birth.message}</p>
        )}
      </div>
      <div className="space-y-2">
        <Label htmlFor="patient-email">Email (optional)</Label>
        <Input id="patient-email" type="email" {...register("email")} />
      </div>
      <div className="space-y-2">
        <Label htmlFor="patient-phone">Phone (optional)</Label>
        <Input id="patient-phone" type="tel" placeholder="+15551234567" {...register("phone")} />
      </div>
      <div className="space-y-2">
        <Label>Language Preference</Label>
        <Select defaultValue="en" onValueChange={(v) => { if (v != null) setValue("language_preference", String(v)); }}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="en">English</SelectItem>
            <SelectItem value="es">Spanish</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <Button type="submit" className="w-full" disabled={createPatient.isPending}>
        {createPatient.isPending ? "Creating..." : "Add Patient"}
      </Button>
    </form>
  );
}
