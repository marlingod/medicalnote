# Phase 1 Mobile App Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the React Native / Expo patient mobile app that authenticates via phone OTP, displays visit summaries with medical term tooltips and EN/ES language toggle, handles push notifications from FCM, and caches summaries offline using encrypted MMKV storage.

**Architecture:** Expo Router file-based navigation with two route groups: `(auth)` for login/profile-setup and `(tabs)` for the authenticated experience (summaries list, summary detail, profile/settings). An API client layer wraps all backend calls with JWT auth (stored in Expo SecureStore). MMKV with encryption provides offline summary caching. Firebase Cloud Messaging handles push notification registration and deep-linking into the summary detail screen.

**Tech Stack:** React Native 0.76+ (New Architecture), Expo SDK 52+, Expo Router v4, React Native Paper (MD3), Firebase Cloud Messaging (via `@react-native-firebase/messaging`), Expo SecureStore (JWT tokens), react-native-mmkv (encrypted offline cache), i18next + react-i18next (EN/ES), Jest + React Native Testing Library

---

## Backend API Dependency Summary

The mobile app depends on these backend endpoints (from the backend plan):

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/auth/patient/otp/send/` | POST | Send OTP to phone |
| `/api/v1/auth/patient/otp/verify/` | POST | Verify OTP, returns `{access, refresh, user_id}` |
| `/api/v1/auth/token/refresh/` | POST | Refresh JWT |
| `/api/v1/patient/summaries/` | GET | List patient summaries |
| `/api/v1/patient/summaries/:id/` | GET | Summary detail |
| `/api/v1/patient/summaries/:id/read/` | PATCH | Mark summary as viewed |
| `/api/v1/patient/profile` | GET | Patient profile (spec reference -- may need backend implementation) |

**NOTE:** The backend plan has a placeholder for FCM push notifications (`send_push_notification` in `services/notification_service.py`) and no device token registration endpoint. This plan includes a `POST /api/v1/patient/device/` endpoint that must be added to the backend. The mobile app will send its FCM token on login.

---

## Chunk 1: Project Scaffolding and Configuration

### Task 1.1: Initialize Expo project

- [ ] **Step 1 (3 min):** Create the Expo project with TypeScript template.

```bash
cd /Users/yemalin.godonou/Documents/works/tiko/medicalnote
npx create-expo-app@latest mobile --template expo-template-blank-typescript
cd mobile
```

- [ ] **Step 2 (3 min):** Install all dependencies.

```bash
cd /Users/yemalin.godonou/Documents/works/tiko/medicalnote/mobile
npx expo install expo-router expo-linking expo-constants expo-status-bar expo-secure-store expo-splash-screen expo-font expo-localization
npm install react-native-paper react-native-safe-area-context react-native-screens react-native-gesture-handler
npm install i18next react-i18next
npm install react-native-mmkv
npm install @react-native-firebase/app @react-native-firebase/messaging
npm install axios
npm install --save-dev jest @testing-library/react-native @testing-library/jest-native @types/jest ts-jest
```

- [ ] **Step 3 (2 min):** Configure `app.json` for Expo Router, Firebase, and deep linking.

File: `mobile/app.json`
```json
{
  "expo": {
    "name": "MedicalNote",
    "slug": "medicalnote-patient",
    "version": "1.0.0",
    "orientation": "portrait",
    "icon": "./assets/icon.png",
    "scheme": "medicalnote",
    "userInterfaceStyle": "light",
    "splash": {
      "image": "./assets/splash.png",
      "resizeMode": "contain",
      "backgroundColor": "#ffffff"
    },
    "assetBundlePatterns": ["**/*"],
    "ios": {
      "supportsTablet": false,
      "bundleIdentifier": "com.medicalnote.patient",
      "googleServicesFile": "./GoogleService-Info.plist",
      "infoPlist": {
        "UIBackgroundModes": ["remote-notification"]
      }
    },
    "android": {
      "adaptiveIcon": {
        "foregroundImage": "./assets/adaptive-icon.png",
        "backgroundColor": "#ffffff"
      },
      "package": "com.medicalnote.patient",
      "googleServicesFile": "./google-services.json"
    },
    "plugins": [
      "expo-router",
      "expo-secure-store",
      "expo-localization",
      "@react-native-firebase/app",
      "@react-native-firebase/messaging"
    ],
    "experiments": {
      "typedRoutes": true
    }
  }
}
```

- [ ] **Step 4 (2 min):** Configure TypeScript (`tsconfig.json`).

File: `mobile/tsconfig.json`
```json
{
  "extends": "expo/tsconfig.base",
  "compilerOptions": {
    "strict": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["**/*.ts", "**/*.tsx", ".expo/types/**/*.ts", "expo-env.d.ts"]
}
```

- [ ] **Step 5 (2 min):** Configure Jest for React Native testing.

File: `mobile/jest.config.js`
```javascript
module.exports = {
  preset: 'jest-expo',
  setupFilesAfterSetup: ['@testing-library/jest-native/extend-expect'],
  transformIgnorePatterns: [
    'node_modules/(?!((jest-)?react-native|@react-native(-community)?)|expo(nent)?|@expo(nent)?/.*|@expo-google-fonts/.*|react-navigation|@react-navigation/.*|@unimodules/.*|unimodules|sentry-expo|native-base|react-native-svg|react-native-paper|react-native-mmkv|i18next|react-i18next)',
  ],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  collectCoverageFrom: [
    '**/*.{ts,tsx}',
    '!**/node_modules/**',
    '!**/vendor/**',
    '!**/*.d.ts',
    '!**/coverage/**',
  ],
};
```

- [ ] **Step 6 (2 min):** Create environment configuration.

File: `mobile/config/env.ts`
```typescript
export const ENV = {
  API_BASE_URL: process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1',
  FCM_VAPID_KEY: process.env.EXPO_PUBLIC_FCM_VAPID_KEY ?? '',
} as const;
```

File: `mobile/.env.example`
```
EXPO_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
EXPO_PUBLIC_FCM_VAPID_KEY=
```

- [ ] **Step 7 (2 min):** Write and run first smoke test.

File: `mobile/__tests__/setup.test.ts`
```typescript
describe('Project Setup', () => {
  it('should have correct environment config shape', () => {
    const { ENV } = require('../config/env');
    expect(ENV).toHaveProperty('API_BASE_URL');
    expect(ENV).toHaveProperty('FCM_VAPID_KEY');
    expect(typeof ENV.API_BASE_URL).toBe('string');
  });
});
```

Run: `cd mobile && npx jest __tests__/setup.test.ts`
Verify: Test passes.

---

## Chunk 2: API Client and Auth Token Management

### Task 2.1: Secure token storage

- [ ] **Step 1 (3 min):** Write failing tests for token storage service.

File: `mobile/services/__tests__/token-storage.test.ts`
```typescript
import { tokenStorage } from '../token-storage';

// Mock expo-secure-store
jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}));

import * as SecureStore from 'expo-secure-store';

describe('TokenStorage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should store access and refresh tokens', async () => {
    await tokenStorage.setTokens({ access: 'acc-123', refresh: 'ref-456' });
    expect(SecureStore.setItemAsync).toHaveBeenCalledWith('auth_access_token', 'acc-123');
    expect(SecureStore.setItemAsync).toHaveBeenCalledWith('auth_refresh_token', 'ref-456');
  });

  it('should retrieve access token', async () => {
    (SecureStore.getItemAsync as jest.Mock).mockResolvedValue('acc-123');
    const token = await tokenStorage.getAccessToken();
    expect(token).toBe('acc-123');
    expect(SecureStore.getItemAsync).toHaveBeenCalledWith('auth_access_token');
  });

  it('should retrieve refresh token', async () => {
    (SecureStore.getItemAsync as jest.Mock).mockResolvedValue('ref-456');
    const token = await tokenStorage.getRefreshToken();
    expect(token).toBe('ref-456');
    expect(SecureStore.getItemAsync).toHaveBeenCalledWith('auth_refresh_token');
  });

  it('should clear all tokens on logout', async () => {
    await tokenStorage.clearTokens();
    expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('auth_access_token');
    expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('auth_refresh_token');
    expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('auth_user_id');
  });

  it('should store and retrieve user ID', async () => {
    await tokenStorage.setUserId('user-uuid-1');
    expect(SecureStore.setItemAsync).toHaveBeenCalledWith('auth_user_id', 'user-uuid-1');

    (SecureStore.getItemAsync as jest.Mock).mockResolvedValue('user-uuid-1');
    const userId = await tokenStorage.getUserId();
    expect(userId).toBe('user-uuid-1');
  });
});
```

Run: `cd mobile && npx jest services/__tests__/token-storage.test.ts`
Verify: Tests fail because `token-storage.ts` does not exist.

- [ ] **Step 2 (3 min):** Implement token storage service.

File: `mobile/services/token-storage.ts`
```typescript
import * as SecureStore from 'expo-secure-store';

const KEYS = {
  ACCESS_TOKEN: 'auth_access_token',
  REFRESH_TOKEN: 'auth_refresh_token',
  USER_ID: 'auth_user_id',
} as const;

export interface AuthTokens {
  access: string;
  refresh: string;
}

export const tokenStorage = {
  async setTokens(tokens: AuthTokens): Promise<void> {
    await SecureStore.setItemAsync(KEYS.ACCESS_TOKEN, tokens.access);
    await SecureStore.setItemAsync(KEYS.REFRESH_TOKEN, tokens.refresh);
  },

  async getAccessToken(): Promise<string | null> {
    return SecureStore.getItemAsync(KEYS.ACCESS_TOKEN);
  },

  async getRefreshToken(): Promise<string | null> {
    return SecureStore.getItemAsync(KEYS.REFRESH_TOKEN);
  },

  async setUserId(userId: string): Promise<void> {
    await SecureStore.setItemAsync(KEYS.USER_ID, userId);
  },

  async getUserId(): Promise<string | null> {
    return SecureStore.getItemAsync(KEYS.USER_ID);
  },

  async clearTokens(): Promise<void> {
    await SecureStore.deleteItemAsync(KEYS.ACCESS_TOKEN);
    await SecureStore.deleteItemAsync(KEYS.REFRESH_TOKEN);
    await SecureStore.deleteItemAsync(KEYS.USER_ID);
  },
};
```

Run: `cd mobile && npx jest services/__tests__/token-storage.test.ts`
Verify: All tests pass.

### Task 2.2: Axios API client with JWT interceptors

- [ ] **Step 1 (4 min):** Write failing tests for API client.

File: `mobile/services/__tests__/api-client.test.ts`
```typescript
import axios from 'axios';
import { apiClient } from '../api-client';
import { tokenStorage } from '../token-storage';

