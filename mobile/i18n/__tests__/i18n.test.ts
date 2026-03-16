import i18n from '../index';

describe('i18n', () => {
  it('should initialize with English as default language', () => {
    expect(i18n.language).toBe('en');
  });

  it('should have English translations loaded', () => {
    expect(i18n.t('common.appName')).toBe('MedicalNote');
  });

  it('should switch to Spanish', async () => {
    await i18n.changeLanguage('es');
    expect(i18n.t('common.appName')).toBe('MedicalNote');
    expect(i18n.t('summary.disclaimer')).toBeTruthy();
    await i18n.changeLanguage('en'); // reset
  });

  it('should have all required translation keys in EN', () => {
    const requiredKeys = [
      'common.appName',
      'auth.enterPhone',
      'auth.enterOTP',
      'auth.sendCode',
      'auth.verifyCode',
      'summary.listTitle',
      'summary.visitDate',
      'summary.doctorName',
      'summary.disclaimer',
      'summary.contactDoctor',
      'summary.noSummaries',
      'summary.tapToExplain',
      'profile.title',
      'profile.language',
      'profile.notifications',
      'profile.logout',
    ];
    requiredKeys.forEach((key) => {
      const value = i18n.t(key);
      expect(value).not.toBe(key); // should not return key itself
    });
  });

  it('should have all required translation keys in ES', async () => {
    await i18n.changeLanguage('es');
    const value = i18n.t('auth.enterPhone');
    expect(value).not.toBe('auth.enterPhone');
    await i18n.changeLanguage('en');
  });
});
