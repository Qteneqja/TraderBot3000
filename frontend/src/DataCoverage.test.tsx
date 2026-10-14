import { render, screen } from '@testing-library/react';
import { vi, test, expect } from 'vitest';
import { DataCoverage } from './DataCoverage';
import { useApi } from './api';

vi.mock('./api', () => ({ useApi: vi.fn() }));

test('distinguishes stored provider history from ineligible fixtures', () => {
  vi.mocked(useApi).mockReturnValue({ data: [
    { symbol: 'EUR_USD', source: 'oanda', timeframe: 300, candles: 74589,
      first: '2025-10-14T00:00:00+00:00', last: '2026-10-13T23:55:00+00:00', classification: 'PROVIDER_HISTORY' },
    { symbol: 'EUR_USD', source: 'fixture', timeframe: 300, candles: 2000,
      first: '2025-01-06T00:00:00+00:00', last: '2025-01-12T22:35:00+00:00', classification: 'SYNTHETIC_FIXTURE' },
  ], error: '', refresh: vi.fn() });
  render(<DataCoverage/>);
  expect(screen.getByText('74,589')).toBeInTheDocument();
  expect(screen.getByText('Provider history — unassessed')).toBeInTheDocument();
  expect(screen.getByText('Synthetic fixture — ineligible')).toBeInTheDocument();
  expect(screen.getByText(/Date ranges may contain gaps/)).toBeInTheDocument();
});

test('labels unavailable coverage without inventing counts', () => {
  vi.mocked(useApi).mockReturnValue({ data: null, error: 'API unavailable', refresh: vi.fn() });
  render(<DataCoverage/>);
  expect(screen.getByRole('alert')).toHaveTextContent('Coverage records may be stale');
  expect(screen.getByText('No stored history reported.')).toBeInTheDocument();
});