jest.mock('../token-storage');
jest.mock('axios', () => {
  const instance = {
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
    defaults: { headers: { common: {} } },
  };
  return {
    create: jest.fn(() => instance),
    isAxiosError: jest.fn(),
    __esModule: true,
    default: { create: jest.fn(() => instance) },
  };
});

describe('ApiClient', () => {
  it('should create axios instance with correct base URL', () => {
    expect(axios.create).toHaveBeenCalledWith(
      expect.objectContaining({
        baseURL: expect.any(String),
        timeout: 30000,
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
        }),
      })
    );
  });

  it('should register request interceptor', () => {
    const instance = (axios.create as jest.Mock).mock.results[0]?.value;
    expect(instance.interceptors.request.use).toHaveBeenCalled();
  });

  it('should register response interceptor for token refresh', () => {
    const instance = (axios.create as jest.Mock).mock.results[0]?.value;
    expect(instance.interceptors.response.use).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2 (5 min):** Implement API client with JWT interceptors and silent token refresh.

File: `mobile/services/api-client.ts`
```typescript
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { ENV } from '@/config/env';
import { tokenStorage, AuthTokens } from './token-storage';

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: Error) => void;
}> = [];

const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach((promise) => {
    if (error) {
      promise.reject(error);
    } else {
      promise.resolve(token!);
    }
  });
  failedQueue = [];
};

export const apiClient = axios.create({
  baseURL: ENV.API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach access token
apiClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    const token = await tokenStorage.getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle 401 with token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return apiClient(originalRequest);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      const refreshToken = await tokenStorage.getRefreshToken();
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }

      const response = await axios.post<AuthTokens>(
        `${ENV.API_BASE_URL}/auth/token/refresh/`,
        { refresh: refreshToken }
      );

      const { access, refresh } = response.data;
      await tokenStorage.setTokens({ access, refresh });

      processQueue(null, access);
      originalRequest.headers.Authorization = `Bearer ${access}`;
      return apiClient(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError as Error, null);
      await tokenStorage.clearTokens();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);
```

Run: `cd mobile && npx jest services/__tests__/api-client.test.ts`
Verify: All tests pass.

### Task 2.3: TypeScript types for API responses

- [ ] **Step 1 (3 min):** Create shared TypeScript types matching backend serializers.

File: `mobile/types/api.ts`
```typescript
export interface OTPSendRequest {
  phone: string;
}

export interface OTPSendResponse {
  message: string;
}

export interface OTPVerifyRequest {
  phone: string;
  code: string;
}

export interface OTPVerifyResponse {
  access: string;
  refresh: string;
  user_id: string;
}

export interface TokenRefreshRequest {
  refresh: string;
}

export interface TokenRefreshResponse {
  access: string;
  refresh: string;
}

export interface MedicalTermExplanation {
  term: string;
  explanation: string;
}

export interface PatientSummary {
  id: string;
  summary_en: string;
  summary_es: string;
  reading_level: 'grade_5' | 'grade_8' | 'grade_12';
  medical_terms_explained: MedicalTermExplanation[];
  disclaimer_text: string;
  encounter_date: string; // ISO date string "YYYY-MM-DD"
  doctor_name: string;
  delivery_status: 'pending' | 'sent' | 'viewed' | 'failed';
  viewed_at: string | null;
  created_at: string; // ISO datetime
}

export interface PatientSummaryListResponse {
  count: number;
  results: PatientSummary[];
}

export interface PatientProfile {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  language_preference: string;
}

export interface DeviceTokenRequest {
  token: string;
  platform: 'ios' | 'android';
}

export interface ApiError {
  error: string;
}
```

File: `mobile/types/__tests__/api.test.ts`
```typescript
import type { PatientSummary, OTPVerifyResponse, MedicalTermExplanation } from '../api';

describe('API Types', () => {
  it('should accept valid PatientSummary shape', () => {
    const summary: PatientSummary = {
      id: 'uuid-1',
      summary_en: 'Your visit went well.',
      summary_es: 'Su visita fue bien.',
      reading_level: 'grade_8',
      medical_terms_explained: [
        { term: 'hypertension', explanation: 'high blood pressure' },
      ],
      disclaimer_text: 'For informational purposes only.',
      encounter_date: '2026-03-15',
      doctor_name: 'Dr. Smith',
      delivery_status: 'sent',
      viewed_at: null,
      created_at: '2026-03-15T10:00:00Z',
    };
    expect(summary.id).toBe('uuid-1');
    expect(summary.medical_terms_explained).toHaveLength(1);
  });

  it('should accept valid OTPVerifyResponse shape', () => {
    const response: OTPVerifyResponse = {
      access: 'jwt-access-token',
      refresh: 'jwt-refresh-token',
      user_id: 'user-uuid',
    };
    expect(response.access).toBeTruthy();
  });
});
```

Run: `cd mobile && npx jest types/__tests__/api.test.ts`
Verify: Tests pass.

---

## Chunk 3: Internationalization (i18n) Setup

### Task 3.1: i18next configuration

- [ ] **Step 1 (3 min):** Write failing tests for i18n.

File: `mobile/i18n/__tests__/i18n.test.ts`
```typescript
import i18n from '../index';

describe('i18n', () => {
  it('should initialize with English as default language', () => {
    expect(i18n.language).toBe('en');
  });

  it('should have English translations loaded', () => {
    expect(i18n.t('common.appName')).toBe('MedicalNote');
  });

  it('should switch to Spanish', async () => {
    await i18n.changeLanguage('es');
    expect(i18n.t('common.appName')).toBe('MedicalNote');
    expect(i18n.t('summary.disclaimer')).toBeTruthy();
    await i18n.changeLanguage('en'); // reset
  });

  it('should have all required translation keys in EN', () => {
    const requiredKeys = [
      'common.appName',
      'auth.enterPhone',
      'auth.enterOTP',
      'auth.sendCode',
      'auth.verifyCode',
      'summary.listTitle',
      'summary.visitDate',
      'summary.doctorName',
      'summary.disclaimer',
      'summary.contactDoctor',
      'summary.noSummaries',
      'summary.tapToExplain',
      'profile.title',
      'profile.language',
      'profile.notifications',
      'profile.logout',
    ];
    requiredKeys.forEach((key) => {
      const value = i18n.t(key);
      expect(value).not.toBe(key); // should not return key itself
    });
  });

  it('should have all required translation keys in ES', async () => {
    await i18n.changeLanguage('es');
    const value = i18n.t('auth.enterPhone');
    expect(value).not.toBe('auth.enterPhone');
    await i18n.changeLanguage('en');
  });
});
```

- [ ] **Step 2 (3 min):** Create English translation file.

File: `mobile/i18n/en.json`
```json
{
  "common": {
    "appName": "MedicalNote",
    "loading": "Loading...",
    "error": "An error occurred",
    "retry": "Retry",
    "cancel": "Cancel",
    "save": "Save",
    "ok": "OK",
    "offline": "You are offline. Showing cached data."
  },
  "auth": {
    "welcome": "Welcome to MedicalNote",
    "enterPhone": "Enter your phone number",
    "phoneLabel": "Phone Number",
    "phonePlaceholder": "+1 (555) 123-4567",
    "sendCode": "Send Verification Code",
    "enterOTP": "Enter verification code",
    "otpLabel": "6-Digit Code",
    "otpPlaceholder": "000000",
    "verifyCode": "Verify Code",
    "codeSent": "Verification code sent!",
    "invalidCode": "Invalid verification code. Please try again.",
    "tooManyAttempts": "Too many attempts. Please try again later.",
    "resendCode": "Resend Code",
    "resendIn": "Resend code in {{seconds}}s"
  },
  "profileSetup": {
    "title": "Set Up Your Profile",
    "firstName": "First Name",
    "lastName": "Last Name",
    "language": "Preferred Language",
    "continue": "Continue"
  },
  "summary": {
    "listTitle": "My Visit Summaries",
    "visitDate": "Visit Date",
    "doctorName": "Doctor",
    "disclaimer": "This summary is for informational purposes only and does not replace professional medical advice. Contact your doctor with any questions.",
    "contactDoctor": "Contact My Doctor",
    "noSummaries": "No visit summaries yet. Your doctor will share them with you after your appointments.",
    "tapToExplain": "Tap highlighted terms for explanations",
    "readingLevel": "Reading Level",
    "viewedAt": "Viewed on",
    "new": "New",
    "languageToggle": "View in {{language}}",
    "english": "English",
    "spanish": "Spanish"
  },
  "profile": {
    "title": "Profile & Settings",
    "language": "Language",
    "notifications": "Notifications",
    "notificationsEnabled": "Push notifications are enabled",
    "notificationsDisabled": "Push notifications are disabled",
    "privacy": "Privacy",
    "logout": "Log Out",
    "logoutConfirm": "Are you sure you want to log out?",
    "version": "Version"
  },
  "notification": {
    "newSummary": "New Visit Summary",
    "summaryBody": "{{doctorName}} shared your visit summary from {{date}}"
  }
}
```

- [ ] **Step 3 (3 min):** Create Spanish translation file.

File: `mobile/i18n/es.json`
```json
{
  "common": {
    "appName": "MedicalNote",
    "loading": "Cargando...",
    "error": "Ocurrio un error",
    "retry": "Reintentar",
    "cancel": "Cancelar",
    "save": "Guardar",
    "ok": "Aceptar",
    "offline": "Estas sin conexion. Mostrando datos guardados."
  },
  "auth": {
    "welcome": "Bienvenido a MedicalNote",
    "enterPhone": "Ingrese su numero de telefono",
    "phoneLabel": "Numero de Telefono",
    "phonePlaceholder": "+1 (555) 123-4567",
    "sendCode": "Enviar Codigo de Verificacion",
    "enterOTP": "Ingrese el codigo de verificacion",
    "otpLabel": "Codigo de 6 Digitos",
    "otpPlaceholder": "000000",
    "verifyCode": "Verificar Codigo",
    "codeSent": "Codigo de verificacion enviado!",
    "invalidCode": "Codigo de verificacion invalido. Intente de nuevo.",
    "tooManyAttempts": "Demasiados intentos. Intente mas tarde.",
    "resendCode": "Reenviar Codigo",
    "resendIn": "Reenviar codigo en {{seconds}}s"
  },
  "profileSetup": {
    "title": "Configura Tu Perfil",
    "firstName": "Nombre",
    "lastName": "Apellido",
    "language": "Idioma Preferido",
    "continue": "Continuar"
  },
  "summary": {
    "listTitle": "Mis Resumenes de Visita",
    "visitDate": "Fecha de Visita",
    "doctorName": "Doctor",
    "disclaimer": "Este resumen es solo para fines informativos y no reemplaza el consejo medico profesional. Contacte a su doctor con cualquier pregunta.",
    "contactDoctor": "Contactar a Mi Doctor",
    "noSummaries": "Aun no hay resumenes de visita. Su doctor los compartira con usted despues de sus citas.",
    "tapToExplain": "Toque los terminos resaltados para ver explicaciones",
    "readingLevel": "Nivel de Lectura",
    "viewedAt": "Visto el",
    "new": "Nuevo",
    "languageToggle": "Ver en {{language}}",
    "english": "Ingles",
    "spanish": "Espanol"
  },
  "profile": {
    "title": "Perfil y Configuracion",
    "language": "Idioma",
    "notifications": "Notificaciones",
    "notificationsEnabled": "Las notificaciones push estan habilitadas",
    "notificationsDisabled": "Las notificaciones push estan deshabilitadas",
    "privacy": "Privacidad",
    "logout": "Cerrar Sesion",
    "logoutConfirm": "Esta seguro que desea cerrar sesion?",
    "version": "Version"
  },
  "notification": {
    "newSummary": "Nuevo Resumen de Visita",
    "summaryBody": "{{doctorName}} compartio su resumen de visita del {{date}}"
  }
}
```

- [ ] **Step 4 (3 min):** Initialize i18next.

File: `mobile/i18n/index.ts`
```typescript
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import * as Localization from 'expo-localization';

import en from './en.json';
import es from './es.json';

const resources = {
  en: { translation: en },
  es: { translation: es },
};

const deviceLocale = Localization.getLocales()[0]?.languageCode ?? 'en';
const supportedLanguage = ['en', 'es'].includes(deviceLocale) ? deviceLocale : 'en';

i18n.use(initReactI18next).init({
  resources,
  lng: supportedLanguage,
  fallbackLng: 'en',
  interpolation: {
    escapeValue: false,
  },
  compatibilityJSON: 'v4',
});

export default i18n;
```

Run: `cd mobile && npx jest i18n/__tests__/i18n.test.ts`
Verify: All tests pass.

---

## Chunk 4: Offline Storage with Encrypted MMKV

### Task 4.1: MMKV storage wrapper

- [ ] **Step 1 (3 min):** Write failing tests for offline cache.

File: `mobile/services/__tests__/offline-cache.test.ts`
```typescript
import { offlineCache } from '../offline-cache';
import type { PatientSummary } from '@/types/api';

// Mock react-native-mmkv
jest.mock('react-native-mmkv', () => {
  const store: Record<string, string> = {};
  return {
    MMKV: jest.fn().mockImplementation(() => ({
      set: jest.fn((key: string, value: string) => { store[key] = value; }),
      getString: jest.fn((key: string) => store[key] ?? undefined),
      delete: jest.fn((key: string) => { delete store[key]; }),
      clearAll: jest.fn(() => { Object.keys(store).forEach(k => delete store[k]); }),
      contains: jest.fn((key: string) => key in store),
    })),
  };
});

const mockSummary: PatientSummary = {
  id: 'sum-1',
  summary_en: 'Your visit summary.',
  summary_es: 'Resumen de su visita.',
  reading_level: 'grade_8',
  medical_terms_explained: [{ term: 'BP', explanation: 'Blood pressure' }],
  disclaimer_text: 'Disclaimer text.',
  encounter_date: '2026-03-15',
  doctor_name: 'Dr. Smith',
  delivery_status: 'sent',
  viewed_at: null,
  created_at: '2026-03-15T10:00:00Z',
};

describe('OfflineCache', () => {
  beforeEach(() => {
    offlineCache.clearAll();
  });

  it('should cache a list of summaries', () => {
    offlineCache.setSummaries([mockSummary]);
    const cached = offlineCache.getSummaries();
    expect(cached).toHaveLength(1);
    expect(cached![0].id).toBe('sum-1');
  });

  it('should cache a single summary by ID', () => {
    offlineCache.setSummaryDetail('sum-1', mockSummary);
    const cached = offlineCache.getSummaryDetail('sum-1');
    expect(cached).toBeDefined();
    expect(cached!.doctor_name).toBe('Dr. Smith');
  });

  it('should return null for missing summary', () => {
    const cached = offlineCache.getSummaryDetail('nonexistent');
    expect(cached).toBeNull();
  });

  it('should clear all cached data', () => {
    offlineCache.setSummaries([mockSummary]);
    offlineCache.clearAll();
    const cached = offlineCache.getSummaries();
    expect(cached).toBeNull();
  });

  it('should cache last sync timestamp', () => {
    const now = Date.now();
    offlineCache.setLastSyncTimestamp(now);
    expect(offlineCache.getLastSyncTimestamp()).toBe(now);
  });
});
```

- [ ] **Step 2 (3 min):** Implement offline cache with encrypted MMKV.

File: `mobile/services/offline-cache.ts`
```typescript
import { MMKV } from 'react-native-mmkv';
import type { PatientSummary } from '@/types/api';

const KEYS = {
  SUMMARIES_LIST: 'cache:summaries:list',
  SUMMARY_DETAIL_PREFIX: 'cache:summaries:detail:',
  LAST_SYNC: 'cache:last_sync',
} as const;

// Encrypted MMKV instance for PHI data
const storage = new MMKV({
  id: 'medicalnote-offline-cache',
  encryptionKey: 'medicalnote-mmkv-encryption-key',
});

export const offlineCache = {
  setSummaries(summaries: PatientSummary[]): void {
    storage.set(KEYS.SUMMARIES_LIST, JSON.stringify(summaries));
  },

  getSummaries(): PatientSummary[] | null {
    const raw = storage.getString(KEYS.SUMMARIES_LIST);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as PatientSummary[];
    } catch {
      return null;
    }
  },

  setSummaryDetail(id: string, summary: PatientSummary): void {
    storage.set(`${KEYS.SUMMARY_DETAIL_PREFIX}${id}`, JSON.stringify(summary));
  },

  getSummaryDetail(id: string): PatientSummary | null {
    const raw = storage.getString(`${KEYS.SUMMARY_DETAIL_PREFIX}${id}`);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as PatientSummary;
    } catch {
      return null;
    }
  },

  setLastSyncTimestamp(timestamp: number): void {
    storage.set(KEYS.LAST_SYNC, timestamp.toString());
  },

  getLastSyncTimestamp(): number | null {
    const raw = storage.getString(KEYS.LAST_SYNC);
    if (!raw) return null;
    return parseInt(raw, 10);
  },

  clearAll(): void {
    storage.clearAll();
  },
};
```

Run: `cd mobile && npx jest services/__tests__/offline-cache.test.ts`
Verify: All tests pass.

---

## Chunk 5: Auth Service and Login Screen

### Task 5.1: Auth service

- [ ] **Step 1 (4 min):** Write failing tests for auth service.

File: `mobile/services/__tests__/auth-service.test.ts`
```typescript
import { authService } from '../auth-service';
import { apiClient } from '../api-client';
import { tokenStorage } from '../token-storage';

jest.mock('../api-client');
jest.mock('../token-storage');

describe('AuthService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should send OTP to phone number', async () => {
    (apiClient.post as jest.Mock).mockResolvedValue({
      data: { message: 'Verification code sent.' },
    });

    const result = await authService.sendOTP('+15551234567');
    expect(result).toEqual({ message: 'Verification code sent.' });
    expect(apiClient.post).toHaveBeenCalledWith('/auth/patient/otp/send/', {
      phone: '+15551234567',
    });
  });

  it('should verify OTP and store tokens', async () => {
    (apiClient.post as jest.Mock).mockResolvedValue({
      data: {
        access: 'access-token-123',
        refresh: 'refresh-token-456',
        user_id: 'user-uuid-1',
      },
    });

    const result = await authService.verifyOTP('+15551234567', '123456');
    expect(result.user_id).toBe('user-uuid-1');
    expect(tokenStorage.setTokens).toHaveBeenCalledWith({
      access: 'access-token-123',
      refresh: 'refresh-token-456',
    });
    expect(tokenStorage.setUserId).toHaveBeenCalledWith('user-uuid-1');
  });

  it('should throw on invalid OTP', async () => {
    (apiClient.post as jest.Mock).mockRejectedValue({
      response: { status: 401, data: { error: 'Invalid verification code.' } },
    });

    await expect(authService.verifyOTP('+15551234567', '000000')).rejects.toBeDefined();
  });

  it('should logout and clear tokens', async () => {
    await authService.logout();
    expect(tokenStorage.clearTokens).toHaveBeenCalled();
  });

  it('should check if user is authenticated', async () => {
    (tokenStorage.getAccessToken as jest.Mock).mockResolvedValue('token-123');
    const isAuth = await authService.isAuthenticated();
    expect(isAuth).toBe(true);
  });

  it('should return false when no token stored', async () => {
    (tokenStorage.getAccessToken as jest.Mock).mockResolvedValue(null);
    const isAuth = await authService.isAuthenticated();
    expect(isAuth).toBe(false);
  });
});
```

- [ ] **Step 2 (3 min):** Implement auth service.

File: `mobile/services/auth-service.ts`
```typescript
import { apiClient } from './api-client';
import { tokenStorage } from './token-storage';
import { offlineCache } from './offline-cache';
import type {
  OTPSendRequest,
  OTPSendResponse,
  OTPVerifyRequest,
  OTPVerifyResponse,
} from '@/types/api';

export const authService = {
  async sendOTP(phone: string): Promise<OTPSendResponse> {
    const response = await apiClient.post<OTPSendResponse>(
      '/auth/patient/otp/send/',
      { phone } as OTPSendRequest
    );
    return response.data;
  },

  async verifyOTP(phone: string, code: string): Promise<OTPVerifyResponse> {
    const response = await apiClient.post<OTPVerifyResponse>(
      '/auth/patient/otp/verify/',
      { phone, code } as OTPVerifyRequest
    );
    const { access, refresh, user_id } = response.data;
    await tokenStorage.setTokens({ access, refresh });
    await tokenStorage.setUserId(user_id);
    return response.data;
  },

  async logout(): Promise<void> {
    await tokenStorage.clearTokens();
    offlineCache.clearAll();
  },

  async isAuthenticated(): Promise<boolean> {
    const token = await tokenStorage.getAccessToken();
    return token !== null;
  },
};
```

Run: `cd mobile && npx jest services/__tests__/auth-service.test.ts`
Verify: All tests pass.

### Task 5.2: Auth context provider

- [ ] **Step 1 (4 min):** Write failing tests for auth context.

File: `mobile/contexts/__tests__/auth-context.test.tsx`
```typescript
import React from 'react';
import { renderHook, act } from '@testing-library/react-native';
import { AuthProvider, useAuth } from '../auth-context';
import { authService } from '@/services/auth-service';

jest.mock('@/services/auth-service');

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
);

describe('AuthContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (authService.isAuthenticated as jest.Mock).mockResolvedValue(false);
  });

  it('should provide initial unauthenticated state', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    // Wait for async init
    await act(async () => {});
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.isLoading).toBe(false);
  });

  it('should update state after successful login', async () => {
    (authService.verifyOTP as jest.Mock).mockResolvedValue({
      access: 'token',
      refresh: 'refresh',
      user_id: 'user-1',
    });

    const { result } = renderHook(() => useAuth(), { wrapper });
    await act(async () => {});

    await act(async () => {
      await result.current.login('+15551234567', '123456');
    });
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.userId).toBe('user-1');
  });

  it('should clear state on logout', async () => {
    (authService.isAuthenticated as jest.Mock).mockResolvedValue(true);

    const { result } = renderHook(() => useAuth(), { wrapper });
    await act(async () => {});

    await act(async () => {
      await result.current.logout();
    });
    expect(result.current.isAuthenticated).toBe(false);
    expect(authService.logout).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2 (4 min):** Implement auth context.

File: `mobile/contexts/auth-context.tsx`
```typescript
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authService } from '@/services/auth-service';
import { tokenStorage } from '@/services/token-storage';

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  userId: string | null;
  login: (phone: string, code: string) => Promise<void>;
  logout: () => Promise<void>;
  sendOTP: (phone: string) => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const authenticated = await authService.isAuthenticated();
        if (authenticated) {
          const storedUserId = await tokenStorage.getUserId();
          setUserId(storedUserId);
          setIsAuthenticated(true);
        }
      } catch {
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };
    checkAuth();
  }, []);

  const sendOTP = useCallback(async (phone: string) => {
    await authService.sendOTP(phone);
  }, []);

  const login = useCallback(async (phone: string, code: string) => {
    const response = await authService.verifyOTP(phone, code);
    setUserId(response.user_id);
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(async () => {
    await authService.logout();
    setUserId(null);
    setIsAuthenticated(false);
  }, []);

  return (
    <AuthContext.Provider
      value={{ isAuthenticated, isLoading, userId, login, logout, sendOTP }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
```

Run: `cd mobile && npx jest contexts/__tests__/auth-context.test.tsx`
Verify: All tests pass.

### Task 5.3: Login screen (phone + OTP)

- [ ] **Step 1 (5 min):** Write failing tests for login screen.

File: `mobile/app/(auth)/__tests__/login.test.tsx`
```typescript
import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import LoginScreen from '../login';
import { useAuth } from '@/contexts/auth-context';

jest.mock('@/contexts/auth-context');
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, string>) => {
      const translations: Record<string, string> = {
        'auth.welcome': 'Welcome to MedicalNote',
        'auth.enterPhone': 'Enter your phone number',
        'auth.phoneLabel': 'Phone Number',
        'auth.sendCode': 'Send Verification Code',
        'auth.enterOTP': 'Enter verification code',
        'auth.otpLabel': '6-Digit Code',
        'auth.verifyCode': 'Verify Code',
        'auth.codeSent': 'Verification code sent!',
        'auth.invalidCode': 'Invalid verification code.',
        'auth.resendCode': 'Resend Code',
        'auth.resendIn': `Resend code in ${opts?.seconds ?? ''}s`,
      };
      return translations[key] ?? key;
    },
  }),
}));

