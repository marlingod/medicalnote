import { apiClient } from './api-client';
import { tokenStorage } from './token-storage';
import { offlineCache } from './offline-cache';
import type {
  OTPSendRequest,
  OTPSendResponse,
  OTPVerifyRequest,
  OTPVerifyResponse,
} from '@/types/api';

export const authService = {
  async sendOTP(phone: string): Promise<OTPSendResponse> {
    const response = await apiClient.post<OTPSendResponse>(
      '/auth/patient/otp/send/',
      { phone } as OTPSendRequest
    );
    return response.data;
  },

  async verifyOTP(phone: string, code: string): Promise<OTPVerifyResponse> {
    const response = await apiClient.post<OTPVerifyResponse>(
      '/auth/patient/otp/verify/',
      { phone, code } as OTPVerifyRequest
    );
    const { access, refresh, user_id } = response.data;
    await tokenStorage.setTokens({ access, refresh });
    await tokenStorage.setUserId(user_id);
    return response.data;
  },

  async logout(): Promise<void> {
    await tokenStorage.clearTokens();
    offlineCache.clearAll();
  },

  async isAuthenticated(): Promise<boolean> {
    const token = await tokenStorage.getAccessToken();
    return token !== null;
  },
};
