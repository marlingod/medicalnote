"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export const qualityKeys = {
  all: ["quality"] as const,
  detail: (encounterId: string) =>
    [...qualityKeys.all, encounterId] as const,
};

export function useQualityScore(encounterId: string, enabled = true) {
  return useQuery({
    queryKey: qualityKeys.detail(encounterId),
    queryFn: () => apiClient.quality.get(encounterId),
    enabled: !!encounterId && enabled,
    retry: false,
  });
}

export function useTriggerQualityScore() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (encounterId: string) =>
      apiClient.quality.trigger(encounterId),
    onSuccess: (_, encounterId) => {
      queryClient.invalidateQueries({
        queryKey: qualityKeys.detail(encounterId),
      });
    },
  });
}