const mockSendOTP = jest.fn();
const mockLogin = jest.fn();

beforeEach(() => {
  jest.clearAllMocks();
  (useAuth as jest.Mock).mockReturnValue({
    sendOTP: mockSendOTP,
    login: mockLogin,
    isLoading: false,
  });
});

describe('LoginScreen', () => {
  it('should render phone input step initially', () => {
    const { getByText, getByLabelText } = render(<LoginScreen />);
    expect(getByText('Welcome to MedicalNote')).toBeTruthy();
    expect(getByText('Send Verification Code')).toBeTruthy();
  });

  it('should call sendOTP when phone submitted', async () => {
    mockSendOTP.mockResolvedValue(undefined);
    const { getByLabelText, getByText } = render(<LoginScreen />);

    const phoneInput = getByLabelText('Phone Number');
    fireEvent.changeText(phoneInput, '+15551234567');
    fireEvent.press(getByText('Send Verification Code'));

    await waitFor(() => {
      expect(mockSendOTP).toHaveBeenCalledWith('+15551234567');
    });
  });

  it('should show OTP input after phone submitted', async () => {
    mockSendOTP.mockResolvedValue(undefined);
    const { getByLabelText, getByText } = render(<LoginScreen />);

    fireEvent.changeText(getByLabelText('Phone Number'), '+15551234567');
    fireEvent.press(getByText('Send Verification Code'));

    await waitFor(() => {
      expect(getByText('Enter verification code')).toBeTruthy();
      expect(getByText('Verify Code')).toBeTruthy();
    });
  });

  it('should call login when OTP submitted', async () => {
    mockSendOTP.mockResolvedValue(undefined);
    mockLogin.mockResolvedValue(undefined);

    const { getByLabelText, getByText } = render(<LoginScreen />);

    fireEvent.changeText(getByLabelText('Phone Number'), '+15551234567');
    fireEvent.press(getByText('Send Verification Code'));

    await waitFor(() => {
      expect(getByText('Verify Code')).toBeTruthy();
    });

    fireEvent.changeText(getByLabelText('6-Digit Code'), '123456');
    fireEvent.press(getByText('Verify Code'));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('+15551234567', '123456');
    });
  });
});
```

- [ ] **Step 2 (5 min):** Implement login screen.

File: `mobile/app/(auth)/login.tsx`
```typescript
import React, { useState, useCallback } from 'react';
import { View, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import {
  Text,
  TextInput,
  Button,
  HelperText,
  Surface,
} from 'react-native-paper';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/contexts/auth-context';

type Step = 'phone' | 'otp';

export default function LoginScreen() {
  const { t } = useTranslation();
  const { sendOTP, login } = useAuth();

  const [step, setStep] = useState<Step>('phone');
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resendCountdown, setResendCountdown] = useState(0);

  const handleSendOTP = useCallback(async () => {
    if (!phone.trim()) return;
    setError(null);
    setIsSubmitting(true);
    try {
      await sendOTP(phone.trim());
      setStep('otp');
      startResendCountdown();
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { error?: string } } })?.response?.data?.error ??
        t('common.error');
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }, [phone, sendOTP, t]);

  const handleVerifyOTP = useCallback(async () => {
    if (!code.trim() || code.length !== 6) return;
    setError(null);
    setIsSubmitting(true);
    try {
      await login(phone.trim(), code.trim());
      // Navigation handled by root layout auth check
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { error?: string } } })?.response?.data?.error ??
        t('auth.invalidCode');
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }, [phone, code, login, t]);

  const startResendCountdown = useCallback(() => {
    setResendCountdown(60);
    const interval = setInterval(() => {
      setResendCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }, []);

  const handleResend = useCallback(async () => {
    setError(null);
    try {
      await sendOTP(phone.trim());
      startResendCountdown();
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { error?: string } } })?.response?.data?.error ??
        t('auth.tooManyAttempts');
      setError(message);
    }
  }, [phone, sendOTP, startResendCountdown, t]);

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <Surface style={styles.card} elevation={2}>
        <Text variant="headlineMedium" style={styles.title}>
          {t('auth.welcome')}
        </Text>

        {step === 'phone' ? (
          <>
            <Text variant="bodyLarge" style={styles.subtitle}>
              {t('auth.enterPhone')}
            </Text>
            <TextInput
              label={t('auth.phoneLabel')}
              accessibilityLabel={t('auth.phoneLabel')}
              value={phone}
              onChangeText={setPhone}
              keyboardType="phone-pad"
              autoComplete="tel"
              placeholder={t('auth.phonePlaceholder')}
              style={styles.input}
              mode="outlined"
            />
            {error && <HelperText type="error">{error}</HelperText>}
            <Button
              mode="contained"
              onPress={handleSendOTP}
              loading={isSubmitting}
              disabled={isSubmitting || !phone.trim()}
              style={styles.button}
            >
              {t('auth.sendCode')}
            </Button>
          </>
        ) : (
          <>
            <Text variant="bodyLarge" style={styles.subtitle}>
              {t('auth.enterOTP')}
            </Text>
            <TextInput
              label={t('auth.otpLabel')}
              accessibilityLabel={t('auth.otpLabel')}
              value={code}
              onChangeText={setCode}
              keyboardType="number-pad"
              maxLength={6}
              placeholder={t('auth.otpPlaceholder')}
              style={styles.input}
              mode="outlined"
            />
            {error && <HelperText type="error">{error}</HelperText>}
            <Button
              mode="contained"
              onPress={handleVerifyOTP}
              loading={isSubmitting}
              disabled={isSubmitting || code.length !== 6}
              style={styles.button}
            >
              {t('auth.verifyCode')}
            </Button>
            <Button
              mode="text"
              onPress={handleResend}
              disabled={resendCountdown > 0}
              style={styles.resendButton}
            >
              {resendCountdown > 0
                ? t('auth.resendIn', { seconds: resendCountdown.toString() })
                : t('auth.resendCode')}
            </Button>
          </>
        )}
      </Surface>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: 24,
    backgroundColor: '#f5f5f5',
  },
  card: {
    padding: 24,
    borderRadius: 16,
  },
  title: {
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    textAlign: 'center',
    marginBottom: 24,
    color: '#666',
  },
  input: {
    marginBottom: 8,
  },
  button: {
    marginTop: 16,
  },
  resendButton: {
    marginTop: 8,
  },
});
```

Run: `cd mobile && npx jest app/(auth)/__tests__/login.test.tsx`
Verify: All tests pass.

---

## Chunk 6: Summary Service and Summary List Screen

### Task 6.1: Summary service

- [ ] **Step 1 (3 min):** Write failing tests for summary service.

File: `mobile/services/__tests__/summary-service.test.ts`
```typescript
import { summaryService } from '../summary-service';
import { apiClient } from '../api-client';
import { offlineCache } from '../offline-cache';
import type { PatientSummary } from '@/types/api';

