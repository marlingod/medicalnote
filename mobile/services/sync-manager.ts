import { summaryService } from './summary-service';
import { offlineCache } from './offline-cache';

const SYNC_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

export const syncManager = {
  async syncOnReconnect(): Promise<void> {
    const lastSync = offlineCache.getLastSyncTimestamp();
    if (lastSync && Date.now() - lastSync < SYNC_INTERVAL_MS) {
      return; // Recently synced
    }
    try {
      await summaryService.getSummaries(); // pull-only; caches internally
    } catch {
      // Silently fail -- will retry on next reconnect
    }
  },
};
