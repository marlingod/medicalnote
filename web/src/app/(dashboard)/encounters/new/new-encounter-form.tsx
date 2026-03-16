"use client";

import { useState, useRef } from "react";
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
import { useTemplates } from "@/hooks/use-templates";
import { AudioRecorder } from "@/components/encounters/audio-recorder";
import { PasteInput } from "@/components/encounters/paste-input";
import { ScanUpload } from "@/components/encounters/scan-upload";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
import { SPECIALTY_LABELS } from "@/lib/constants";
import { LayoutTemplate, X } from "lucide-react";
import type { InputMethod, NoteTemplateListItem } from "@/types";

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
  const [selectedTemplate, setSelectedTemplate] = useState<NoteTemplateListItem | null>(null);

  const { data: patientsData } = usePatients();
  const { data: templatesData } = useTemplates({ scope: "mine" });
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

      {/* Template Selection (Optional) */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <LayoutTemplate className="h-5 w-5" />
            Template (Optional)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {selectedTemplate ? (
            <div className="flex items-center justify-between rounded-md border p-3 bg-muted/50">
              <div>
                <p className="font-medium">{selectedTemplate.name}</p>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant="outline" className="text-xs">
                    {SPECIALTY_LABELS[selectedTemplate.specialty] || selectedTemplate.specialty}
                  </Badge>
                  <span className="text-xs text-muted-foreground uppercase">
                    {selectedTemplate.note_type.replace(/_/g, " ")}
                  </span>
                </div>
                {selectedTemplate.description && (
                  <p className="text-sm text-muted-foreground mt-1 line-clamp-1">
                    {selectedTemplate.description}
                  </p>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedTemplate(null)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                Optionally select a template to guide the AI note generation.
              </p>
              <Select
                onValueChange={(value) => {
                  if (value != null) {
                    const template = templatesData?.results.find(
                      (t) => t.id === String(value)
                    );
                    if (template) setSelectedTemplate(template);
                  }
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a template..." />
                </SelectTrigger>
                <SelectContent>
                  {templatesData?.results.map((template) => (
                    <SelectItem key={template.id} value={template.id}>
                      {template.name} ({SPECIALTY_LABELS[template.specialty] || template.specialty})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
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
  const [isListening, setIsListening] = useState(false);
  const [interimText, setInterimText] = useState("");
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  const supportsVoice =
    typeof window !== "undefined" &&
    ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);

  const startListening = () => {
    if (!supportsVoice) return;

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = "";
      let final = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          final += transcript + " ";
        } else {
          interim += transcript;
        }
      }
      if (final) {
        setText((prev) => prev + final);
      }
      setInterimText(interim);
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      console.error("Speech recognition error:", event.error);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
      setInterimText("");
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setIsListening(false);
    setInterimText("");
  };

  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const clearText = () => {
    setText("");
    setInterimText("");
  };

  return (
    <div className="space-y-4">
      <Label htmlFor="dictation">Dictate Clinical Notes</Label>

      {!supportsVoice && (
        <Alert>
          <AlertDescription>
            Voice dictation is not supported in this browser. You can type your notes below instead.
          </AlertDescription>
        </Alert>
      )}

      <div className="flex gap-2">
        {supportsVoice && (
          <Button
            type="button"
            variant={isListening ? "destructive" : "default"}
            onClick={toggleListening}
            disabled={isSubmitting}
            className="flex items-center gap-2"
          >
            {isListening ? (
              <>
                <span className="relative flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-white"></span>
                </span>
                Stop Listening
              </>
            ) : (
              <>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>
                Start Dictating
              </>
            )}
          </Button>
        )}
        {text.length > 0 && (
          <Button
            type="button"
            variant="outline"
            onClick={clearText}
            disabled={isSubmitting || isListening}
          >
            Clear
          </Button>
        )}
      </div>

      <div className="relative">
        <Textarea
          id="dictation"
          placeholder={isListening ? "Listening... speak now" : "Click 'Start Dictating' to use voice, or type your clinical notes here..."}
          className={`min-h-[200px] ${isListening ? "border-red-500 border-2" : ""}`}
          value={text + (interimText ? interimText : "")}
          onChange={(e) => {
            if (!isListening) {
              setText(e.target.value);
            }
          }}
          readOnly={isListening}
        />
        {isListening && (
          <div className="absolute bottom-2 right-2 flex items-center gap-1 text-xs text-red-500">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
            </span>
            Recording...
          </div>
        )}
      </div>

      {interimText && (
        <p className="text-sm text-muted-foreground italic">
          Hearing: "{interimText}"
        </p>
      )}

      <Button
        onClick={() => {
          stopListening();
          onSubmit(text);
        }}
        disabled={isSubmitting || text.length < 10 || isListening}
        className="w-full"
      >
        {isSubmitting ? "Submitting..." : "Submit Dictation"}
      </Button>
    </div>
  );
}
