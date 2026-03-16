"use client";

import { useJobStatus } from "@/hooks/use-job-status";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { CheckCircle2, Loader2, XCircle, Circle } from "lucide-react";
import type { EncounterStatus } from "@/types";

interface ProcessingStatusProps {
  encounterId: string;
  currentStatus: EncounterStatus;
  onStatusChange?: (status: EncounterStatus) => void;
}

const steps: { key: EncounterStatus; label: string }[] = [
  { key: "uploading", label: "Uploading" },
  { key: "transcribing", label: "Transcribing Audio" },
  { key: "generating_note", label: "Generating SOAP Note" },
  { key: "generating_summary", label: "Generating Summary" },
  { key: "ready_for_review", label: "Ready for Review" },
];

const statusOrder: EncounterStatus[] = [
  "uploading",
  "transcribing",
  "generating_note",
  "generating_summary",
  "ready_for_review",
];

const failedStatuses: EncounterStatus[] = [
  "transcription_failed",
  "note_generation_failed",
  "summary_generation_failed",
];

export function ProcessingStatus({
  encounterId,
  currentStatus,
  onStatusChange,
}: ProcessingStatusProps) {
  const isProcessing =
    !failedStatuses.includes(currentStatus) &&
    currentStatus !== "ready_for_review" &&
    currentStatus !== "approved" &&
    currentStatus !== "delivered";

  const { status: wsStatus } = useJobStatus(encounterId, {
    enabled: isProcessing,
    onStatusChange,
  });

  const activeStatus = wsStatus || currentStatus;
  const currentIndex = statusOrder.indexOf(activeStatus);
  const isFailed = failedStatuses.includes(activeStatus);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Processing Status</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {steps.map((step, index) => {
            const isComplete = currentIndex > index;
            const isActive = currentIndex === index;
            const isFailedAtStep = isFailed && currentIndex === index;

            return (
              <div key={step.key} className="flex items-center gap-3">
                {isComplete ? (
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                ) : isFailedAtStep ? (
                  <XCircle className="h-5 w-5 text-red-600" />
                ) : isActive ? (
                  <Loader2 className="h-5 w-5 text-primary animate-spin" />
                ) : (
                  <Circle className="h-5 w-5 text-muted-foreground/40" />
                )}
                <span
                  className={cn(
                    "text-sm",
                    isComplete && "text-green-700 font-medium",
                    isActive && !isFailedAtStep && "text-primary font-medium",
                    isFailedAtStep && "text-red-700 font-medium",
                    !isComplete && !isActive && "text-muted-foreground"
                  )}
                >
                  {step.label}
                  {isFailedAtStep && " - Failed"}
                </span>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
