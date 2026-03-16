"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { UpdateNoteRequest } from "@/types";
import { encounterKeys } from "@/hooks/use-encounters";

export const noteKeys = {
  detail: (encounterId: string) => ["notes", encounterId] as const,
};

export function useNote(encounterId: string, enabled = true) {
  return useQuery({
    queryKey: noteKeys.detail(encounterId),
    queryFn: () => apiClient.notes.get(encounterId),
    enabled: !!encounterId && enabled,
  });
}

export function useUpdateNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      encounterId,
      data,
    }: {
      encounterId: string;
      data: UpdateNoteRequest;
    }) => apiClient.notes.update(encounterId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: noteKeys.detail(variables.encounterId),
      });
    },
  });
}

export function useApproveNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (encounterId: string) => apiClient.notes.approve(encounterId),
    onSuccess: (_, encounterId) => {
      queryClient.invalidateQueries({
        queryKey: noteKeys.detail(encounterId),
      });
      queryClient.invalidateQueries({
        queryKey: encounterKeys.detail(encounterId),
      });
    },
  });
}
