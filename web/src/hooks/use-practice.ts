"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Practice } from "@/types";

export const practiceKeys = {
  detail: ["practice"] as const,
  stats: ["practice", "stats"] as const,
  auditLog: (params: Record<string, string>) =>
    ["practice", "audit-log", params] as const,
};

export function usePractice() {
  return useQuery({
    queryKey: practiceKeys.detail,
    queryFn: () => apiClient.practice.get(),
  });
}

export function usePracticeStats() {
  return useQuery({
    queryKey: practiceKeys.stats,
    queryFn: () => apiClient.practice.getStats(),
  });
}

export function useUpdatePractice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Practice>) => apiClient.practice.update(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: practiceKeys.detail });
    },
  });
}

export function useAuditLog(params?: Record<string, string>) {
  return useQuery({
    queryKey: practiceKeys.auditLog(params || {}),
    queryFn: () => apiClient.practice.getAuditLog(params),
  });
}
