import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import ProfileSetupScreen from '../profile-setup';

jest.mock('expo-router', () => ({
  useRouter: () => ({ replace: jest.fn() }),
}));
jest.mock('@/services/api-client', () => ({
  apiClient: { patch: jest.fn().mockResolvedValue({ data: {} }) },
}));
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'profileSetup.title': 'Set Up Your Profile',
        'profileSetup.firstName': 'First Name',
        'profileSetup.lastName': 'Last Name',
        'profileSetup.language': 'Preferred Language',
        'profileSetup.continue': 'Continue',
      };
      return translations[key] ?? key;
    },
    i18n: { changeLanguage: jest.fn() },
  }),
}));

describe('ProfileSetupScreen', () => {
  it('should render form fields', () => {
    const { getByText, getByLabelText } = render(<ProfileSetupScreen />);
    expect(getByText('Set Up Your Profile')).toBeTruthy();
    expect(getByLabelText('First Name')).toBeTruthy();
    expect(getByLabelText('Last Name')).toBeTruthy();
  });

  it('should submit profile data', async () => {
    const { apiClient } = require('@/services/api-client');
    const { getByLabelText, getByText } = render(<ProfileSetupScreen />);

    fireEvent.changeText(getByLabelText('First Name'), 'John');
    fireEvent.changeText(getByLabelText('Last Name'), 'Doe');
    fireEvent.press(getByText('Continue'));

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalled();
    });
  });
});
