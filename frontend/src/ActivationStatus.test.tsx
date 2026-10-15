import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import ActivationStatus from './ActivationStatus';
import { useApi } from './api';

vi.mock('./api', () => ({ useApi: vi.fn() }));
afterEach(cleanup);

test('zero-trade reasons and disabled automatic delivery remain explicit after a test receipt', () => {
  vi.mocked(useApi).mockReturnValue({ data: { as_of: '2026-10-15T17:00:00Z', active_paper_deployments: 0,
    first_entry_blocker: 'NO_ACTIVE_QUALIFIED_PAPER_DEPLOYMENT', workers: { trading: { state: 'FRESH' } },
    signals: { stored_counts: { REJECTED: 100 }, sample_count: 100,
      rejection_reasons: { NO_VALIDATED_CALIBRATED_MODEL: 100 } },
    telegram: { status: 'DISABLED', delivery_evidence: 'API_CONFIRMED', counts: { DELIVERED: 1 },
      latest_attempt: { state: 'DELIVERED', error_code: null, delivered_at: '2026-10-15T16:59:00Z' } } },
    error: '', refresh: vi.fn() });
  render(<ActivationStatus/>);
  expect(screen.getByText('AWAITING QUALIFIED MODEL')).toBeInTheDocument();
  expect(screen.getByText('NO_VALIDATED_CALIBRATED_MODEL')).toBeInTheDocument();
  expect(screen.getByText(/Telegram automatic delivery: DISABLED/)).toHaveTextContent('API_CONFIRMED');
  expect(screen.getByText(/connectivity test does not verify real trade notifications/)).toBeInTheDocument();
});

test('missing API evidence never reports readiness', () => {
  vi.mocked(useApi).mockReturnValue({ data: null, error: 'Unavailable', refresh: vi.fn() });
  render(<ActivationStatus/>);
  expect(screen.getByRole('alert')).toHaveTextContent('may be stale');
  expect(screen.getByText(/Waiting for recorded/)).toBeInTheDocument();
});
