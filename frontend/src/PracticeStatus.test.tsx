import { render, screen } from '@testing-library/react';
import { vi, test, expect } from 'vitest';
import PracticeStatus from './PracticeStatus';
import { useApi } from './api';

vi.mock('./api', () => ({ useApi: vi.fn() }));

test('a consistent account is still suspended until approval', () => {
  vi.mocked(useApi).mockReturnValue({ data: [{ account_reference: 'test', current: true, currency: 'CAD',
    reconciled: true, suspended: true, synchronized_at: '2026-10-14T00:00:00Z',
    approval_scope: 'NOT_APPROVED', order_states: {} }], error: '', refresh: vi.fn() });
  render(<PracticeStatus/>);
  expect(screen.getByText(/Reconciliation: Consistent/)).toHaveTextContent('New entries: Suspended');
  expect(screen.getByText(/Approval: NOT APPROVED/)).toBeInTheDocument();
  expect(screen.getByText('No practice orders recorded.')).toBeInTheDocument();
});

test('missing practice evidence is not represented as ready', () => {
  vi.mocked(useApi).mockReturnValue({ data: null, error: 'API unavailable', refresh: vi.fn() });
  render(<PracticeStatus/>);
  expect(screen.getByRole('alert')).toHaveTextContent('Practice status may be stale');
  expect(screen.getByText(/No durable practice reconciliation recorded/)).toBeInTheDocument();
});
