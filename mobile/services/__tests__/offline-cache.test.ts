import { offlineCache } from '../offline-cache';
import type { PatientSummary } from '@/types/api';

// Mock react-native-mmkv
jest.mock('react-native-mmkv', () => {
  const store: Record<string, string> = {};
  return {
    MMKV: jest.fn().mockImplementation(() => ({
      set: jest.fn((key: string, value: string) => { store[key] = value; }),
      getString: jest.fn((key: string) => store[key] ?? undefined),
      delete: jest.fn((key: string) => { delete store[key]; }),
      clearAll: jest.fn(() => { Object.keys(store).forEach(k => delete store[k]); }),
      contains: jest.fn((key: string) => key in store),
    })),
  };
});

const mockSummary: PatientSummary = {
  id: 'sum-1',
  summary_en: 'Your visit summary.',
  summary_es: 'Resumen de su visita.',
  reading_level: 'grade_8',
  medical_terms_explained: [{ term: 'BP', explanation: 'Blood pressure' }],
  disclaimer_text: 'Disclaimer text.',
  encounter_date: '2026-03-15',
  doctor_name: 'Dr. Smith',
  delivery_status: 'sent',
  viewed_at: null,
  created_at: '2026-03-15T10:00:00Z',
};

describe('OfflineCache', () => {
  beforeEach(() => {
    offlineCache.clearAll();
  });

  it('should cache a list of summaries', () => {
    offlineCache.setSummaries([mockSummary]);
    const cached = offlineCache.getSummaries();
    expect(cached).toHaveLength(1);
    expect(cached![0].id).toBe('sum-1');
  });

  it('should cache a single summary by ID', () => {
    offlineCache.setSummaryDetail('sum-1', mockSummary);
    const cached = offlineCache.getSummaryDetail('sum-1');
    expect(cached).toBeDefined();
    expect(cached!.doctor_name).toBe('Dr. Smith');
  });

  it('should return null for missing summary', () => {
    const cached = offlineCache.getSummaryDetail('nonexistent');
    expect(cached).toBeNull();
  });

  it('should clear all cached data', () => {
    offlineCache.setSummaries([mockSummary]);
    offlineCache.clearAll();
    const cached = offlineCache.getSummaries();
    expect(cached).toBeNull();
  });

  it('should cache last sync timestamp', () => {
    const now = Date.now();
    offlineCache.setLastSyncTimestamp(now);
    expect(offlineCache.getLastSyncTimestamp()).toBe(now);
  });
});
