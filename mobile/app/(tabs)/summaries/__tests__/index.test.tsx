import React from 'react';
import { render, waitFor } from '@testing-library/react-native';
import SummaryListScreen from '../index';
import { summaryService } from '@/services/summary-service';
import type { PatientSummary } from '@/types/api';

jest.mock('@/services/summary-service');
jest.mock('expo-router', () => ({ useRouter: () => ({ push: jest.fn() }) }));
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'summary.listTitle': 'My Visit Summaries',
        'summary.noSummaries': 'No visit summaries yet.',
        'common.loading': 'Loading...',
        'common.error': 'An error occurred',
        'common.retry': 'Retry',
        'common.offline': 'You are offline.',
        'summary.visitDate': 'Visit Date',
        'summary.doctorName': 'Doctor',
        'summary.new': 'New',
      };
      return translations[key] ?? key;
    },
  }),
}));

const mockSummary: PatientSummary = {
  id: 'sum-1',
  summary_en: 'Your visit summary.',
  summary_es: 'Resumen.',
  reading_level: 'grade_8',
  medical_terms_explained: [],
  disclaimer_text: 'Disclaimer.',
  encounter_date: '2026-03-15',
  doctor_name: 'Dr. Smith',
  delivery_status: 'sent',
  viewed_at: null,
  created_at: '2026-03-15T10:00:00Z',
};

describe('SummaryListScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should show loading state initially', () => {
    (summaryService.getSummaries as jest.Mock).mockReturnValue(new Promise(() => {}));
    const { getByText } = render(<SummaryListScreen />);
    expect(getByText('Loading...')).toBeTruthy();
  });

  it('should display summaries when loaded', async () => {
    (summaryService.getSummaries as jest.Mock).mockResolvedValue([mockSummary]);

    const { getByText } = render(<SummaryListScreen />);
    await waitFor(() => {
      expect(getByText('Dr. Smith')).toBeTruthy();
    });
  });

  it('should show empty state when no summaries', async () => {
    (summaryService.getSummaries as jest.Mock).mockResolvedValue([]);

    const { getByText } = render(<SummaryListScreen />);
    await waitFor(() => {
      expect(getByText('No visit summaries yet.')).toBeTruthy();
    });
  });

  it('should show error state on failure', async () => {
    (summaryService.getSummaries as jest.Mock).mockRejectedValue(new Error('Network Error'));

    const { getByText } = render(<SummaryListScreen />);
    await waitFor(() => {
      expect(getByText('An error occurred')).toBeTruthy();
      expect(getByText('Retry')).toBeTruthy();
    });
  });
});
