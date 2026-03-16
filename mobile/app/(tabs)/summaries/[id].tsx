import React, { useEffect, useState, useCallback } from 'react';
import { ScrollView, StyleSheet, View, Linking } from 'react-native';
import {
  Text,
  ActivityIndicator,
  Button,
  Banner,
  Divider,
  Surface,
} from 'react-native-paper';
import { useLocalSearchParams } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { summaryService } from '@/services/summary-service';
import { MedicalTermTooltip } from '@/components/medical-term-tooltip';
import { LanguageToggle } from '@/components/language-toggle';
import type { PatientSummary } from '@/types/api';

export default function SummaryDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { t } = useTranslation();
  const [summary, setSummary] = useState<PatientSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [displayLanguage, setDisplayLanguage] = useState<'en' | 'es'>('en');

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      try {
        const data = await summaryService.getSummaryDetail(id);
        setSummary(data);

        // Mark as read if not already viewed
        if (data.delivery_status !== 'viewed') {
          try {
            await summaryService.markAsRead(id);
          } catch {
            // Silently fail mark-as-read -- non-critical
          }
        }
      } catch {
        setError(t('common.error'));
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [id, t]);

  const handleContactDoctor = useCallback(() => {
    // In production, this would open a messaging screen or phone dialer
    // For Phase 1, we link to a phone call or email
    Linking.openURL('tel:+15551234567');
  }, []);

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" />
        <Text style={styles.loadingText}>{t('common.loading')}</Text>
      </View>
    );
  }

  if (error || !summary) {
    return (
      <View style={styles.centered}>
        <Text variant="bodyLarge">{error ?? t('common.error')}</Text>
      </View>
    );
  }

  const summaryText = displayLanguage === 'es' && summary.summary_es
    ? summary.summary_es
    : summary.summary_en;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Disclaimer Banner */}
      <Banner
        visible
        icon="information"
        style={styles.disclaimer}
      >
        {summary.disclaimer_text}
      </Banner>

      {/* Header */}
      <Surface style={styles.header} elevation={1}>
        <Text variant="titleLarge" style={styles.doctorName}>
          {summary.doctor_name}
        </Text>
        <Text variant="bodyMedium" style={styles.date}>
          {t('summary.visitDate')}: {summary.encounter_date}
        </Text>
      </Surface>

      {/* Language Toggle */}
      {summary.summary_es ? (
        <LanguageToggle
          currentLanguage={displayLanguage}
          onToggle={setDisplayLanguage}
        />
      ) : null}

      {/* Summary Text */}
      <Surface style={styles.summarySection} elevation={1}>
        <Text variant="bodyLarge" style={styles.summaryText}>
          {summaryText}
        </Text>
      </Surface>

      {/* Medical Terms */}
      {summary.medical_terms_explained.length > 0 && (
        <Surface style={styles.termsSection} elevation={1}>
          <Text variant="titleSmall" style={styles.termsTitle}>
            {t('summary.tapToExplain')}
          </Text>
          <Divider style={styles.divider} />
          {summary.medical_terms_explained.map((termObj) => (
            <MedicalTermTooltip
              key={termObj.term}
              term={termObj.term}
              explanation={termObj.explanation}
            />
          ))}
        </Surface>
      )}

      {/* Contact Doctor */}
      <Button
        mode="outlined"
        icon="phone"
        onPress={handleContactDoctor}
        style={styles.contactButton}
      >
        {t('summary.contactDoctor')}
      </Button>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  content: {
    paddingBottom: 32,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  loadingText: {
    marginTop: 12,
  },
  disclaimer: {
    backgroundColor: '#fff3e0',
  },
  header: {
    margin: 16,
    padding: 16,
    borderRadius: 12,
  },
  doctorName: {
    fontWeight: '600',
  },
  date: {
    color: '#666',
    marginTop: 4,
  },
  summarySection: {
    margin: 16,
    marginTop: 0,
    padding: 16,
    borderRadius: 12,
  },
  summaryText: {
    lineHeight: 26,
    color: '#333',
  },
  termsSection: {
    margin: 16,
    marginTop: 0,
    padding: 16,
    borderRadius: 12,
  },
  termsTitle: {
    color: '#666',
    marginBottom: 8,
  },
  divider: {
    marginBottom: 8,
  },
  contactButton: {
    marginHorizontal: 16,
    marginTop: 8,
  },
});