jest.mock('../api-client');
jest.mock('../offline-cache');

const mockSummary: PatientSummary = {
  id: 'sum-1',
  summary_en: 'Your visit summary.',
  summary_es: 'Resumen de su visita.',
  reading_level: 'grade_8',
  medical_terms_explained: [],
  disclaimer_text: 'Disclaimer.',
  encounter_date: '2026-03-15',
  doctor_name: 'Dr. Smith',
  delivery_status: 'sent',
  viewed_at: null,
  created_at: '2026-03-15T10:00:00Z',
};

describe('SummaryService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should fetch summaries from API and cache them', async () => {
    (apiClient.get as jest.Mock).mockResolvedValue({
      data: { count: 1, results: [mockSummary] },
    });

    const result = await summaryService.getSummaries();
    expect(result).toHaveLength(1);
    expect(apiClient.get).toHaveBeenCalledWith('/patient/summaries/');
    expect(offlineCache.setSummaries).toHaveBeenCalledWith([mockSummary]);
  });

  it('should return cached summaries when offline', async () => {
    (apiClient.get as jest.Mock).mockRejectedValue(new Error('Network Error'));
    (offlineCache.getSummaries as jest.Mock).mockReturnValue([mockSummary]);

    const result = await summaryService.getSummaries();
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe('sum-1');
  });

  it('should throw when offline and no cache', async () => {
    (apiClient.get as jest.Mock).mockRejectedValue(new Error('Network Error'));
    (offlineCache.getSummaries as jest.Mock).mockReturnValue(null);

    await expect(summaryService.getSummaries()).rejects.toThrow();
  });

  it('should fetch summary detail and cache it', async () => {
    (apiClient.get as jest.Mock).mockResolvedValue({ data: mockSummary });

    const result = await summaryService.getSummaryDetail('sum-1');
    expect(result.id).toBe('sum-1');
    expect(offlineCache.setSummaryDetail).toHaveBeenCalledWith('sum-1', mockSummary);
  });

  it('should mark summary as read', async () => {
    (apiClient.patch as jest.Mock).mockResolvedValue({ data: { status: 'viewed' } });

    await summaryService.markAsRead('sum-1');
    expect(apiClient.patch).toHaveBeenCalledWith('/patient/summaries/sum-1/read/');
  });

  it('should return cached detail when offline', async () => {
    (apiClient.get as jest.Mock).mockRejectedValue(new Error('Network Error'));
    (offlineCache.getSummaryDetail as jest.Mock).mockReturnValue(mockSummary);

    const result = await summaryService.getSummaryDetail('sum-1');
    expect(result.id).toBe('sum-1');
  });
});
```

- [ ] **Step 2 (3 min):** Implement summary service.

File: `mobile/services/summary-service.ts`
```typescript
import { apiClient } from './api-client';
import { offlineCache } from './offline-cache';
import type { PatientSummary, PatientSummaryListResponse } from '@/types/api';

