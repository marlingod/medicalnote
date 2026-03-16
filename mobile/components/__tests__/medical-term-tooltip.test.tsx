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
