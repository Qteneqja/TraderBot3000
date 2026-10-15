import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import FinalEvaluations from './FinalEvaluations';
import { useApi } from './api';

vi.mock('./api', () => ({ useApi: vi.fn() }));
afterEach(cleanup);

test('completed evaluation preserves rejected status and separate activation', () => {
  vi.mocked(useApi).mockReturnValue({ data: [{ id: 'test', parent: 'test-frozen', model: 'test-final',
    state: 'COMPLETED', start: '2026-11-01T00:00:00Z', end: '2026-12-16T00:00:00Z',
    result: { status: 'REJECTED' } }], error: '', refresh: vi.fn() });
  render(<FinalEvaluations/>);
  expect(screen.getByText('Research assessment: REJECTED')).toBeInTheDocument();
  expect(screen.getByText('Model activation requires separate approval.')).toBeInTheDocument();
});

test('unavailable final evidence is visibly stale', () => {
  vi.mocked(useApi).mockReturnValue({ data: null, error: 'API unavailable', refresh: vi.fn() });
  render(<FinalEvaluations/>);
  expect(screen.getByRole('alert')).toHaveTextContent('Final-evaluation records may be stale');
  expect(screen.getByText('No future test reserved.')).toBeInTheDocument();
});
