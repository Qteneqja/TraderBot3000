import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import ShadowPanel from './ShadowPanel';

vi.mock('./api', () => ({ useApi: () => ({ data: [{ id: 1, model_id: 'test', symbol: 'EUR_USD',
  time: '2026-01-01T00:00:00Z', mode: 'PAPER_TRIAL', candidate: { source: 'oanda', direction: 'LONG' },
  prediction: { probability_target: .8, probability_stop: .15, probability_timeout: .05, execution_allowed: false },
}], error: '' }) }));

it('distinguishes paper trial predictions from non-executing shadow observations', () => {
  render(<ShadowPanel/>);
  expect(screen.getByText(/Paper trial.*Risk approval required/)).toBeInTheDocument();
  fireEvent.change(screen.getByRole('combobox'), { target: { value: 'SHADOW' } });
  expect(screen.getByText('No model observations')).toBeInTheDocument();
  expect(screen.queryByText('80.0%')).not.toBeInTheDocument();
});
