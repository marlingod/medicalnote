import React from 'react';
import { StyleSheet, View } from 'react-native';
import { SegmentedButtons } from 'react-native-paper';
import { useTranslation } from 'react-i18next';

interface LanguageToggleProps {
  currentLanguage: 'en' | 'es';
  onToggle: (language: 'en' | 'es') => void;
}

export function LanguageToggle({ currentLanguage, onToggle }: LanguageToggleProps) {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <SegmentedButtons
        value={currentLanguage}
        onValueChange={(value) => onToggle(value as 'en' | 'es')}
        buttons={[
          { value: 'en', label: t('summary.english') },
          { value: 'es', label: t('summary.spanish') },
        ]}
        density="small"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginVertical: 12,
  },
});
