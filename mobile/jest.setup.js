// Polyfill __ExpoImportMetaRegistry to prevent Expo SDK 55 runtime errors in Jest
if (typeof globalThis.__ExpoImportMetaRegistry === 'undefined') {
  globalThis.__ExpoImportMetaRegistry = {
    register: jest.fn(),
    get: jest.fn(() => ({})),
  };
}

// Mock expo/src/winter to prevent import errors in Jest with Expo SDK 55
jest.mock('expo/src/winter', () => {});
jest.mock('expo/src/winter/runtime.native', () => {});

// Global mocks for native modules that cannot be loaded in Jest

// Mock react-native-mmkv
jest.mock('react-native-mmkv', () => {
  const stores = {};
  return {
    MMKV: jest.fn().mockImplementation((opts) => {
      const id = opts?.id || 'default';
      if (!stores[id]) {
        stores[id] = {};
      }
      const store = stores[id];
      return {
        set: jest.fn((key, value) => { store[key] = value; }),
        getString: jest.fn((key) => store[key] ?? undefined),
        getNumber: jest.fn((key) => store[key] ?? undefined),
        getBoolean: jest.fn((key) => store[key] ?? undefined),
        delete: jest.fn((key) => { delete store[key]; }),
        clearAll: jest.fn(() => { Object.keys(store).forEach(k => delete store[k]); }),
        contains: jest.fn((key) => key in store),
        getAllKeys: jest.fn(() => Object.keys(store)),
      };
    }),
  };
});

// Mock expo-secure-store
jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}));

// Mock expo-localization
jest.mock('expo-localization', () => ({
  getLocales: jest.fn(() => [{ languageCode: 'en', languageTag: 'en-US' }]),
  getCalendars: jest.fn(() => [{ calendar: 'gregory' }]),
}));

// Mock expo-constants
jest.mock('expo-constants', () => ({
  expoConfig: { version: '1.0.0' },
  default: { expoConfig: { version: '1.0.0' } },
}));

// Mock @react-native-firebase/messaging
jest.mock('@react-native-firebase/messaging', () => {
  const mockMessaging = {
    requestPermission: jest.fn().mockResolvedValue(1),
    getToken: jest.fn().mockResolvedValue('mock-fcm-token'),
    onMessage: jest.fn().mockReturnValue(jest.fn()),
    onNotificationOpenedApp: jest.fn().mockReturnValue(jest.fn()),
    getInitialNotification: jest.fn().mockResolvedValue(null),
    setBackgroundMessageHandler: jest.fn(),
  };
  const messagingFn = () => mockMessaging;
  messagingFn.AuthorizationStatus = {
    AUTHORIZED: 1,
    PROVISIONAL: 2,
    NOT_DETERMINED: -1,
    DENIED: 0,
  };
  return messagingFn;
});

// Mock @react-native-firebase/app
jest.mock('@react-native-firebase/app', () => ({
  firebase: {
    app: jest.fn(),
    apps: [],
  },
}));

// Mock @react-native-community/netinfo
jest.mock('@react-native-community/netinfo', () => ({
  addEventListener: jest.fn(() => jest.fn()),
  fetch: jest.fn().mockResolvedValue({ isConnected: true, isInternetReachable: true }),
}));

// Mock expo-router
jest.mock('expo-router', () => ({
  Slot: () => null,
  Stack: Object.assign(
    ({ children }) => children || null,
    { Screen: ({ children }) => children || null }
  ),
  Tabs: Object.assign(
    ({ children }) => children || null,
    { Screen: ({ children }) => children || null }
  ),
  Redirect: ({ href }) => null,
  useRouter: () => ({ push: jest.fn(), replace: jest.fn(), back: jest.fn() }),
  useSegments: () => ['(tabs)'],
  useLocalSearchParams: () => ({ id: 'test-id' }),
  Link: ({ children }) => children,
}));
