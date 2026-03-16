import messaging, { FirebaseMessagingTypes } from '@react-native-firebase/messaging';
import { Platform } from 'react-native';
import { apiClient } from './api-client';

export interface NotificationPayload {
  summaryId?: string;
  title?: string;
  body?: string;
}

export const pushNotificationService = {
  async requestPermission(): Promise<boolean> {
    const authStatus = await messaging().requestPermission();
    const enabled =
      authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
      authStatus === messaging.AuthorizationStatus.PROVISIONAL;
    return enabled;
  },

  async getDeviceToken(): Promise<string> {
    return messaging().getToken();
  },

  async registerDeviceToken(token: string): Promise<void> {
    await apiClient.post('/patient/device/', {
      token,
      platform: Platform.OS as 'ios' | 'android',
    });
  },

  async initializeAndRegister(): Promise<void> {
    const permissionGranted = await this.requestPermission();
    if (!permissionGranted) return;

    const token = await this.getDeviceToken();
    await this.registerDeviceToken(token);
  },

  onForegroundMessage(
    handler: (payload: NotificationPayload) => void
  ): () => void {
    return messaging().onMessage(
      (remoteMessage: FirebaseMessagingTypes.RemoteMessage) => {
        handler({
          summaryId: remoteMessage.data?.summary_id as string | undefined,
          title: remoteMessage.notification?.title,
          body: remoteMessage.notification?.body,
        });
      }
    );
  },

  onNotificationOpened(
    handler: (payload: NotificationPayload) => void
  ): () => void {
    return messaging().onNotificationOpenedApp(
      (remoteMessage: FirebaseMessagingTypes.RemoteMessage) => {
        handler({
          summaryId: remoteMessage.data?.summary_id as string | undefined,
          title: remoteMessage.notification?.title,
          body: remoteMessage.notification?.body,
        });
      }
    );
  },

  async getInitialNotification(): Promise<NotificationPayload | null> {
    const remoteMessage = await messaging().getInitialNotification();
    if (!remoteMessage) return null;
    return {
      summaryId: remoteMessage.data?.summary_id as string | undefined,
      title: remoteMessage.notification?.title,
      body: remoteMessage.notification?.body,
    };
  },
};