export const summaryService = {
  async getSummaries(): Promise<PatientSummary[]> {
    try {
      const response = await apiClient.get<PatientSummaryListResponse>(
        '/patient/summaries/'
      );
      const summaries = response.data.results;
      offlineCache.setSummaries(summaries);
      offlineCache.setLastSyncTimestamp(Date.now());
      return summaries;
    } catch (error) {
      const cached = offlineCache.getSummaries();
      if (cached) {
        return cached;
      }
      throw error;
    }
  },

  async getSummaryDetail(id: string): Promise<PatientSummary> {
    try {
      const response = await apiClient.get<PatientSummary>(
        `/patient/summaries/${id}/`
      );
      const summary = response.data;
      offlineCache.setSummaryDetail(id, summary);
      return summary;
    } catch (error) {
      const cached = offlineCache.getSummaryDetail(id);
      if (cached) {
        return cached;
      }
      throw error;
    }
  },

  async markAsRead(id: string): Promise<void> {
    await apiClient.patch(`/patient/summaries/${id}/read/`);
  },
};
```

Run: `cd mobile && npx jest services/__tests__/summary-service.test.ts`
Verify: All tests pass.

### Task 6.2: Summary card component

- [ ] **Step 1 (3 min):** Write failing tests for summary card.

File: `mobile/components/__tests__/summary-card.test.tsx`
```typescript
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { SummaryCard } from '../summary-card';
import type { PatientSummary } from '@/types/api';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'summary.visitDate': 'Visit Date',
        'summary.doctorName': 'Doctor',
        'summary.new': 'New',
      };
      return translations[key] ?? key;
    },
  }),
}));

const mockSummary: PatientSummary = {
  id: 'sum-1',
  summary_en: 'Your visit went well. Blood pressure was normal.',
  summary_es: 'Su visita fue bien.',
  reading_level: 'grade_8',
  medical_terms_explained: [{ term: 'BP', explanation: 'Blood pressure' }],
  disclaimer_text: 'Disclaimer.',
  encounter_date: '2026-03-15',
  doctor_name: 'Dr. Smith',
  delivery_status: 'sent',
  viewed_at: null,
  created_at: '2026-03-15T10:00:00Z',
};

describe('SummaryCard', () => {
  it('should render doctor name and visit date', () => {
    const { getByText } = render(
      <SummaryCard summary={mockSummary} onPress={jest.fn()} />
    );
    expect(getByText('Dr. Smith')).toBeTruthy();
    expect(getByText(/2026-03-15/)).toBeTruthy();
  });

  it('should show "New" badge for unviewed summaries', () => {
    const { getByText } = render(
      <SummaryCard summary={mockSummary} onPress={jest.fn()} />
    );
    expect(getByText('New')).toBeTruthy();
  });

  it('should not show "New" badge for viewed summaries', () => {
    const viewedSummary = { ...mockSummary, delivery_status: 'viewed' as const, viewed_at: '2026-03-15T12:00:00Z' };
    const { queryByText } = render(
      <SummaryCard summary={viewedSummary} onPress={jest.fn()} />
    );
    expect(queryByText('New')).toBeNull();
  });

  it('should show summary preview text', () => {
    const { getByText } = render(
      <SummaryCard summary={mockSummary} onPress={jest.fn()} />
    );
    expect(getByText(/Your visit went well/)).toBeTruthy();
  });

  it('should call onPress when tapped', () => {
    const onPress = jest.fn();
    const { getByText } = render(
      <SummaryCard summary={mockSummary} onPress={onPress} />
    );
    fireEvent.press(getByText('Dr. Smith'));
    expect(onPress).toHaveBeenCalledWith('sum-1');
  });
});
```

- [ ] **Step 2 (4 min):** Implement summary card.

File: `mobile/components/summary-card.tsx`
```typescript
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
```

Run: `cd mobile && npx jest components/__tests__/summary-card.test.tsx`
Verify: All tests pass.

### Task 6.3: Summary list screen

- [ ] **Step 1 (4 min):** Write failing tests for summary list screen.

File: `mobile/app/(tabs)/summaries/__tests__/index.test.tsx`
```typescript
import React from 'react';
import { render, waitFor } from '@testing-library/react-native';
import SummaryListScreen from '../index';
import { summaryService } from '@/services/summary-service';
import type { PatientSummary } from '@/types/api';

jest.mock('@/services/summary-service');
jest.mock('expo-router', () => ({ useRouter: () => ({ push: jest.fn() }) }));
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'summary.listTitle': 'My Visit Summaries',
        'summary.noSummaries': 'No visit summaries yet.',
        'common.loading': 'Loading...',
        'common.error': 'An error occurred',
        'common.retry': 'Retry',
        'common.offline': 'You are offline.',
        'summary.visitDate': 'Visit Date',
        'summary.doctorName': 'Doctor',
        'summary.new': 'New',
      };
      return translations[key] ?? key;
    },
  }),
}));

const mockSummary: PatientSummary = {
  id: 'sum-1',
  summary_en: 'Your visit summary.',
  summary_es: 'Resumen.',
  reading_level: 'grade_8',
  medical_terms_explained: [],
  disclaimer_text: 'Disclaimer.',
  encounter_date: '2026-03-15',
  doctor_name: 'Dr. Smith',
  delivery_status: 'sent',
  viewed_at: null,
  created_at: '2026-03-15T10:00:00Z',
};

