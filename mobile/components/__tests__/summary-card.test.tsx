import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { SummaryCard } from '../summary-card';
import type { PatientSummary } from '@/types/api';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
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
  summary_en: 'Your visit went well. Blood pressure was normal.',
  summary_es: 'Su visita fue bien.',
  reading_level: 'grade_8',
  medical_terms_explained: [{ term: 'BP', explanation: 'Blood pressure' }],
  disclaimer_text: 'Disclaimer.',
  encounter_date: '2026-03-15',
  doctor_name: 'Dr. Smith',
  delivery_status: 'sent',
  viewed_at: null,
  created_at: '2026-03-15T10:00:00Z',
};

describe('SummaryCard', () => {
  it('should render doctor name and visit date', () => {
    const { getByText } = render(
      <SummaryCard summary={mockSummary} onPress={jest.fn()} />
    );
    expect(getByText('Dr. Smith')).toBeTruthy();
    expect(getByText(/2026-03-15/)).toBeTruthy();
  });

  it('should show "New" badge for unviewed summaries', () => {
    const { getByText } = render(
      <SummaryCard summary={mockSummary} onPress={jest.fn()} />
    );
    expect(getByText('New')).toBeTruthy();
  });

  it('should not show "New" badge for viewed summaries', () => {
    const viewedSummary = { ...mockSummary, delivery_status: 'viewed' as const, viewed_at: '2026-03-15T12:00:00Z' };
    const { queryByText } = render(
      <SummaryCard summary={viewedSummary} onPress={jest.fn()} />
    );
    expect(queryByText('New')).toBeNull();
  });

  it('should show summary preview text', () => {
    const { getByText } = render(
      <SummaryCard summary={mockSummary} onPress={jest.fn()} />
    );
    expect(getByText(/Your visit went well/)).toBeTruthy();
  });

  it('should call onPress when tapped', () => {
    const onPress = jest.fn();
    const { getByText } = render(
      <SummaryCard summary={mockSummary} onPress={onPress} />
    );
    fireEvent.press(getByText('Dr. Smith'));
    expect(onPress).toHaveBeenCalledWith('sum-1');
  });
});
