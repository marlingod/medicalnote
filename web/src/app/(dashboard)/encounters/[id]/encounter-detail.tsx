"use client";

import { useEncounter, useTranscript } from "@/hooks/use-encounters";
import { useNote } from "@/hooks/use-notes";
import { useSummary } from "@/hooks/use-summaries";
import { useQueryClient } from "@tanstack/react-query";
import { encounterKeys } from "@/hooks/use-encounters";
import { ProcessingStatus } from "@/components/encounters/processing-status";
import { NoteEditor } from "@/components/notes/note-editor";
import { SummaryPreview } from "@/components/encounters/summary-preview";
import { QualityScoreDetail } from "@/components/quality/quality-score-detail";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";
import type { EncounterStatus } from "@/types";

interface EncounterDetailProps {
  encounterId: string;
}

const completedStatuses: EncounterStatus[] = [
  "ready_for_review",
  "approved",
  "delivered",
];

const failedStatuses: EncounterStatus[] = [
  "transcription_failed",
  "note_generation_failed",
  "summary_generation_failed",
];

export function EncounterDetail({ encounterId }: EncounterDetailProps) {
  const queryClient = useQueryClient();

  const { data: encounter, isLoading: encounterLoading } =
    useEncounter(encounterId);

  const showOutputs =
    encounter && completedStatuses.includes(encounter.status);
  const showProcessing =
    encounter &&
    !completedStatuses.includes(encounter.status) &&
    !failedStatuses.includes(encounter.status);
  const showFailed =
    encounter && failedStatuses.includes(encounter.status);

  const { data: transcript } = useTranscript(
    encounterId,
    !!encounter?.has_transcript || showOutputs === true
  );
  const { data: note } = useNote(
    encounterId,
    !!encounter?.has_note || showOutputs === true
  );
  const { data: summary } = useSummary(
    encounterId,
    !!encounter?.has_summary || showOutputs === true
  );

  const handleStatusChange = (status: EncounterStatus) => {
    queryClient.invalidateQueries({
      queryKey: encounterKeys.detail(encounterId),
    });
  };

  if (encounterLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!encounter) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-muted-foreground">Encounter not found.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-4">
        <Link href="/encounters">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">
            Encounter - {format(new Date(encounter.encounter_date), "MMMM d, yyyy")}
          </h1>
          <p className="text-sm text-muted-foreground capitalize">
            Input: {encounter.input_method}
          </p>
        </div>
        <StatusBadge status={encounter.status} />
      </div>

      {showProcessing && (
        <ProcessingStatus
          encounterId={encounterId}
          currentStatus={encounter.status}
          onStatusChange={handleStatusChange}
        />
      )}

      {showFailed && (
        <Card className="border-destructive">
          <CardContent className="py-6 text-center">
            <p className="text-destructive font-medium">
              Processing failed at: {encounter.status.replace(/_/g, " ")}
            </p>
            <Button variant="outline" className="mt-4" onClick={() =>
              queryClient.invalidateQueries({ queryKey: encounterKeys.detail(encounterId) })
            }>
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {transcript && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Transcript</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="max-h-64 overflow-y-auto">
              {transcript.speaker_segments.length > 0 ? (
                <div className="space-y-2">
                  {transcript.speaker_segments.map((seg, idx) => (
                    <div key={idx} className="text-sm">
                      <span className="font-medium capitalize">{seg.speaker}:</span>{" "}
                      <span>{seg.text}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm whitespace-pre-wrap">{transcript.raw_text}</p>
              )}
            </div>
            {transcript.confidence_score > 0 && (
              <p className="text-xs text-muted-foreground mt-2">
                Confidence: {(transcript.confidence_score * 100).toFixed(0)}%
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {note && (
        <NoteEditor
          note={note}
          encounterId={encounterId}
          onApproved={() =>
            queryClient.invalidateQueries({
              queryKey: encounterKeys.detail(encounterId),
            })
          }
        />
      )}

      {note && (
        <QualityScoreDetail
          encounterId={encounterId}
          enabled={!!note}
        />
      )}

      {summary && (
        <SummaryPreview
          summary={summary}
          encounterId={encounterId}
          onSent={() =>
            queryClient.invalidateQueries({
              queryKey: encounterKeys.detail(encounterId),
            })
          }
        />
      )}
    </div>
  );
}
