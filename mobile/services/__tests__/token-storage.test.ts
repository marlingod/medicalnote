import { tokenStorage } from '../token-storage';

// Mock expo-secure-store
jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}));

import * as SecureStore from 'expo-secure-store';

describe('TokenStorage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should store access and refresh tokens', async () => {
    await tokenStorage.setTokens({ access: 'acc-123', refresh: 'ref-456' });
    expect(SecureStore.setItemAsync).toHaveBeenCalledWith('auth_access_token', 'acc-123');
    expect(SecureStore.setItemAsync).toHaveBeenCalledWith('auth_refresh_token', 'ref-456');
  });

  it('should retrieve access token', async () => {
    (SecureStore.getItemAsync as jest.Mock).mockResolvedValue('acc-123');
    const token = await tokenStorage.getAccessToken();
    expect(token).toBe('acc-123');
    expect(SecureStore.getItemAsync).toHaveBeenCalledWith('auth_access_token');
  });

  it('should retrieve refresh token', async () => {
    (SecureStore.getItemAsync as jest.Mock).mockResolvedValue('ref-456');
    const token = await tokenStorage.getRefreshToken();
    expect(token).toBe('ref-456');
    expect(SecureStore.getItemAsync).toHaveBeenCalledWith('auth_refresh_token');
  });

  it('should clear all tokens on logout', async () => {
    await tokenStorage.clearTokens();
    expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('auth_access_token');
    expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('auth_refresh_token');
    expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('auth_user_id');
  });

  it('should store and retrieve user ID', async () => {
    await tokenStorage.setUserId('user-uuid-1');
    expect(SecureStore.setItemAsync).toHaveBeenCalledWith('auth_user_id', 'user-uuid-1');

    (SecureStore.getItemAsync as jest.Mock).mockResolvedValue('user-uuid-1');
    const userId = await tokenStorage.getUserId();
    expect(userId).toBe('user-uuid-1');
  });
});
