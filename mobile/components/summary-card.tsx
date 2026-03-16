import React from 'react';
import { StyleSheet } from 'react-native';
import { Card, Text, Badge, Chip } from 'react-native-paper';
import { useTranslation } from 'react-i18next';
import type { PatientSummary } from '@/types/api';

interface SummaryCardProps {
  summary: PatientSummary;
  onPress: (id: string) => void;
}

export function SummaryCard({ summary, onPress }: SummaryCardProps) {
  const { t } = useTranslation();
  const isNew = summary.delivery_status === 'sent' && !summary.viewed_at;
  const previewText = summary.summary_en.substring(0, 120) + (summary.summary_en.length > 120 ? '...' : '');

  return (
    <Card
      style={[styles.card, isNew && styles.cardNew]}
      onPress={() => onPress(summary.id)}
      mode="elevated"
    >
      <Card.Content>
        <Text variant="titleMedium" style={styles.doctorName}>
          {summary.doctor_name}
        </Text>
        <Text variant="bodySmall" style={styles.date}>
          {t('summary.visitDate')}: {summary.encounter_date}
        </Text>
        <Text variant="bodyMedium" style={styles.preview} numberOfLines={2}>
          {previewText}
        </Text>
        {isNew && (
          <Chip style={styles.badge} compact textStyle={styles.badgeText}>
            {t('summary.new')}
          </Chip>
        )}
      </Card.Content>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    marginHorizontal: 16,
    marginVertical: 6,
  },
  cardNew: {
    borderLeftWidth: 4,
    borderLeftColor: '#1976d2',
  },
  doctorName: {
    fontWeight: '600',
  },
  date: {
    color: '#666',
    marginTop: 4,
  },
  preview: {
    marginTop: 8,
    color: '#444',
  },
  badge: {
    alignSelf: 'flex-start',
    marginTop: 8,
    backgroundColor: '#e3f2fd',
  },
  badgeText: {
    color: '#1976d2',
    fontSize: 12,
  },
});
