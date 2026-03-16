"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { CreateEncounterRequest } from "@/types";

export const encounterKeys = {
  all: ["encounters"] as const,
  lists: () => [...encounterKeys.all, "list"] as const,
  list: (params: Record<string, string>) =>
    [...encounterKeys.lists(), params] as const,
  details: () => [...encounterKeys.all, "detail"] as const,
  detail: (id: string) => [...encounterKeys.details(), id] as const,
  transcript: (id: string) =>
    [...encounterKeys.detail(id), "transcript"] as const,
};

export function useEncounters(params?: Record<string, string>) {
  return useQuery({
    queryKey: encounterKeys.list(params || {}),
    queryFn: () => apiClient.encounters.list(params),
  });
}

export function useEncounter(id: string) {
  return useQuery({
    queryKey: encounterKeys.detail(id),
    queryFn: () => apiClient.encounters.get(id),
    enabled: !!id,
  });
}

export function useTranscript(encounterId: string, enabled = true) {
  return useQuery({
    queryKey: encounterKeys.transcript(encounterId),
    queryFn: () => apiClient.encounters.getTranscript(encounterId),
    enabled: !!encounterId && enabled,
  });
}

export function useCreateEncounter() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateEncounterRequest) =>
      apiClient.encounters.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: encounterKeys.lists() });
    },
  });
}

export function usePasteInput() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, text }: { id: string; text: string }) =>
      apiClient.encounters.pasteInput(id, text),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: encounterKeys.detail(variables.id),
      });
    },
  });
}

export function useDictationInput() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, text }: { id: string; text: string }) =>
      apiClient.encounters.dictationInput(id, text),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: encounterKeys.detail(variables.id),
      });
    },
  });
}

export function useUploadRecording() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) =>
      apiClient.encounters.uploadRecording(id, file),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: encounterKeys.detail(variables.id),
      });
    },
  });
}

export function useUploadScan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) =>
      apiClient.encounters.uploadScan(id, file),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: encounterKeys.detail(variables.id),
      });
    },
  });
}
