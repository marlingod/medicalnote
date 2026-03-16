"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Mic, Square, Pause, Play } from "lucide-react";
import { MAX_RECORDING_DURATION_MS } from "@/lib/constants";

interface AudioRecorderProps {
  onRecordingComplete: (blob: Blob, duration: number) => void;
  disabled?: boolean;
}

export function AudioRecorder({ onRecordingComplete, disabled }: AudioRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval>>(undefined);
  const startTimeRef = useRef<number>(0);
  const elapsedRef = useRef<number>(0);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const startRecording = useCallback(async () => {
    setError(null);
    chunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        stream.getTracks().forEach((track) => track.stop());
        if (timerRef.current) clearInterval(timerRef.current);
        const finalDuration = elapsedRef.current;
        onRecordingComplete(blob, finalDuration);
        setIsRecording(false);
        setIsPaused(false);
        setDuration(0);
        elapsedRef.current = 0;
      };

      recorder.start(1000); // Collect data every second
      setIsRecording(true);
      startTimeRef.current = Date.now();

      timerRef.current = setInterval(() => {
        const elapsed = elapsedRef.current + (Date.now() - startTimeRef.current);
        setDuration(Math.floor(elapsed / 1000));
        if (elapsed >= MAX_RECORDING_DURATION_MS) {
          stopRecording();
        }
      }, 500);
    } catch {
      setError("Microphone access denied. Please allow microphone access to record.");
    }
  }, [onRecordingComplete]);

  const stopRecording = useCallback(() => {
    elapsedRef.current += Date.now() - startTimeRef.current;
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const togglePause = useCallback(() => {
    if (!mediaRecorderRef.current) return;
    if (isPaused) {
      mediaRecorderRef.current.resume();
      startTimeRef.current = Date.now();
      timerRef.current = setInterval(() => {
        const elapsed = elapsedRef.current + (Date.now() - startTimeRef.current);
        setDuration(Math.floor(elapsed / 1000));
      }, 500);
      setIsPaused(false);
    } else {
      mediaRecorderRef.current.pause();
      elapsedRef.current += Date.now() - startTimeRef.current;
      if (timerRef.current) clearInterval(timerRef.current);
      setIsPaused(true);
    }
  }, [isPaused]);

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-4 py-8">
        {error && <p className="text-sm text-destructive">{error}</p>}

        {isRecording && (
          <div className="text-center">
            <div className="flex items-center gap-2 mb-2">
              <div className={`h-3 w-3 rounded-full ${isPaused ? "bg-yellow-500" : "bg-red-500 animate-pulse"}`} />
              <span className="text-sm font-medium">{isPaused ? "Paused" : "Recording"}</span>
            </div>
            <p className="text-3xl font-mono font-bold">{formatDuration(duration)}</p>
          </div>
        )}

        <div className="flex gap-3">
          {!isRecording ? (
            <Button onClick={startRecording} disabled={disabled} size="lg">
              <Mic className="mr-2 h-5 w-5" />
              Start Recording
            </Button>
          ) : (
            <>
              <Button onClick={togglePause} variant="outline" size="lg">
                {isPaused ? <Play className="mr-2 h-5 w-5" /> : <Pause className="mr-2 h-5 w-5" />}
                {isPaused ? "Resume" : "Pause"}
              </Button>
              <Button onClick={stopRecording} variant="destructive" size="lg">
                <Square className="mr-2 h-5 w-5" />
                Stop
              </Button>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
