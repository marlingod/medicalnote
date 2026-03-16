"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type {
  CreateTemplateRequest,
  UpdateTemplateRequest,
  CloneTemplateRequest,
  RateTemplateRequest,
  AutoCompleteRequest,
} from "@/types";

export const templateKeys = {
  all: ["templates"] as const,
  lists: () => [...templateKeys.all, "list"] as const,
  list: (params: Record<string, string>) =>
    [...templateKeys.lists(), params] as const,
  details: () => [...templateKeys.all, "detail"] as const,
  detail: (id: string) => [...templateKeys.details(), id] as const,
  specialties: () => [...templateKeys.all, "specialties"] as const,
  favorites: () => [...templateKeys.all, "favorites"] as const,
};

export function useTemplates(params?: Record<string, string>) {
  return useQuery({
    queryKey: templateKeys.list(params || {}),
    queryFn: () => apiClient.templates.list(params),
  });
}

export function useTemplate(id: string) {
  return useQuery({
    queryKey: templateKeys.detail(id),
    queryFn: () => apiClient.templates.get(id),
    enabled: !!id,
  });
}

export function useSpecialties() {
  return useQuery({
    queryKey: templateKeys.specialties(),
    queryFn: () => apiClient.templates.getSpecialties(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useFavoriteTemplates(params?: Record<string, string>) {
  return useQuery({
    queryKey: templateKeys.favorites(),
    queryFn: () => apiClient.templates.getFavorites(params),
  });
}

export function useCreateTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateTemplateRequest) =>
      apiClient.templates.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: templateKeys.lists() });
    },
  });
}

export function useUpdateTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: UpdateTemplateRequest;
    }) => apiClient.templates.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: templateKeys.detail(variables.id),
      });
      queryClient.invalidateQueries({ queryKey: templateKeys.lists() });
    },
  });
}

export function useDeleteTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.templates.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: templateKeys.lists() });
    },
  });
}

export function useCloneTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data?: CloneTemplateRequest;
    }) => apiClient.templates.clone(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: templateKeys.lists() });
    },
  });
}

export function useRateTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: RateTemplateRequest;
    }) => apiClient.templates.rate(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: templateKeys.detail(variables.id),
      });
    },
  });
}

export function useToggleFavorite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      favorited,
    }: {
      id: string;
      favorited: boolean;
    }) =>
      favorited
        ? apiClient.templates.unfavorite(id)
        : apiClient.templates.favorite(id),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: templateKeys.detail(variables.id),
      });
      queryClient.invalidateQueries({ queryKey: templateKeys.lists() });
      queryClient.invalidateQueries({ queryKey: templateKeys.favorites() });
    },
  });
}

export function useAutoComplete() {
  return useMutation({
    mutationFn: ({
      templateId,
      data,
    }: {
      templateId: string;
      data: AutoCompleteRequest;
    }) => apiClient.templates.autoComplete(templateId, data),
  });
}
