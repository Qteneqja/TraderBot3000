import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import Narratives from './Narratives';
import { useApi } from './api';

vi.mock('./api', () => ({ useApi: vi.fn() }));
afterEach(cleanup);

test('generated commentary has no execution or training authority', () => {
  vi.mocked(useApi).mockReturnValue({ data: { status: 'SUCCEEDED', enabled: true, provider: 'deepseek',
    model: 'deepseek-flash', max_calls_per_day: 4, records: [{ id: 'test', source_kind: 'RESEARCH',
      state: 'SUCCEEDED', facts: { symbol: 'EUR_USD', classification: 'PROVIDER_RESEARCH' },
      explanation: { summary: 'Activity is insufficient.', risks: [], limitations: ['Research only.'] }, error_type: null }] },
    error: '', refresh: vi.fn() });
  render(<Narratives/>);
  expect(screen.getByText('Activity is insufficient.')).toBeInTheDocument();
  expect(screen.getByText('NARRATIVE ONLY')).toBeInTheDocument();
  expect(screen.getByText(/API calls do not fine-tune DeepSeek/)).toBeInTheDocument();
});

test('provider outage keeps commentary unavailable and decisions unchanged', () => {
  vi.mocked(useApi).mockReturnValue({ data: { status: 'UNKNOWN', enabled: true, provider: 'deepseek',
    model: 'deepseek-flash', max_calls_per_day: 4, records: [{ id: 'test', source_kind: 'RESEARCH',
      state: 'UNKNOWN', facts: {}, explanation: null, error_type: 'TIMEOUT' }] },
    error: 'API unavailable', refresh: vi.fn() });
  render(<Narratives/>);
  expect(screen.getByRole('alert')).toHaveTextContent('Commentary records may be stale');
  expect(screen.getByText(/Explanation unavailable \(TIMEOUT\)/)).toHaveTextContent('Quantitative decisions remain unchanged');
});
