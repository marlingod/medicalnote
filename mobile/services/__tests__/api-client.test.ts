jest.mock('../token-storage');

// We need to mock axios BEFORE api-client loads, and the mock factory
// is hoisted but can't reference outer-scope variables. Use a module-level approach.
jest.mock('axios', () => {
  const interceptors = {
    request: { use: jest.fn() },
    response: { use: jest.fn() },
  };
  const instance = {
    interceptors,
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
    defaults: { headers: { common: {} } },
  };
  const create = jest.fn(() => instance);
  return {
    __esModule: true,
    default: {
      create,
      post: jest.fn(),
      isAxiosError: jest.fn(),
    },
    create,
    post: jest.fn(),
    isAxiosError: jest.fn(),
  };
});

// Now import after mocks are set up
import axios from 'axios';
// Force the api-client module to load (it calls axios.create at module scope)
import '../api-client';

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
    expect(instance).toBeDefined();
    expect(instance.interceptors.request.use).toHaveBeenCalled();
  });

  it('should register response interceptor for token refresh', () => {
    const instance = (axios.create as jest.Mock).mock.results[0]?.value;
    expect(instance).toBeDefined();
    expect(instance.interceptors.response.use).toHaveBeenCalled();
  });
});
