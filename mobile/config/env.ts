export const ENV = {
  API_BASE_URL: process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1',
  FCM_VAPID_KEY: process.env.EXPO_PUBLIC_FCM_VAPID_KEY ?? '',
} as const;