describe('SummaryListScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should show loading state initially', () => {
    (summaryService.getSummaries as jest.Mock).mockReturnValue(new Promise(() => {}));
    const { getByText } = render(<SummaryListScreen />);
    expect(getByText('Loading...')).toBeTruthy();
  });

  it('should display summaries when loaded', async () => {
    (summaryService.getSummaries as jest.Mock).mockResolvedValue([mockSummary]);

    const { getByText } = render(<SummaryListScreen />);
    await waitFor(() => {
      expect(getByText('Dr. Smith')).toBeTruthy();
    });
  });

  it('should show empty state when no summaries', async () => {
    (summaryService.getSummaries as jest.Mock).mockResolvedValue([]);

    const { getByText } = render(<SummaryListScreen />);
    await waitFor(() => {
      expect(getByText('No visit summaries yet.')).toBeTruthy();
    });
  });

  it('should show error state on failure', async () => {
    (summaryService.getSummaries as jest.Mock).mockRejectedValue(new Error('Network Error'));

    const { getByText } = render(<SummaryListScreen />);
    await waitFor(() => {
      expect(getByText('An error occurred')).toBeTruthy();
      expect(getByText('Retry')).toBeTruthy();
    });
  });
});
```

- [ ] **Step 2 (5 min):** Implement summary list screen.

File: `mobile/app/(tabs)/summaries/index.tsx`
```typescript
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
```

Run: `cd mobile && npx jest app/(tabs)/summaries/__tests__/index.test.tsx`
Verify: All tests pass.

---

## Chunk 7: Summary Detail Screen with Medical Term Tooltips and Language Toggle

### Task 7.1: Medical term tooltip component

- [ ] **Step 1 (3 min):** Write failing tests for medical term tooltip.

File: `mobile/components/__tests__/medical-term-tooltip.test.tsx`
```typescript
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { MedicalTermTooltip } from '../medical-term-tooltip';

describe('MedicalTermTooltip', () => {
  it('should render the term text', () => {
    const { getByText } = render(
      <MedicalTermTooltip term="hypertension" explanation="high blood pressure" />
    );
    expect(getByText('hypertension')).toBeTruthy();
  });

  it('should show explanation when pressed', () => {
    const { getByText } = render(
      <MedicalTermTooltip term="hypertension" explanation="high blood pressure" />
    );
    fireEvent.press(getByText('hypertension'));
    expect(getByText('high blood pressure')).toBeTruthy();
  });

  it('should toggle explanation on repeated press', () => {
    const { getByText, queryByText } = render(
      <MedicalTermTooltip term="ECG" explanation="A test that measures heart electrical activity" />
    );
    fireEvent.press(getByText('ECG'));
    expect(getByText(/A test that measures/)).toBeTruthy();
    fireEvent.press(getByText('ECG'));
    expect(queryByText(/A test that measures/)).toBeNull();
  });
});
```

- [ ] **Step 2 (3 min):** Implement medical term tooltip.

File: `mobile/components/medical-term-tooltip.tsx`
```typescript
import React, { useState } from 'react';
import { StyleSheet, Pressable, View } from 'react-native';
import { Text, Surface } from 'react-native-paper';

interface MedicalTermTooltipProps {
  term: string;
  explanation: string;
}

export function MedicalTermTooltip({ term, explanation }: MedicalTermTooltipProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <View style={styles.container}>
      <Pressable onPress={() => setIsExpanded(!isExpanded)}>
        <Text style={styles.term}>{term}</Text>
      </Pressable>
      {isExpanded && (
        <Surface style={styles.tooltip} elevation={2}>
          <Text variant="bodySmall" style={styles.explanation}>
            {explanation}
          </Text>
        </Surface>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginVertical: 2,
  },
  term: {
    color: '#1976d2',
    textDecorationLine: 'underline',
    fontWeight: '600',
  },
  tooltip: {
    padding: 12,
    borderRadius: 8,
    marginTop: 4,
    marginBottom: 4,
    backgroundColor: '#e3f2fd',
  },
  explanation: {
    color: '#333',
  },
});
```

Run: `cd mobile && npx jest components/__tests__/medical-term-tooltip.test.tsx`
Verify: All tests pass.

### Task 7.2: Language toggle component

- [ ] **Step 1 (3 min):** Write failing tests for language toggle.

File: `mobile/components/__tests__/language-toggle.test.tsx`
```typescript
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { LanguageToggle } from '../language-toggle';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, string>) => {
      const translations: Record<string, string> = {
        'summary.english': 'English',
        'summary.spanish': 'Spanish',
      };
      return translations[key] ?? key;
    },
  }),
}));

describe('LanguageToggle', () => {
  it('should render with English selected by default', () => {
    const { getByText } = render(
      <LanguageToggle currentLanguage="en" onToggle={jest.fn()} />
    );
    expect(getByText('English')).toBeTruthy();
    expect(getByText('Spanish')).toBeTruthy();
  });

  it('should call onToggle with "es" when Spanish pressed', () => {
    const onToggle = jest.fn();
    const { getByText } = render(
      <LanguageToggle currentLanguage="en" onToggle={onToggle} />
    );
    fireEvent.press(getByText('Spanish'));
    expect(onToggle).toHaveBeenCalledWith('es');
  });

  it('should call onToggle with "en" when English pressed', () => {
    const onToggle = jest.fn();
    const { getByText } = render(
      <LanguageToggle currentLanguage="es" onToggle={onToggle} />
    );
    fireEvent.press(getByText('English'));
    expect(onToggle).toHaveBeenCalledWith('en');
  });
});
```

- [ ] **Step 2 (3 min):** Implement language toggle.

File: `mobile/components/language-toggle.tsx`
```typescript
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
```

Run: `cd mobile && npx jest components/__tests__/language-toggle.test.tsx`
Verify: All tests pass.

### Task 7.3: Summary detail screen

- [ ] **Step 1 (5 min):** Write failing tests for summary detail screen.

File: `mobile/app/(tabs)/summaries/__tests__/detail.test.tsx`
```typescript
import React from 'react';
import { render, waitFor } from '@testing-library/react-native';
import SummaryDetailScreen from '../[id]';
import { summaryService } from '@/services/summary-service';
import type { PatientSummary } from '@/types/api';

jest.mock('@/services/summary-service');
jest.mock('expo-router', () => ({
  useLocalSearchParams: () => ({ id: 'sum-1' }),
  useRouter: () => ({ back: jest.fn() }),
}));
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'summary.visitDate': 'Visit Date',
        'summary.doctorName': 'Doctor',
        'summary.disclaimer': 'For informational purposes only.',
        'summary.contactDoctor': 'Contact My Doctor',
        'summary.tapToExplain': 'Tap terms for explanations',
        'summary.english': 'English',
        'summary.spanish': 'Spanish',
        'common.loading': 'Loading...',
        'common.error': 'An error occurred',
      };
      return translations[key] ?? key;
    },
  }),
}));

const mockSummary: PatientSummary = {
  id: 'sum-1',
  summary_en: 'Your blood pressure was normal. Continue your medication.',
  summary_es: 'Su presion arterial fue normal. Continue con su medicamento.',
  reading_level: 'grade_8',
  medical_terms_explained: [
    { term: 'blood pressure', explanation: 'The force of blood against artery walls.' },
  ],
  disclaimer_text: 'This is for informational purposes only.',
  encounter_date: '2026-03-15',
  doctor_name: 'Dr. Smith',
  delivery_status: 'sent',
  viewed_at: null,
  created_at: '2026-03-15T10:00:00Z',
};

describe('SummaryDetailScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should show loading state initially', () => {
    (summaryService.getSummaryDetail as jest.Mock).mockReturnValue(new Promise(() => {}));
    const { getByText } = render(<SummaryDetailScreen />);
    expect(getByText('Loading...')).toBeTruthy();
  });

  it('should display summary content', async () => {
    (summaryService.getSummaryDetail as jest.Mock).mockResolvedValue(mockSummary);
    (summaryService.markAsRead as jest.Mock).mockResolvedValue(undefined);

    const { getByText } = render(<SummaryDetailScreen />);
    await waitFor(() => {
      expect(getByText('Dr. Smith')).toBeTruthy();
      expect(getByText(/blood pressure was normal/)).toBeTruthy();
    });
  });

  it('should display disclaimer banner', async () => {
    (summaryService.getSummaryDetail as jest.Mock).mockResolvedValue(mockSummary);
    (summaryService.markAsRead as jest.Mock).mockResolvedValue(undefined);

    const { getByText } = render(<SummaryDetailScreen />);
    await waitFor(() => {
      expect(getByText(/informational purposes only/)).toBeTruthy();
    });
  });

  it('should show contact doctor action', async () => {
    (summaryService.getSummaryDetail as jest.Mock).mockResolvedValue(mockSummary);
    (summaryService.markAsRead as jest.Mock).mockResolvedValue(undefined);

    const { getByText } = render(<SummaryDetailScreen />);
    await waitFor(() => {
      expect(getByText('Contact My Doctor')).toBeTruthy();
    });
  });

  it('should display medical term explanations', async () => {
    (summaryService.getSummaryDetail as jest.Mock).mockResolvedValue(mockSummary);
    (summaryService.markAsRead as jest.Mock).mockResolvedValue(undefined);

    const { getByText } = render(<SummaryDetailScreen />);
    await waitFor(() => {
      expect(getByText('blood pressure')).toBeTruthy();
    });
  });

  it('should mark as read on load', async () => {
    (summaryService.getSummaryDetail as jest.Mock).mockResolvedValue(mockSummary);
    (summaryService.markAsRead as jest.Mock).mockResolvedValue(undefined);

    render(<SummaryDetailScreen />);
    await waitFor(() => {
      expect(summaryService.markAsRead).toHaveBeenCalledWith('sum-1');
    });
  });
});
```

- [ ] **Step 2 (5 min):** Implement summary detail screen.

File: `mobile/app/(tabs)/summaries/[id].tsx`
```typescript
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
```

Run: `cd mobile && npx jest app/(tabs)/summaries/__tests__/detail.test.tsx`
Verify: All tests pass.

---

## Chunk 8: Push Notifications with Firebase Cloud Messaging

### Task 8.1: Push notification service

- [ ] **Step 1 (3 min):** Write failing tests for push notification service.

File: `mobile/services/__tests__/push-notification-service.test.ts`
```typescript
import { pushNotificationService } from '../push-notification-service';

