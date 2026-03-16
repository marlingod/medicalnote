import { MMKV } from 'react-native-mmkv';
import type { PatientSummary } from '@/types/api';

const KEYS = {
  SUMMARIES_LIST: 'cache:summaries:list',
  SUMMARY_DETAIL_PREFIX: 'cache:summaries:detail:',
  LAST_SYNC: 'cache:last_sync',
} as const;

// Encrypted MMKV instance for PHI data
const storage = new MMKV({
  id: 'medicalnote-offline-cache',
  encryptionKey: 'medicalnote-mmkv-encryption-key',
});

export const offlineCache = {
  setSummaries(summaries: PatientSummary[]): void {
    storage.set(KEYS.SUMMARIES_LIST, JSON.stringify(summaries));
  },

  getSummaries(): PatientSummary[] | null {
    const raw = storage.getString(KEYS.SUMMARIES_LIST);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as PatientSummary[];
    } catch {
      return null;
    }
  },

  setSummaryDetail(id: string, summary: PatientSummary): void {
    storage.set(`${KEYS.SUMMARY_DETAIL_PREFIX}${id}`, JSON.stringify(summary));
  },

  getSummaryDetail(id: string): PatientSummary | null {
    const raw = storage.getString(`${KEYS.SUMMARY_DETAIL_PREFIX}${id}`);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as PatientSummary;
    } catch {
      return null;
    }
  },

  setLastSyncTimestamp(timestamp: number): void {
    storage.set(KEYS.LAST_SYNC, timestamp.toString());
  },

  getLastSyncTimestamp(): number | null {
    const raw = storage.getString(KEYS.LAST_SYNC);
    if (!raw) return null;
    return parseInt(raw, 10);
  },

  clearAll(): void {
    storage.clearAll();
  },
};
