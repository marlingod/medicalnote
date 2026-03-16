"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { SendSummaryRequest } from "@/types";
import { encounterKeys } from "@/hooks/use-encounters";

export const summaryKeys = {
  detail: (encounterId: string) => ["summaries", encounterId] as const,
};

export function useSummary(encounterId: string, enabled = true) {
  return useQuery({
    queryKey: summaryKeys.detail(encounterId),
    queryFn: () => apiClient.summaries.get(encounterId),
    enabled: !!encounterId && enabled,
  });
}

export function useSendSummary() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      encounterId,
      data,
    }: {
      encounterId: string;
      data: SendSummaryRequest;
    }) => apiClient.summaries.send(encounterId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: summaryKeys.detail(variables.encounterId),
      });
      queryClient.invalidateQueries({
        queryKey: encounterKeys.detail(variables.encounterId),
      });
    },
  });
}
