import React from 'react';
import { render, waitFor } from '@testing-library/react-native';
import SummaryDetailScreen from '../[id]';
import { summaryService } from '@/services/summary-service';
import type { PatientSummary } from '@/types/api';

jest.mock('@/services/summary-service');
jest.mock('expo-router', () => ({
  useLocalSearchParams: () => ({ id: 'sum-1' }),
  useRouter: () => ({ back: jest.fn() }),
}));
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'summary.visitDate': 'Visit Date',
        'summary.doctorName': 'Doctor',
        'summary.disclaimer': 'For informational purposes only.',
        'summary.contactDoctor': 'Contact My Doctor',
        'summary.tapToExplain': 'Tap terms for explanations',
        'summary.english': 'English',
        'summary.spanish': 'Spanish',
        'common.loading': 'Loading...',
        'common.error': 'An error occurred',
      };
      return translations[key] ?? key;
    },
  }),
}));

const mockSummary: PatientSummary = {
  id: 'sum-1',
  summary_en: 'Your blood pressure was normal. Continue your medication.',
  summary_es: 'Su presion arterial fue normal. Continue con su medicamento.',
  reading_level: 'grade_8',
  medical_terms_explained: [
    { term: 'blood pressure', explanation: 'The force of blood against artery walls.' },
  ],
  disclaimer_text: 'This is for informational purposes only.',
  encounter_date: '2026-03-15',
  doctor_name: 'Dr. Smith',
  delivery_status: 'sent',
  viewed_at: null,
  created_at: '2026-03-15T10:00:00Z',
};

describe('SummaryDetailScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should show loading state initially', () => {
    (summaryService.getSummaryDetail as jest.Mock).mockReturnValue(new Promise(() => {}));
    const { getByText } = render(<SummaryDetailScreen />);
    expect(getByText('Loading...')).toBeTruthy();
  });

  it('should display summary content', async () => {
    (summaryService.getSummaryDetail as jest.Mock).mockResolvedValue(mockSummary);
    (summaryService.markAsRead as jest.Mock).mockResolvedValue(undefined);

    const { getByText } = render(<SummaryDetailScreen />);
    await waitFor(() => {
      expect(getByText('Dr. Smith')).toBeTruthy();
      expect(getByText(/blood pressure was normal/)).toBeTruthy();
    });
  });

  it('should display disclaimer banner', async () => {
    (summaryService.getSummaryDetail as jest.Mock).mockResolvedValue(mockSummary);
    (summaryService.markAsRead as jest.Mock).mockResolvedValue(undefined);

    const { getByText } = render(<SummaryDetailScreen />);
    await waitFor(() => {
      expect(getByText(/informational purposes only/)).toBeTruthy();
    });
  });

  it('should show contact doctor action', async () => {
    (summaryService.getSummaryDetail as jest.Mock).mockResolvedValue(mockSummary);
    (summaryService.markAsRead as jest.Mock).mockResolvedValue(undefined);

    const { getByText } = render(<SummaryDetailScreen />);
    await waitFor(() => {
      expect(getByText('Contact My Doctor')).toBeTruthy();
    });
  });

  it('should display medical term explanations', async () => {
    (summaryService.getSummaryDetail as jest.Mock).mockResolvedValue(mockSummary);
    (summaryService.markAsRead as jest.Mock).mockResolvedValue(undefined);

    const { getByText } = render(<SummaryDetailScreen />);
    await waitFor(() => {
      expect(getByText('blood pressure')).toBeTruthy();
    });
  });

  it('should mark as read on load', async () => {
    (summaryService.getSummaryDetail as jest.Mock).mockResolvedValue(mockSummary);
    (summaryService.markAsRead as jest.Mock).mockResolvedValue(undefined);

    render(<SummaryDetailScreen />);
    await waitFor(() => {
      expect(summaryService.markAsRead).toHaveBeenCalledWith('sum-1');
    });
  });
});
