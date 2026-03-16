import { summaryService } from '../summary-service';
import { apiClient } from '../api-client';
import { offlineCache } from '../offline-cache';
import type { PatientSummary } from '@/types/api';

jest.mock('../api-client');
jest.mock('../offline-cache');

const mockSummary: PatientSummary = {
  id: 'sum-1',
  summary_en: 'Your visit summary.',
  summary_es: 'Resumen de su visita.',
  reading_level: 'grade_8',
  medical_terms_explained: [],
  disclaimer_text: 'Disclaimer.',
  encounter_date: '2026-03-15',
  doctor_name: 'Dr. Smith',
  delivery_status: 'sent',
  viewed_at: null,
  created_at: '2026-03-15T10:00:00Z',
};

describe('SummaryService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should fetch summaries from API and cache them', async () => {
    (apiClient.get as jest.Mock).mockResolvedValue({
      data: { count: 1, results: [mockSummary] },
    });

    const result = await summaryService.getSummaries();
    expect(result).toHaveLength(1);
    expect(apiClient.get).toHaveBeenCalledWith('/patient/summaries/');
    expect(offlineCache.setSummaries).toHaveBeenCalledWith([mockSummary]);
  });

  it('should return cached summaries when offline', async () => {
    (apiClient.get as jest.Mock).mockRejectedValue(new Error('Network Error'));
    (offlineCache.getSummaries as jest.Mock).mockReturnValue([mockSummary]);

    const result = await summaryService.getSummaries();
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe('sum-1');
  });

  it('should throw when offline and no cache', async () => {
    (apiClient.get as jest.Mock).mockRejectedValue(new Error('Network Error'));
    (offlineCache.getSummaries as jest.Mock).mockReturnValue(null);

    await expect(summaryService.getSummaries()).rejects.toThrow();
  });

  it('should fetch summary detail and cache it', async () => {
    (apiClient.get as jest.Mock).mockResolvedValue({ data: mockSummary });

    const result = await summaryService.getSummaryDetail('sum-1');
    expect(result.id).toBe('sum-1');
    expect(offlineCache.setSummaryDetail).toHaveBeenCalledWith('sum-1', mockSummary);
  });

  it('should mark summary as read', async () => {
    (apiClient.patch as jest.Mock).mockResolvedValue({ data: { status: 'viewed' } });

    await summaryService.markAsRead('sum-1');
    expect(apiClient.patch).toHaveBeenCalledWith('/patient/summaries/sum-1/read/');
  });

  it('should return cached detail when offline', async () => {
    (apiClient.get as jest.Mock).mockRejectedValue(new Error('Network Error'));
    (offlineCache.getSummaryDetail as jest.Mock).mockReturnValue(mockSummary);

    const result = await summaryService.getSummaryDetail('sum-1');
    expect(result.id).toBe('sum-1');
  });
});
