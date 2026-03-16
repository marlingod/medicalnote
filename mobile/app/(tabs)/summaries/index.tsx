import React, { useEffect, useState, useCallback } from 'react';
import { FlatList, StyleSheet, RefreshControl, View } from 'react-native';
import { Text, ActivityIndicator, Button } from 'react-native-paper';
import { useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { summaryService } from '@/services/summary-service';
import { SummaryCard } from '@/components/summary-card';
import type { PatientSummary } from '@/types/api';

export default function SummaryListScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const [summaries, setSummaries] = useState<PatientSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSummaries = useCallback(async () => {
    setError(null);
    try {
      const data = await summaryService.getSummaries();
      setSummaries(data);
    } catch {
      setError(t('common.error'));
    }
  }, [t]);

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      await fetchSummaries();
      setIsLoading(false);
    };
    load();
  }, [fetchSummaries]);

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    await fetchSummaries();
    setIsRefreshing(false);
  }, [fetchSummaries]);

  const handleSummaryPress = useCallback(
    (id: string) => {
      router.push(`/(tabs)/summaries/${id}` as const);
    },
    [router]
  );

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" />
        <Text style={styles.loadingText}>{t('common.loading')}</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centered}>
        <Text variant="bodyLarge">{error}</Text>
        <Button mode="contained" onPress={fetchSummaries} style={styles.retryButton}>
          {t('common.retry')}
        </Button>
      </View>
    );
  }

  if (summaries.length === 0) {
    return (
      <View style={styles.centered}>
        <Text variant="bodyLarge" style={styles.emptyText}>
          {t('summary.noSummaries')}
        </Text>
      </View>
    );
  }

  return (
    <FlatList
      data={summaries}
      keyExtractor={(item) => item.id}
      renderItem={({ item }) => (
        <SummaryCard summary={item} onPress={handleSummaryPress} />
      )}
      contentContainerStyle={styles.list}
      refreshControl={
        <RefreshControl refreshing={isRefreshing} onRefresh={handleRefresh} />
      }
    />
  );
}

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  loadingText: {
    marginTop: 12,
  },
  emptyText: {
    textAlign: 'center',
    color: '#666',
  },
  list: {
    paddingVertical: 8,
  },
  retryButton: {
    marginTop: 16,
  },
});
