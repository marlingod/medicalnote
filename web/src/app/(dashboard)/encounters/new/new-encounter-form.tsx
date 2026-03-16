"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import { format } from "date-fns";
import {
  useCreateEncounter,
  usePasteInput,
  useUploadRecording,
  useUploadScan,
  useDictationInput,
} from "@/hooks/use-encounters";
import { usePatients } from "@/hooks/use-patients";
import { AudioRecorder } from "@/components/encounters/audio-recorder";
import { PasteInput } from "@/components/encounters/paste-input";
import { ScanUpload } from "@/components/encounters/scan-upload";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { InputMethod } from "@/types";

const encounterSchema = z.object({
  patient: z.string().min(1, "Patient is required"),
  encounter_date: z.string().min(1, "Date is required"),
  consent_recording: z.boolean().optional(),
  consent_method: z.string().optional(),
  consent_jurisdiction_state: z.string().optional(),
});

type EncounterFormData = z.infer<typeof encounterSchema>;

export function NewEncounterForm() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<InputMethod>("paste");
  const [encounterId, setEncounterId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: patientsData } = usePatients();
  const createEncounter = useCreateEncounter();
  const pasteInput = usePasteInput();
  const uploadRecording = useUploadRecording();
  const uploadScan = useUploadScan();
  const dictationInput = useDictationInput();

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<EncounterFormData>({
    resolver: zodResolver(encounterSchema),
    defaultValues: {
      encounter_date: format(new Date(), "yyyy-MM-dd"),
      consent_recording: false,
    },
  });

  const createAndProcess = async (
    formData: EncounterFormData,
    inputMethod: InputMethod,
    processInput: (encounterId: string) => Promise<unknown>
  ) => {
    setError(null);
    try {
      const encounter = await createEncounter.mutateAsync({
        patient: formData.patient,
        encounter_date: formData.encounter_date,
        input_method: inputMethod,
        consent_recording: formData.consent_recording,
        consent_method: formData.consent_method,
        consent_jurisdiction_state: formData.consent_jurisdiction_state,
      });
      setEncounterId(encounter.id);
      await processInput(encounter.id);
      router.push(`/encounters/${encounter.id}`);
    } catch {
      setError("Failed to create encounter. Please try again.");
    }
  };

  const handlePasteSubmit = (text: string) => {
    handleSubmit((formData) =>
      createAndProcess(formData, "paste", (id) =>
        pasteInput.mutateAsync({ id, text })
      )
    )();
  };

  const handleRecordingComplete = (blob: Blob, duration: number) => {
    const file = new File([blob], `recording-${Date.now()}.webm`, {
      type: blob.type,
    });
    handleSubmit((formData) =>
      createAndProcess(formData, "recording", (id) =>
        uploadRecording.mutateAsync({ id, file })
      )
    )();
  };

  const handleScanUpload = (file: File) => {
    handleSubmit((formData) =>
      createAndProcess(formData, "scan", (id) =>
        uploadScan.mutateAsync({ id, file })
      )
    )();
  };

  const handleDictation = (text: string) => {
    handleSubmit((formData) =>
      createAndProcess(formData, "dictation", (id) =>
        dictationInput.mutateAsync({ id, text })
      )
    )();
  };

  const isProcessing =
    createEncounter.isPending ||
    pasteInput.isPending ||
    uploadRecording.isPending ||
    uploadScan.isPending ||
    dictationInput.isPending;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">New Encounter</h1>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Encounter Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="patient">Patient</Label>
              <Select onValueChange={(value) => { if (value != null) setValue("patient", String(value)); }}>
                <SelectTrigger>
                  <SelectValue placeholder="Select patient" />
                </SelectTrigger>
                <SelectContent>
                  {patientsData?.results.map((patient) => (
                    <SelectItem key={patient.id} value={patient.id}>
                      {patient.first_name} {patient.last_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.patient && (
                <p className="text-sm text-destructive">{errors.patient.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="encounter_date">Date</Label>
              <Input type="date" {...register("encounter_date")} />
              {errors.encounter_date && (
                <p className="text-sm text-destructive">
                  {errors.encounter_date.message}
                </p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Input Method</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs
            value={activeTab}
            onValueChange={(v) => setActiveTab(v as InputMethod)}
          >
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="paste">Paste</TabsTrigger>
              <TabsTrigger value="recording">Record</TabsTrigger>
              <TabsTrigger value="dictation">Dictate</TabsTrigger>
              <TabsTrigger value="scan">Scan</TabsTrigger>
            </TabsList>

            <TabsContent value="paste" className="mt-4">
              <PasteInput
                onSubmit={handlePasteSubmit}
                isSubmitting={isProcessing}
              />
            </TabsContent>

            <TabsContent value="recording" className="mt-4">
              <AudioRecorder
                onRecordingComplete={handleRecordingComplete}
                disabled={isProcessing}
              />
            </TabsContent>

            <TabsContent value="dictation" className="mt-4">
              <Card>
                <CardContent className="py-6">
                  <DictationInput
                    onSubmit={handleDictation}
                    isSubmitting={isProcessing}
                  />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="scan" className="mt-4">
              <ScanUpload
                onUpload={handleScanUpload}
                isUploading={isProcessing}
              />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}

function DictationInput({
  onSubmit,
  isSubmitting,
}: {
  onSubmit: (text: string) => void;
  isSubmitting?: boolean;
}) {
  const [text, setText] = useState("");
  return (
    <div className="space-y-4">
      <Label htmlFor="dictation">Dictate Clinical Notes</Label>
      <Textarea
        id="dictation"
        placeholder="Dictate or type your clinical notes..."
        className="min-h-[200px]"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <Button
        onClick={() => onSubmit(text)}
        disabled={isSubmitting || text.length < 10}
        className="w-full"
      >
        {isSubmitting ? "Submitting..." : "Submit Dictation"}
      </Button>
    </div>
  );
}
