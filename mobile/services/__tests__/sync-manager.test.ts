import { syncManager } from '../sync-manager';
import { summaryService } from '../summary-service';
import { offlineCache } from '../offline-cache';

jest.mock('../summary-service');
jest.mock('../offline-cache');

describe('SyncManager', () => {
  beforeEach(() => jest.clearAllMocks());

  it('should pull summaries on sync', async () => {
    (summaryService.getSummaries as jest.Mock).mockResolvedValue([]);
    await syncManager.syncOnReconnect();
    expect(summaryService.getSummaries).toHaveBeenCalled();
  });

  it('should skip sync if recently synced', async () => {
    (offlineCache.getLastSyncTimestamp as jest.Mock).mockReturnValue(Date.now());
    await syncManager.syncOnReconnect();
    expect(summaryService.getSummaries).not.toHaveBeenCalled();
  });

  it('should sync if last sync was over 5 minutes ago', async () => {
    (offlineCache.getLastSyncTimestamp as jest.Mock).mockReturnValue(Date.now() - 6 * 60 * 1000);
    (summaryService.getSummaries as jest.Mock).mockResolvedValue([]);
    await syncManager.syncOnReconnect();
    expect(summaryService.getSummaries).toHaveBeenCalled();
  });
});
