import { renderHook, act } from '@testing-library/react-native';
import { useNetworkStatus } from '../use-network-status';

const mockAddEventListener = jest.fn();
const mockFetch = jest.fn();

jest.mock('@react-native-community/netinfo', () => ({
  addEventListener: (callback: Function) => {
    mockAddEventListener(callback);
    return jest.fn(); // unsubscribe
  },
  fetch: () => mockFetch(),
}));

describe('useNetworkStatus', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockResolvedValue({ isConnected: true, isInternetReachable: true });
  });

  it('should return connected status initially', async () => {
    const { result } = renderHook(() => useNetworkStatus());
    await act(async () => {});
    expect(result.current.isConnected).toBe(true);
  });

  it('should register event listener', () => {
    renderHook(() => useNetworkStatus());
    expect(mockAddEventListener).toHaveBeenCalled();
  });
});
