import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { LanguageToggle } from '../language-toggle';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, string>) => {
      const translations: Record<string, string> = {
        'summary.english': 'English',
        'summary.spanish': 'Spanish',
      };
      return translations[key] ?? key;
    },
  }),
}));

describe('LanguageToggle', () => {
  it('should render with English selected by default', () => {
    const { getByText } = render(
      <LanguageToggle currentLanguage="en" onToggle={jest.fn()} />
    );
    expect(getByText('English')).toBeTruthy();
    expect(getByText('Spanish')).toBeTruthy();
  });

  it('should call onToggle with "es" when Spanish pressed', () => {
    const onToggle = jest.fn();
    const { getByText } = render(
      <LanguageToggle currentLanguage="en" onToggle={onToggle} />
    );
    fireEvent.press(getByText('Spanish'));
    expect(onToggle).toHaveBeenCalledWith('es');
  });

  it('should call onToggle with "en" when English pressed', () => {
    const onToggle = jest.fn();
    const { getByText } = render(
      <LanguageToggle currentLanguage="es" onToggle={onToggle} />
    );
    fireEvent.press(getByText('English'));
    expect(onToggle).toHaveBeenCalledWith('en');
  });
});
