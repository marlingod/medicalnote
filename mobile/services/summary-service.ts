import { apiClient } from './api-client';
import { offlineCache } from './offline-cache';
import type { PatientSummary, PatientSummaryListResponse } from '@/types/api';

export const summaryService = {
  async getSummaries(): Promise<PatientSummary[]> {
    try {
      const response = await apiClient.get<PatientSummaryListResponse>(
        '/patient/summaries/'
      );
      const summaries = response.data.results;
      offlineCache.setSummaries(summaries);
      offlineCache.setLastSyncTimestamp(Date.now());
      return summaries;
    } catch (error) {
      const cached = offlineCache.getSummaries();
      if (cached) {
        return cached;
      }
      throw error;
    }
  },

  async getSummaryDetail(id: string): Promise<PatientSummary> {
    try {
      const response = await apiClient.get<PatientSummary>(
        `/patient/summaries/${id}/`
      );
      const summary = response.data;
      offlineCache.setSummaryDetail(id, summary);
      return summary;
    } catch (error) {
      const cached = offlineCache.getSummaryDetail(id);
      if (cached) {
        return cached;
      }
      throw error;
    }
  },

  async markAsRead(id: string): Promise<void> {
    await apiClient.patch(`/patient/summaries/${id}/read/`);
  },
};
