import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import LoginScreen from '../login';
import { useAuth } from '@/contexts/auth-context';

jest.mock('@/contexts/auth-context');
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, string>) => {
      const translations: Record<string, string> = {
        'auth.welcome': 'Welcome to MedicalNote',
        'auth.enterPhone': 'Enter your phone number',
        'auth.phoneLabel': 'Phone Number',
        'auth.sendCode': 'Send Verification Code',
        'auth.enterOTP': 'Enter verification code',
        'auth.otpLabel': '6-Digit Code',
        'auth.verifyCode': 'Verify Code',
        'auth.codeSent': 'Verification code sent!',
        'auth.invalidCode': 'Invalid verification code.',
        'auth.resendCode': 'Resend Code',
        'auth.resendIn': `Resend code in ${opts?.seconds ?? ''}s`,
      };
      return translations[key] ?? key;
    },
  }),
}));

const mockSendOTP = jest.fn();
const mockLogin = jest.fn();

beforeEach(() => {
  jest.clearAllMocks();
  (useAuth as jest.Mock).mockReturnValue({
    sendOTP: mockSendOTP,
    login: mockLogin,
    isLoading: false,
  });
});

describe('LoginScreen', () => {
  it('should render phone input step initially', () => {
    const { getByText, getByLabelText } = render(<LoginScreen />);
    expect(getByText('Welcome to MedicalNote')).toBeTruthy();
    expect(getByText('Send Verification Code')).toBeTruthy();
  });

  it('should call sendOTP when phone submitted', async () => {
    mockSendOTP.mockResolvedValue(undefined);
    const { getByLabelText, getByText } = render(<LoginScreen />);

    const phoneInput = getByLabelText('Phone Number');
    fireEvent.changeText(phoneInput, '+15551234567');
    fireEvent.press(getByText('Send Verification Code'));

    await waitFor(() => {
      expect(mockSendOTP).toHaveBeenCalledWith('+15551234567');
    });
  });

  it('should show OTP input after phone submitted', async () => {
    mockSendOTP.mockResolvedValue(undefined);
    const { getByLabelText, getByText } = render(<LoginScreen />);

    fireEvent.changeText(getByLabelText('Phone Number'), '+15551234567');
    fireEvent.press(getByText('Send Verification Code'));

    await waitFor(() => {
      expect(getByText('Enter verification code')).toBeTruthy();
      expect(getByText('Verify Code')).toBeTruthy();
    });
  });

  it('should call login when OTP submitted', async () => {
    mockSendOTP.mockResolvedValue(undefined);
    mockLogin.mockResolvedValue(undefined);

    const { getByLabelText, getByText } = render(<LoginScreen />);

    fireEvent.changeText(getByLabelText('Phone Number'), '+15551234567');
    fireEvent.press(getByText('Send Verification Code'));

    await waitFor(() => {
      expect(getByText('Verify Code')).toBeTruthy();
    });

    fireEvent.changeText(getByLabelText('6-Digit Code'), '123456');
    fireEvent.press(getByText('Verify Code'));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('+15551234567', '123456');
    });
  });
});
