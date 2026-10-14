type Quote = { bid: number | string; ask: number | string; time: string; stale: boolean };

export default function MarketQuote({ quote, symbol, demo, error }: {
  quote?: Quote; symbol: string; demo: boolean; error: boolean;
}) {
  if (demo) return null;
  if (!quote) return <p className="muted">Waiting for a current provider quote.</p>;
  const precision = symbol.includes('_') ? 5 : 2;
  return <p className="muted" aria-label="Provider quote">
    {quote.stale || error ? 'Last observed quote (stale or unavailable)' : 'Latest provider quote'}
    {' · '}Bid {Number(quote.bid).toFixed(precision)} / Ask {Number(quote.ask).toFixed(precision)}
    {' · '}{new Date(quote.time).toISOString().replace('T', ' ').slice(0, 19)} UTC
    {' · '}Dashboard refreshes every 15 seconds
  </p>;
}
