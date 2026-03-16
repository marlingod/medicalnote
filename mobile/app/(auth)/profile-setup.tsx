import React, { useState, useCallback } from 'react';
import { View, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { Text, TextInput, Button, Surface, SegmentedButtons } from 'react-native-paper';
import { useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { apiClient } from '@/services/api-client';

export default function ProfileSetupScreen() {
  const { t, i18n } = useTranslation();
  const router = useRouter();

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [language, setLanguage] = useState<string>(i18n.language || 'en');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = useCallback(async () => {
    setIsSubmitting(true);
    try {
      await apiClient.patch('/patient/profile', {
        first_name: firstName,
        last_name: lastName,
        language_preference: language,
      });
      await i18n.changeLanguage(language);
      router.replace('/(tabs)/summaries');
    } catch {
      // Handle error
    } finally {
      setIsSubmitting(false);
    }
  }, [firstName, lastName, language, i18n, router]);

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <Surface style={styles.card} elevation={2}>
        <Text variant="headlineMedium" style={styles.title}>
          {t('profileSetup.title')}
        </Text>

        <TextInput
          label={t('profileSetup.firstName')}
          accessibilityLabel={t('profileSetup.firstName')}
          value={firstName}
          onChangeText={setFirstName}
          autoComplete="given-name"
          style={styles.input}
          mode="outlined"
        />

        <TextInput
          label={t('profileSetup.lastName')}
          accessibilityLabel={t('profileSetup.lastName')}
          value={lastName}
          onChangeText={setLastName}
          autoComplete="family-name"
          style={styles.input}
          mode="outlined"
        />

        <Text variant="bodyMedium" style={styles.label}>
          {t('profileSetup.language')}
        </Text>
        <SegmentedButtons
          value={language}
          onValueChange={setLanguage}
          buttons={[
            { value: 'en', label: 'English' },
            { value: 'es', label: 'Espanol' },
          ]}
          style={styles.segmented}
        />

        <Button
          mode="contained"
          onPress={handleSubmit}
          loading={isSubmitting}
          disabled={isSubmitting || !firstName.trim()}
          style={styles.button}
        >
          {t('profileSetup.continue')}
        </Button>
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
    marginBottom: 24,
  },
  input: {
    marginBottom: 12,
  },
  label: {
    marginBottom: 8,
    color: '#666',
  },
  segmented: {
    marginBottom: 12,
  },
  button: {
    marginTop: 16,
  },
});
