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
