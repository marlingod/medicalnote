import { Badge } from "@/components/ui/badge";
import { ENCOUNTER_STATUSES } from "@/lib/constants";
import type { EncounterStatus } from "@/types";
import { cn } from "@/lib/utils";

const statusVariants: Record<string, string> = {
  uploading: "bg-blue-100 text-blue-800",
  transcribing: "bg-yellow-100 text-yellow-800",
  generating_note: "bg-yellow-100 text-yellow-800",
  generating_summary: "bg-yellow-100 text-yellow-800",
  ready_for_review: "bg-orange-100 text-orange-800",
  approved: "bg-green-100 text-green-800",
  delivered: "bg-green-200 text-green-900",
  transcription_failed: "bg-red-100 text-red-800",
  note_generation_failed: "bg-red-100 text-red-800",
  summary_generation_failed: "bg-red-100 text-red-800",
};

export function StatusBadge({ status }: { status: EncounterStatus }) {
  const label = ENCOUNTER_STATUSES[status] || status;
  return (
    <Badge variant="outline" className={cn("font-medium", statusVariants[status])}>
      {label}
    </Badge>
  );
}
