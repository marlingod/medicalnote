import React from 'react';
import { renderHook, act } from '@testing-library/react-native';
import { AuthProvider, useAuth } from '../auth-context';
import { authService } from '@/services/auth-service';

jest.mock('@/services/auth-service');

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
);

describe('AuthContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (authService.isAuthenticated as jest.Mock).mockResolvedValue(false);
  });

  it('should provide initial unauthenticated state', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    // Wait for async init
    await act(async () => {});
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.isLoading).toBe(false);
  });

  it('should update state after successful login', async () => {
    (authService.verifyOTP as jest.Mock).mockResolvedValue({
      access: 'token',
      refresh: 'refresh',
      user_id: 'user-1',
    });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await act(async () => {});

    await act(async () => {
      await result.current.login('+15551234567', '123456');
    });
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.userId).toBe('user-1');
  });

  it('should clear state on logout', async () => {
    (authService.isAuthenticated as jest.Mock).mockResolvedValue(true);

    const { result } = renderHook(() => useAuth(), { wrapper });
    await act(async () => {});

    await act(async () => {
      await result.current.logout();
    });
    expect(result.current.isAuthenticated).toBe(false);
    expect(authService.logout).toHaveBeenCalled();
  });
});
