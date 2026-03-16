const mockMessagingInstance = {
  requestPermission: jest.fn().mockResolvedValue(1),
  getToken: jest.fn().mockResolvedValue('fcm-token-123'),
  onMessage: jest.fn().mockReturnValue(jest.fn()),
  onNotificationOpenedApp: jest.fn().mockReturnValue(jest.fn()),
  getInitialNotification: jest.fn().mockResolvedValue(null),
  setBackgroundMessageHandler: jest.fn(),
};

jest.mock('@react-native-firebase/messaging', () => {
  const messagingFn = () => mockMessagingInstance;
  messagingFn.AuthorizationStatus = {
    AUTHORIZED: 1,
    PROVISIONAL: 2,
    NOT_DETERMINED: -1,
    DENIED: 0,
  };
  return messagingFn;
});

jest.mock('../api-client', () => ({
  apiClient: {
    post: jest.fn().mockResolvedValue({ data: {} }),
  },
}));

import { pushNotificationService } from '../push-notification-service';

describe('PushNotificationService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should request notification permission', async () => {
    await pushNotificationService.requestPermission();
    expect(mockMessagingInstance.requestPermission).toHaveBeenCalled();
  });

  it('should get FCM token', async () => {
    const token = await pushNotificationService.getDeviceToken();
    expect(token).toBe('fcm-token-123');
  });

  it('should register device token with backend', async () => {
    const { apiClient } = require('../api-client');
    await pushNotificationService.registerDeviceToken('fcm-token-123');
    expect(apiClient.post).toHaveBeenCalledWith('/patient/device/', {
      token: 'fcm-token-123',
      platform: expect.stringMatching(/ios|android/),
    });
  });

  it('should set up foreground message handler', () => {
    const handler = jest.fn();
    pushNotificationService.onForegroundMessage(handler);
    expect(mockMessagingInstance.onMessage).toHaveBeenCalled();
  });

  it('should set up notification opened handler', () => {
    const handler = jest.fn();
    pushNotificationService.onNotificationOpened(handler);
    expect(mockMessagingInstance.onNotificationOpenedApp).toHaveBeenCalled();
  });
});
