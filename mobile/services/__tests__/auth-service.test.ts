import { authService } from '../auth-service';
import { apiClient } from '../api-client';
import { tokenStorage } from '../token-storage';

jest.mock('../api-client');
jest.mock('../token-storage');

describe('AuthService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should send OTP to phone number', async () => {
    (apiClient.post as jest.Mock).mockResolvedValue({
      data: { message: 'Verification code sent.' },
    });

    const result = await authService.sendOTP('+15551234567');
    expect(result).toEqual({ message: 'Verification code sent.' });
    expect(apiClient.post).toHaveBeenCalledWith('/auth/patient/otp/send/', {
      phone: '+15551234567',
    });
  });

  it('should verify OTP and store tokens', async () => {
    (apiClient.post as jest.Mock).mockResolvedValue({
      data: {
        access: 'access-token-123',
        refresh: 'refresh-token-456',
        user_id: 'user-uuid-1',
      },
    });

    const result = await authService.verifyOTP('+15551234567', '123456');
    expect(result.user_id).toBe('user-uuid-1');
    expect(tokenStorage.setTokens).toHaveBeenCalledWith({
      access: 'access-token-123',
      refresh: 'refresh-token-456',
    });
    expect(tokenStorage.setUserId).toHaveBeenCalledWith('user-uuid-1');
  });

  it('should throw on invalid OTP', async () => {
    (apiClient.post as jest.Mock).mockRejectedValue({
      response: { status: 401, data: { error: 'Invalid verification code.' } },
    });

    await expect(authService.verifyOTP('+15551234567', '000000')).rejects.toBeDefined();
  });

  it('should logout and clear tokens', async () => {
    await authService.logout();
    expect(tokenStorage.clearTokens).toHaveBeenCalled();
  });

  it('should check if user is authenticated', async () => {
    (tokenStorage.getAccessToken as jest.Mock).mockResolvedValue('token-123');
    const isAuth = await authService.isAuthenticated();
    expect(isAuth).toBe(true);
  });

  it('should return false when no token stored', async () => {
    (tokenStorage.getAccessToken as jest.Mock).mockResolvedValue(null);
    const isAuth = await authService.isAuthenticated();
    expect(isAuth).toBe(false);
  });
});
