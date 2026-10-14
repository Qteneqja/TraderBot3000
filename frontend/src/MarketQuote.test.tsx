import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, expect, it } from 'vitest';
import MarketQuote from './MarketQuote';

afterEach(cleanup);
const quote = { bid: '1.12345', ask: '1.12347', time: '2026-10-14T15:30:00Z', stale: false };
it('keeps fixture data separate and reports missing provider quotes', () => {
  const view = render(<MarketQuote quote={quote} symbol="EUR_USD" demo error={false}/>);
  expect(screen.queryByLabelText('Provider quote')).not.toBeInTheDocument();
  view.rerender(<MarketQuote symbol="EUR_USD" demo={false} error={false}/>);
  expect(screen.getByText(/Waiting for a current provider quote/)).toBeInTheDocument();
});
it('shows timestamped bid and ask and stops claiming freshness after an API failure', () => {
  const view = render(<MarketQuote quote={quote} symbol="EUR_USD" demo={false} error={false}/>);
  expect(screen.getByLabelText('Provider quote')).toHaveTextContent('Bid 1.12345 / Ask 1.12347');
  expect(screen.getByLabelText('Provider quote')).toHaveTextContent('2026-10-14 15:30:00 UTC');
  view.rerender(<MarketQuote quote={quote} symbol="EUR_USD" demo={false} error/>);
  expect(screen.getByLabelText('Provider quote')).toHaveTextContent('stale or unavailable');
});
