describe('Project Setup', () => {
  it('should have correct environment config shape', () => {
    const { ENV } = require('../config/env');
    expect(ENV).toHaveProperty('API_BASE_URL');
    expect(ENV).toHaveProperty('FCM_VAPID_KEY');
    expect(typeof ENV.API_BASE_URL).toBe('string');
  });
});
