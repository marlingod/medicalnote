import React, { useState, useCallback } from 'react';
import { View, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import {
  Text,
  TextInput,
  Button,
  HelperText,
  Surface,
} from 'react-native-paper';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/contexts/auth-context';

type Step = 'phone' | 'otp';

export default function LoginScreen() {
  const { t } = useTranslation();
  const { sendOTP, login } = useAuth();

  const [step, setStep] = useState<Step>('phone');
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resendCountdown, setResendCountdown] = useState(0);

  const handleSendOTP = useCallback(async () => {
    if (!phone.trim()) return;
    setError(null);
    setIsSubmitting(true);
    try {
      await sendOTP(phone.trim());
      setStep('otp');
      startResendCountdown();
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { error?: string } } })?.response?.data?.error ??
        t('common.error');
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }, [phone, sendOTP, t]);

  const handleVerifyOTP = useCallback(async () => {
    if (!code.trim() || code.length !== 6) return;
    setError(null);
    setIsSubmitting(true);
    try {
      await login(phone.trim(), code.trim());
      // Navigation handled by root layout auth check
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { error?: string } } })?.response?.data?.error ??
        t('auth.invalidCode');
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }, [phone, code, login, t]);

  const startResendCountdown = useCallback(() => {
    setResendCountdown(60);
    const interval = setInterval(() => {
      setResendCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }, []);

  const handleResend = useCallback(async () => {
    setError(null);
    try {
      await sendOTP(phone.trim());
      startResendCountdown();
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { error?: string } } })?.response?.data?.error ??
        t('auth.tooManyAttempts');
      setError(message);
    }
  }, [phone, sendOTP, startResendCountdown, t]);

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <Surface style={styles.card} elevation={2}>
        <Text variant="headlineMedium" style={styles.title}>
          {t('auth.welcome')}
        </Text>

        {step === 'phone' ? (
          <>
            <Text variant="bodyLarge" style={styles.subtitle}>
              {t('auth.enterPhone')}
            </Text>
            <TextInput
              label={t('auth.phoneLabel')}
              accessibilityLabel={t('auth.phoneLabel')}
              value={phone}
              onChangeText={setPhone}
              keyboardType="phone-pad"
              autoComplete="tel"
              placeholder={t('auth.phonePlaceholder')}
              style={styles.input}
              mode="outlined"
            />
            {error && <HelperText type="error">{error}</HelperText>}
            <Button
              mode="contained"
              onPress={handleSendOTP}
              loading={isSubmitting}
              disabled={isSubmitting || !phone.trim()}
              style={styles.button}
            >
              {t('auth.sendCode')}
            </Button>
          </>
        ) : (
          <>
            <Text variant="bodyLarge" style={styles.subtitle}>
              {t('auth.enterOTP')}
            </Text>
            <TextInput
              label={t('auth.otpLabel')}
              accessibilityLabel={t('auth.otpLabel')}
              value={code}
              onChangeText={setCode}
              keyboardType="number-pad"
              maxLength={6}
              placeholder={t('auth.otpPlaceholder')}
              style={styles.input}
              mode="outlined"
            />
            {error && <HelperText type="error">{error}</HelperText>}
            <Button
              mode="contained"
              onPress={handleVerifyOTP}
              loading={isSubmitting}
              disabled={isSubmitting || code.length !== 6}
              style={styles.button}
            >
              {t('auth.verifyCode')}
            </Button>
            <Button
              mode="text"
              onPress={handleResend}
              disabled={resendCountdown > 0}
              style={styles.resendButton}
            >
              {resendCountdown > 0
                ? t('auth.resendIn', { seconds: resendCountdown.toString() })
                : t('auth.resendCode')}
            </Button>
          </>
        )}
      </Surface>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: 24,
    backgroundColor: '#f5f5f5',
  },
  card: {
    padding: 24,
    borderRadius: 16,
  },
  title: {
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    textAlign: 'center',
    marginBottom: 24,
    color: '#666',
  },
  input: {
    marginBottom: 8,
  },
  button: {
    marginTop: 16,
  },
  resendButton: {
    marginTop: 8,
  },
});
