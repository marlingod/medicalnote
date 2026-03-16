"use client";

import { usePatient, useUpdatePatient } from "@/hooks/use-patients";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";

interface PatientDetailProps {
  patientId: string;
}

export function PatientDetail({ patientId }: PatientDetailProps) {
  const { data: patient, isLoading } = usePatient(patientId);

  if (isLoading) {
    return <Skeleton className="h-64 w-full" />;
  }

  if (!patient) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          Patient not found.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <div className="flex items-center gap-4">
        <Link href="/patients">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <h1 className="text-2xl font-bold">
          {patient.first_name} {patient.last_name}
        </h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Patient Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Date of Birth</p>
              <p className="font-medium">
                {format(new Date(patient.date_of_birth), "MMMM d, yyyy")}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">Language</p>
              <p className="font-medium">{patient.language_preference.toUpperCase()}</p>
            </div>
            {patient.email && (
              <div>
                <p className="text-muted-foreground">Email</p>
                <p className="font-medium">{patient.email}</p>
              </div>
            )}
            {patient.phone && (
              <div>
                <p className="text-muted-foreground">Phone</p>
                <p className="font-medium">{patient.phone}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
