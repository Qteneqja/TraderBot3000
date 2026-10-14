import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App';

vi.mock('./Chart', () => ({ default: () => <div>Chart unavailable</div> }));
vi.mock('./api', () => ({ useApi: (path: string) => ({
  data: path === '/api/overview' ? { mode: 'PAPER', demo: true, open_positions: 0, pending_orders: 0,
    planned_risk: 0, signals: 0, account: { equity: 10000, day_start: 10000, suspended: false } }
    : path.startsWith('/api/candles') ? { source: 'fixture', candles: [] } : null,
  error: '', refresh: vi.fn(),
}) }));

afterEach(cleanup);

describe('honest empty states', () => {
  it('labels fixtures and never invents model confidence', () => {
    render(<App/>);
    expect(screen.getByText('Offline research workspace')).toBeInTheDocument();
    expect(screen.getByText('UNVALIDATED')).toBeInTheDocument();
    expect(screen.getByText('No signals yet')).toBeInTheDocument();
    expect(screen.getByText('NO REAL MONEY')).toBeInTheDocument();
  });
  it('navigates to model and journal empty states without inventing records', () => {
    render(<App/>);
    fireEvent.click(screen.getByRole('button', { name: 'Model lab' }));
    expect(screen.getByText('Evidence starts with research')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Trade journal' }));
    expect(screen.getByText('A clean trading journal')).toBeInTheDocument();
  });
  it('exposes read-only risk controls and no live activation action', () => {
    render(<App/>);
    fireEvent.click(screen.getByRole('button', { name: 'Risk controls' }));
    expect(screen.getByText('Risk has the final word.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /activate live/i })).not.toBeInTheDocument();
  });
});
