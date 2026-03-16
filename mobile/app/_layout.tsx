import React, { useEffect } from 'react';
import { Slot, useRouter, useSegments } from 'expo-router';
import { PaperProvider, MD3LightTheme } from 'react-native-paper';
import { AuthProvider, useAuth } from '@/contexts/auth-context';
import { pushNotificationService } from '@/services/push-notification-service';
import '@/i18n';

const theme = {
  ...MD3LightTheme,
  colors: {
    ...MD3LightTheme.colors,
    primary: '#1976d2',
    secondary: '#455a64',
    surface: '#ffffff',
    background: '#f5f5f5',
  },
};

function RootLayoutNav() {
  const { isAuthenticated, isLoading } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;

    const inAuthGroup = segments[0] === '(auth)';

    if (!isAuthenticated && !inAuthGroup) {
      router.replace('/(auth)/login');
    } else if (isAuthenticated && inAuthGroup) {
      router.replace('/(tabs)/summaries');
    }
  }, [isAuthenticated, isLoading, segments, router]);

  useEffect(() => {
    if (!isAuthenticated) return;

    // Register device for push notifications after login
    pushNotificationService.initializeAndRegister().catch(() => {
      // Silently fail -- push notifications are non-critical
    });

    // Handle notification that opened the app from killed state
    pushNotificationService.getInitialNotification().then((payload) => {
      if (payload?.summaryId) {
        router.push(`/(tabs)/summaries/${payload.summaryId}`);
      }
    });

    // Handle notification taps while app is in background
    const unsubscribeOpened = pushNotificationService.onNotificationOpened((payload) => {
      if (payload?.summaryId) {
        router.push(`/(tabs)/summaries/${payload.summaryId}`);
      }
    });

    // Handle foreground notifications (show in-app banner)
    const unsubscribeForeground = pushNotificationService.onForegroundMessage((payload) => {
      // In-app notification handling -- could show a Snackbar or in-app alert
      if (payload?.summaryId) {
        // Optionally refresh summary list
      }
    });

    return () => {
      unsubscribeOpened();
      unsubscribeForeground();
    };
  }, [isAuthenticated, router]);

  return <Slot />;
}

export default function RootLayout() {
  return (
    <PaperProvider theme={theme}>
      <AuthProvider>
        <RootLayoutNav />
      </AuthProvider>
    </PaperProvider>
  );
}
