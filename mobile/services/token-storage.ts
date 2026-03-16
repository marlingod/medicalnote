import * as SecureStore from 'expo-secure-store';

const KEYS = {
  ACCESS_TOKEN: 'auth_access_token',
  REFRESH_TOKEN: 'auth_refresh_token',
  USER_ID: 'auth_user_id',
} as const;

export interface AuthTokens {
  access: string;
  refresh: string;
}

export const tokenStorage = {
  async setTokens(tokens: AuthTokens): Promise<void> {
    await SecureStore.setItemAsync(KEYS.ACCESS_TOKEN, tokens.access);
    await SecureStore.setItemAsync(KEYS.REFRESH_TOKEN, tokens.refresh);
  },

  async getAccessToken(): Promise<string | null> {
    return SecureStore.getItemAsync(KEYS.ACCESS_TOKEN);
  },

  async getRefreshToken(): Promise<string | null> {
    return SecureStore.getItemAsync(KEYS.REFRESH_TOKEN);
  },

  async setUserId(userId: string): Promise<void> {
    await SecureStore.setItemAsync(KEYS.USER_ID, userId);
  },

  async getUserId(): Promise<string | null> {
    return SecureStore.getItemAsync(KEYS.USER_ID);
  },

  async clearTokens(): Promise<void> {
    await SecureStore.deleteItemAsync(KEYS.ACCESS_TOKEN);
    await SecureStore.deleteItemAsync(KEYS.REFRESH_TOKEN);
    await SecureStore.deleteItemAsync(KEYS.USER_ID);
  },
};