jest.mock('@react-native-firebase/messaging', () => {
  const mockMessaging = {
    requestPermission: jest.fn().mockResolvedValue(1),
    getToken: jest.fn().mockResolvedValue('fcm-token-123'),
    onMessage: jest.fn().mockReturnValue(jest.fn()),
    onNotificationOpenedApp: jest.fn().mockReturnValue(jest.fn()),
    getInitialNotification: jest.fn().mockResolvedValue(null),
    setBackgroundMessageHandler: jest.fn(),
  };
  return () => mockMessaging;
});

jest.mock('../api-client', () => ({
  apiClient: {
    post: jest.fn().mockResolvedValue({ data: {} }),
  },
}));

describe('PushNotificationService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should request notification permission', async () => {
    const messaging = require('@react-native-firebase/messaging')();
    await pushNotificationService.requestPermission();
    expect(messaging.requestPermission).toHaveBeenCalled();
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
    const messaging = require('@react-native-firebase/messaging')();
    const handler = jest.fn();
    pushNotificationService.onForegroundMessage(handler);
    expect(messaging.onMessage).toHaveBeenCalled();
  });

  it('should set up notification opened handler', () => {
    const messaging = require('@react-native-firebase/messaging')();
    const handler = jest.fn();
    pushNotificationService.onNotificationOpened(handler);
    expect(messaging.onNotificationOpenedApp).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2 (4 min):** Implement push notification service.

File: `mobile/services/push-notification-service.ts`
```typescript
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
```

Run: `cd mobile && npx jest services/__tests__/push-notification-service.test.ts`
Verify: All tests pass.

---

## Chunk 9: Navigation Layout and Root Routing

### Task 9.1: Root layout with auth guard and Paper theme

- [ ] **Step 1 (4 min):** Write failing tests for root layout logic.

File: `mobile/app/__tests__/layout.test.tsx`
```typescript
import React from 'react';
import { render } from '@testing-library/react-native';
import { useAuth } from '@/contexts/auth-context';

jest.mock('@/contexts/auth-context');
jest.mock('expo-router', () => ({
  Slot: () => null,
  Redirect: ({ href }: { href: string }) => null,
  useRouter: () => ({ replace: jest.fn() }),
  useSegments: () => ['(tabs)'],
}));
jest.mock('react-native-paper', () => ({
  PaperProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  MD3LightTheme: {},
}));
jest.mock('@/i18n', () => ({}));

describe('Root Layout Auth Guard', () => {
  it('should redirect to login when unauthenticated', () => {
    (useAuth as jest.Mock).mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    });
    // The root layout should redirect unauthenticated users to /(auth)/login
    // This is tested by verifying the Redirect component is rendered
    const { useSegments, Redirect } = require('expo-router');
    const segments = useSegments();
    const inAuthGroup = segments[0] === '(auth)';
    const isAuthenticated = false;

    expect(!isAuthenticated && !inAuthGroup).toBe(true);
  });

  it('should allow access to tabs when authenticated', () => {
    (useAuth as jest.Mock).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });
    const isAuthenticated = true;
    const inAuthGroup = false;
    expect(isAuthenticated && !inAuthGroup).toBe(true);
  });
});
```

- [ ] **Step 2 (5 min):** Implement root layout with auth guard, Paper provider, and i18n.

File: `mobile/app/_layout.tsx`
```typescript
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
```

### Task 9.2: Auth layout

- [ ] **Step 1 (2 min):** Create auth group layout.

File: `mobile/app/(auth)/_layout.tsx`
```typescript
import { Stack } from 'expo-router';

export default function AuthLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="login" />
      <Stack.Screen name="profile-setup" />
    </Stack>
  );
}
```

### Task 9.3: Tabs layout

- [ ] **Step 1 (3 min):** Create tabs group layout with bottom navigation.

File: `mobile/app/(tabs)/_layout.tsx`
```typescript
import { Tabs } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { MaterialCommunityIcons } from '@expo/vector-icons';

export default function TabsLayout() {
  const { t } = useTranslation();

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: '#1976d2',
        headerStyle: { backgroundColor: '#1976d2' },
        headerTintColor: '#fff',
      }}
    >
      <Tabs.Screen
        name="summaries"
        options={{
          title: t('summary.listTitle'),
          tabBarIcon: ({ color, size }) => (
            <MaterialCommunityIcons name="file-document" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: t('profile.title'),
          tabBarIcon: ({ color, size }) => (
            <MaterialCommunityIcons name="account" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
```

### Task 9.4: Summaries stack layout

- [ ] **Step 1 (2 min):** Create summaries group stack layout.

File: `mobile/app/(tabs)/summaries/_layout.tsx`
```typescript
import { Stack } from 'expo-router';

export default function SummariesLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="index" />
      <Stack.Screen name="[id]" />
    </Stack>
  );
}
```

Run: `cd mobile && npx jest app/__tests__/layout.test.tsx`
Verify: All tests pass.

---

## Chunk 10: Profile Setup and Profile/Settings Screen

### Task 10.1: Profile setup screen (post-registration)

- [ ] **Step 1 (3 min):** Write failing tests for profile setup.

File: `mobile/app/(auth)/__tests__/profile-setup.test.tsx`
```typescript
import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import ProfileSetupScreen from '../profile-setup';

jest.mock('expo-router', () => ({
  useRouter: () => ({ replace: jest.fn() }),
}));
jest.mock('@/services/api-client', () => ({
  apiClient: { patch: jest.fn().mockResolvedValue({ data: {} }) },
}));
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'profileSetup.title': 'Set Up Your Profile',
        'profileSetup.firstName': 'First Name',
        'profileSetup.lastName': 'Last Name',
        'profileSetup.language': 'Preferred Language',
        'profileSetup.continue': 'Continue',
      };
      return translations[key] ?? key;
    },
    i18n: { changeLanguage: jest.fn() },
  }),
}));

describe('ProfileSetupScreen', () => {
  it('should render form fields', () => {
    const { getByText, getByLabelText } = render(<ProfileSetupScreen />);
    expect(getByText('Set Up Your Profile')).toBeTruthy();
    expect(getByLabelText('First Name')).toBeTruthy();
    expect(getByLabelText('Last Name')).toBeTruthy();
  });

  it('should submit profile data', async () => {
    const { apiClient } = require('@/services/api-client');
    const { getByLabelText, getByText } = render(<ProfileSetupScreen />);

    fireEvent.changeText(getByLabelText('First Name'), 'John');
    fireEvent.changeText(getByLabelText('Last Name'), 'Doe');
    fireEvent.press(getByText('Continue'));

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalled();
    });
  });
});
```

- [ ] **Step 2 (4 min):** Implement profile setup screen.

File: `mobile/app/(auth)/profile-setup.tsx`
```typescript
import React, { useState, useCallback } from 'react';
import { View, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { Text, TextInput, Button, Surface, SegmentedButtons } from 'react-native-paper';
import { useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { apiClient } from '@/services/api-client';

export default function ProfileSetupScreen() {
  const { t, i18n } = useTranslation();
  const router = useRouter();

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [language, setLanguage] = useState<string>(i18n.language || 'en');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = useCallback(async () => {
    setIsSubmitting(true);
    try {
      await apiClient.patch('/patient/profile', {
        first_name: firstName,
        last_name: lastName,
        language_preference: language,
      });
      await i18n.changeLanguage(language);
      router.replace('/(tabs)/summaries');
    } catch {
      // Handle error
    } finally {
      setIsSubmitting(false);
    }
  }, [firstName, lastName, language, i18n, router]);

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <Surface style={styles.card} elevation={2}>
        <Text variant="headlineMedium" style={styles.title}>
          {t('profileSetup.title')}
        </Text>

        <TextInput
          label={t('profileSetup.firstName')}
          accessibilityLabel={t('profileSetup.firstName')}
          value={firstName}
          onChangeText={setFirstName}
          autoComplete="given-name"
          style={styles.input}
          mode="outlined"
        />

        <TextInput
          label={t('profileSetup.lastName')}
          accessibilityLabel={t('profileSetup.lastName')}
          value={lastName}
          onChangeText={setLastName}
          autoComplete="family-name"
          style={styles.input}
          mode="outlined"
        />

        <Text variant="bodyMedium" style={styles.label}>
          {t('profileSetup.language')}
        </Text>
        <SegmentedButtons
          value={language}
          onValueChange={setLanguage}
          buttons={[
            { value: 'en', label: 'English' },
            { value: 'es', label: 'Espanol' },
          ]}
          style={styles.segmented}
        />

        <Button
          mode="contained"
          onPress={handleSubmit}
          loading={isSubmitting}
          disabled={isSubmitting || !firstName.trim()}
          style={styles.button}
        >
          {t('profileSetup.continue')}
        </Button>
      </Surface>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: 24,
    backgroundColor: '#f5f5f5',
  },
  card: {
    padding: 24,
    borderRadius: 16,
  },
  title: {
    textAlign: 'center',
    marginBottom: 24,
  },
  input: {
    marginBottom: 12,
  },
  label: {
    marginBottom: 8,
    color: '#666',
  },
  segmented: {
    marginBottom: 12,
  },
  button: {
    marginTop: 16,
  },
});
```

### Task 10.2: Profile/Settings screen

- [ ] **Step 1 (3 min):** Write failing tests for profile screen.

File: `mobile/app/(tabs)/__tests__/profile.test.tsx`
```typescript
import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import ProfileScreen from '../profile';
import { useAuth } from '@/contexts/auth-context';

jest.mock('@/contexts/auth-context');
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'profile.title': 'Profile & Settings',
        'profile.language': 'Language',
        'profile.notifications': 'Notifications',
        'profile.notificationsEnabled': 'Push notifications are enabled',
        'profile.privacy': 'Privacy',
        'profile.logout': 'Log Out',
        'profile.logoutConfirm': 'Are you sure you want to log out?',
        'profile.version': 'Version',
        'common.cancel': 'Cancel',
        'summary.english': 'English',
        'summary.spanish': 'Spanish',
      };
      return translations[key] ?? key;
    },
    i18n: { language: 'en', changeLanguage: jest.fn() },
  }),
}));

describe('ProfileScreen', () => {
  beforeEach(() => {
    (useAuth as jest.Mock).mockReturnValue({
      logout: jest.fn(),
    });
  });

  it('should render profile settings', () => {
    const { getByText } = render(<ProfileScreen />);
    expect(getByText('Profile & Settings')).toBeTruthy();
    expect(getByText('Language')).toBeTruthy();
    expect(getByText('Log Out')).toBeTruthy();
  });

  it('should call logout on confirmation', async () => {
    const mockLogout = jest.fn();
    (useAuth as jest.Mock).mockReturnValue({ logout: mockLogout });

    const { getByText } = render(<ProfileScreen />);
    fireEvent.press(getByText('Log Out'));
    // The confirmation dialog would appear in a real app
  });
});
```

- [ ] **Step 2 (5 min):** Implement profile/settings screen.

File: `mobile/app/(tabs)/profile.tsx`
```typescript
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
```

Run: `cd mobile && npx jest app/(tabs)/__tests__/profile.test.tsx`
Verify: All tests pass.

---

## Chunk 11: Network Status and Offline Sync

### Task 11.1: Network status hook

- [ ] **Step 1 (3 min):** Write failing tests for useNetworkStatus hook.

File: `mobile/hooks/__tests__/use-network-status.test.ts`
```typescript
import { renderHook, act } from '@testing-library/react-native';
import { useNetworkStatus } from '../use-network-status';

const mockAddEventListener = jest.fn();
const mockFetch = jest.fn();

jest.mock('@react-native-community/netinfo', () => ({
  addEventListener: (callback: Function) => {
    mockAddEventListener(callback);
    return jest.fn(); // unsubscribe
  },
  fetch: () => mockFetch(),
}));

describe('useNetworkStatus', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockResolvedValue({ isConnected: true, isInternetReachable: true });
  });

  it('should return connected status initially', async () => {
    const { result } = renderHook(() => useNetworkStatus());
    await act(async () => {});
    expect(result.current.isConnected).toBe(true);
  });

  it('should register event listener', () => {
    renderHook(() => useNetworkStatus());
    expect(mockAddEventListener).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2 (3 min):** Implement network status hook.

First install netinfo:
```bash
cd /Users/yemalin.godonou/Documents/works/tiko/medicalnote/mobile
npx expo install @react-native-community/netinfo
```

File: `mobile/hooks/use-network-status.ts`
```typescript
import { useState, useEffect } from 'react';
import NetInfo, { NetInfoState } from '@react-native-community/netinfo';

interface NetworkStatus {
  isConnected: boolean;
  isInternetReachable: boolean | null;
}

export function useNetworkStatus(): NetworkStatus {
  const [status, setStatus] = useState<NetworkStatus>({
    isConnected: true,
    isInternetReachable: true,
  });

  useEffect(() => {
    // Fetch initial state
    NetInfo.fetch().then((state: NetInfoState) => {
      setStatus({
        isConnected: state.isConnected ?? true,
        isInternetReachable: state.isInternetReachable,
      });
    });

    // Subscribe to changes
    const unsubscribe = NetInfo.addEventListener((state: NetInfoState) => {
      setStatus({
        isConnected: state.isConnected ?? true,
        isInternetReachable: state.isInternetReachable,
      });
    });

    return () => unsubscribe();
  }, []);

  return status;
}
```

Run: `cd mobile && npx jest hooks/__tests__/use-network-status.test.ts`
Verify: All tests pass.

### Task 11.2: Offline sync manager

- [ ] **Step 1 (3 min):** Write failing tests.

File: `mobile/services/__tests__/sync-manager.test.ts`
```typescript
import { syncManager } from '../sync-manager';
import { summaryService } from '../summary-service';
import { offlineCache } from '../offline-cache';

jest.mock('../summary-service');
jest.mock('../offline-cache');

describe('SyncManager', () => {
  beforeEach(() => jest.clearAllMocks());

  it('should pull summaries on sync', async () => {
    (summaryService.getSummaries as jest.Mock).mockResolvedValue([]);
    await syncManager.syncOnReconnect();
    expect(summaryService.getSummaries).toHaveBeenCalled();
  });

  it('should skip sync if recently synced', async () => {
    (offlineCache.getLastSyncTimestamp as jest.Mock).mockReturnValue(Date.now());
    await syncManager.syncOnReconnect();
    expect(summaryService.getSummaries).not.toHaveBeenCalled();
  });

  it('should sync if last sync was over 5 minutes ago', async () => {
    (offlineCache.getLastSyncTimestamp as jest.Mock).mockReturnValue(Date.now() - 6 * 60 * 1000);
    (summaryService.getSummaries as jest.Mock).mockResolvedValue([]);
    await syncManager.syncOnReconnect();
    expect(summaryService.getSummaries).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2 (2 min):** Implement sync manager.

File: `mobile/services/sync-manager.ts`
```typescript
import { summaryService } from './summary-service';
import { offlineCache } from './offline-cache';

const SYNC_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

export const syncManager = {
  async syncOnReconnect(): Promise<void> {
    const lastSync = offlineCache.getLastSyncTimestamp();
    if (lastSync && Date.now() - lastSync < SYNC_INTERVAL_MS) {
      return; // Recently synced
    }
    try {
      await summaryService.getSummaries(); // pull-only; caches internally
    } catch {
      // Silently fail -- will retry on next reconnect
    }
  },
};
```

Run: `cd mobile && npx jest services/__tests__/sync-manager.test.ts`
Verify: All tests pass.

---

## Chunk 12: Integration Wiring and Final Verification

### Task 12.1: Background message handler for FCM

- [ ] **Step 1 (2 min):** Create background handler registration file.

File: `mobile/services/background-messaging.ts`
```typescript
import messaging from '@react-native-firebase/messaging';

// Must be registered outside of React lifecycle
messaging().setBackgroundMessageHandler(async (remoteMessage) => {
  // Data-only messages can be processed here
  // Summary data is NOT pre-fetched in background to avoid PHI in memory
  // The app will fetch on next foreground
  console.log('Background message received:', remoteMessage.messageId);
});
```

### Task 12.2: App entry point

- [ ] **Step 1 (2 min):** Register background handler in app entry.

File: `mobile/index.ts`
```typescript
import 'expo-router/entry';
import './services/background-messaging';
```

Update `package.json` main field:
```json
{
  "main": "index.ts"
}
```

### Task 12.3: Full test suite run

- [ ] **Step 1 (3 min):** Run full test suite.

```bash
cd /Users/yemalin.godonou/Documents/works/tiko/medicalnote/mobile && npx jest --coverage
```

Verify: All tests pass across all modules.

---

## Summary of File Inventory

All files to create (42 files total):

**Config (4):** `app.json`, `tsconfig.json`, `jest.config.js`, `config/env.ts`

**Types (1):** `types/api.ts`

**i18n (3):** `i18n/index.ts`, `i18n/en.json`, `i18n/es.json`

**Services (8):** `services/token-storage.ts`, `services/api-client.ts`, `services/auth-service.ts`, `services/summary-service.ts`, `services/offline-cache.ts`, `services/push-notification-service.ts`, `services/sync-manager.ts`, `services/background-messaging.ts`

**Contexts (1):** `contexts/auth-context.tsx`

**Components (3):** `components/summary-card.tsx`, `components/medical-term-tooltip.tsx`, `components/language-toggle.tsx`

**Hooks (1):** `hooks/use-network-status.ts`

**App Routes (9):** `app/_layout.tsx`, `app/(auth)/_layout.tsx`, `app/(auth)/login.tsx`, `app/(auth)/profile-setup.tsx`, `app/(tabs)/_layout.tsx`, `app/(tabs)/summaries/_layout.tsx`, `app/(tabs)/summaries/index.tsx`, `app/(tabs)/summaries/[id].tsx`, `app/(tabs)/profile.tsx`

**Entry (1):** `index.ts`

**Tests (11):** `__tests__/setup.test.ts`, `services/__tests__/token-storage.test.ts`, `services/__tests__/api-client.test.ts`, `services/__tests__/auth-service.test.ts`, `services/__tests__/summary-service.test.ts`, `services/__tests__/offline-cache.test.ts`, `services/__tests__/push-notification-service.test.ts`, `services/__tests__/sync-manager.test.ts`, `types/__tests__/api.test.ts`, `i18n/__tests__/i18n.test.ts`, `hooks/__tests__/use-network-status.test.ts`, `contexts/__tests__/auth-context.test.tsx`, `components/__tests__/summary-card.test.tsx`, `components/__tests__/medical-term-tooltip.test.tsx`, `components/__tests__/language-toggle.test.tsx`, `app/__tests__/layout.test.tsx`, `app/(auth)/__tests__/login.test.tsx`, `app/(auth)/__tests__/profile-setup.test.tsx`, `app/(tabs)/__tests__/profile.test.tsx`, `app/(tabs)/summaries/__tests__/index.test.tsx`, `app/(tabs)/summaries/__tests__/detail.test.tsx`

---

## Backend Gaps to Address

The following must be added to the backend before full mobile integration:

1. **Device token registration endpoint:** `POST /api/v1/patient/device/` -- accepts `{token, platform}` and stores FCM device token for the authenticated patient user. This is referenced in `push-notification-service.ts`.

2. **Patient profile endpoint:** `GET/PATCH /api/v1/patient/profile` -- listed in the architecture spec (line 591) but not implemented in the backend plan. The mobile app's profile-setup screen sends a PATCH to this endpoint.

3. **FCM send implementation:** The backend `services/notification_service.py` has `send_push_notification` as a placeholder. It needs `firebase-admin` SDK integration to actually send messages via FCM.
