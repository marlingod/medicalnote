import React, { useState, useCallback } from 'react';
import { ScrollView, StyleSheet, View, Alert } from 'react-native';
import {
  Text,
  List,
  Divider,
  Button,
  Switch,
  SegmentedButtons,
} from 'react-native-paper';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/contexts/auth-context';
import Constants from 'expo-constants';

export default function ProfileScreen() {
  const { t, i18n } = useTranslation();
  const { logout } = useAuth();
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [language, setLanguage] = useState(i18n.language || 'en');

  const handleLanguageChange = useCallback(
    async (lang: string) => {
      setLanguage(lang);
      await i18n.changeLanguage(lang);
    },
    [i18n]
  );

  const handleLogout = useCallback(() => {
    Alert.alert(
      t('profile.logout'),
      t('profile.logoutConfirm'),
      [
        { text: t('common.cancel'), style: 'cancel' },
        {
          text: t('profile.logout'),
          style: 'destructive',
          onPress: logout,
        },
      ]
    );
  }, [logout, t]);

  const appVersion = Constants.expoConfig?.version ?? '1.0.0';

  return (
    <ScrollView style={styles.container}>
      <Text variant="headlineSmall" style={styles.title}>
        {t('profile.title')}
      </Text>

      {/* Language */}
      <List.Section>
        <List.Subheader>{t('profile.language')}</List.Subheader>
        <View style={styles.settingRow}>
          <SegmentedButtons
            value={language}
            onValueChange={handleLanguageChange}
            buttons={[
              { value: 'en', label: t('summary.english') },
              { value: 'es', label: t('summary.spanish') },
            ]}
          />
        </View>
      </List.Section>

      <Divider />

      {/* Notifications */}
      <List.Section>
        <List.Subheader>{t('profile.notifications')}</List.Subheader>
        <List.Item
          title={t('profile.notifications')}
          description={
            notificationsEnabled
              ? t('profile.notificationsEnabled')
              : t('profile.notificationsDisabled')
          }
          right={() => (
            <Switch
              value={notificationsEnabled}
              onValueChange={setNotificationsEnabled}
            />
          )}
        />
      </List.Section>

      <Divider />

      {/* Privacy */}
      <List.Section>
        <List.Subheader>{t('profile.privacy')}</List.Subheader>
        <List.Item
          title={t('profile.privacy')}
          left={(props) => <List.Icon {...props} icon="shield-lock" />}
          right={(props) => <List.Icon {...props} icon="chevron-right" />}
        />
      </List.Section>

      <Divider />

      {/* Version */}
      <List.Item
        title={t('profile.version')}
        description={appVersion}
        left={(props) => <List.Icon {...props} icon="information" />}
      />

      {/* Logout */}
      <Button
        mode="outlined"
        onPress={handleLogout}
        style={styles.logoutButton}
        textColor="#d32f2f"
      >
        {t('profile.logout')}
      </Button>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  title: {
    padding: 16,
    fontWeight: '600',
  },
  settingRow: {
    paddingHorizontal: 16,
    paddingBottom: 12,
  },
  logoutButton: {
    margin: 16,
    borderColor: '#d32f2f',
  },
});
