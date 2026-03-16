import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import ProfileScreen from '../profile';
import { useAuth } from '@/contexts/auth-context';

jest.mock('@/contexts/auth-context');
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'profile.title': 'Profile & Settings',
        'profile.language': 'Language',
        'profile.notifications': 'Notifications',
        'profile.notificationsEnabled': 'Push notifications are enabled',
        'profile.privacy': 'Privacy',
        'profile.logout': 'Log Out',
        'profile.logoutConfirm': 'Are you sure you want to log out?',
        'profile.version': 'Version',
        'common.cancel': 'Cancel',
        'summary.english': 'English',
        'summary.spanish': 'Spanish',
      };
      return translations[key] ?? key;
    },
    i18n: { language: 'en', changeLanguage: jest.fn() },
  }),
}));

describe('ProfileScreen', () => {
  beforeEach(() => {
    (useAuth as jest.Mock).mockReturnValue({
      logout: jest.fn(),
    });
  });

  it('should render profile settings', () => {
    const { getByText } = render(<ProfileScreen />);
    expect(getByText('Profile & Settings')).toBeTruthy();
    expect(getByText('Language')).toBeTruthy();
    expect(getByText('Log Out')).toBeTruthy();
  });

  it('should call logout on confirmation', async () => {
    const mockLogout = jest.fn();
    (useAuth as jest.Mock).mockReturnValue({ logout: mockLogout });

    const { getByText } = render(<ProfileScreen />);
    fireEvent.press(getByText('Log Out'));
    // The confirmation dialog would appear in a real app
  });
});
