import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, vi, test, expect } from 'vitest';
import LearningStatus from './LearningStatus';
import { useApi } from './api';

vi.mock('./api', () => ({ useApi: vi.fn() }));
afterEach(cleanup);

test('experimental research never implies activation or final qualification', () => {
  vi.mocked(useApi).mockReturnValue({ data: { schedules: [], outcomes: [], runs: [{ id: 'mock',
    state: 'COMPLETED', final_test: 'PROSPECTIVE_UNTOUCHED_PERIOD_REQUIRED', candidates: [
      { family: 'logistic', status: 'EXPERIMENTAL', validation: { multiclass_brier: .55 } }] }] },
    error: '', refresh: vi.fn() });
  render(<LearningStatus/>);
  expect(screen.getByText('logistic: EXPERIMENTAL', { exact: false })).toHaveTextContent('0.5500');
  expect(screen.getByText('PROSPECTIVE UNTOUCHED PERIOD REQUIRED')).toBeInTheDocument();
  expect(screen.getByText(/Model activation requires separate operator approval/)).toBeInTheDocument();
});

test('unavailable research status is visibly stale', () => {
  vi.mocked(useApi).mockReturnValue({ data: null, error: 'API unavailable', refresh: vi.fn() });
  render(<LearningStatus/>);
  expect(screen.getByRole('alert')).toHaveTextContent('Learning records may be stale');
  expect(screen.getByText('No research schedule enabled.')).toBeInTheDocument();
});
