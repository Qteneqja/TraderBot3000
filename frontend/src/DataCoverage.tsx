import { useApi } from './api';

export type Coverage = { symbol: string; source: string; timeframe: number; candles: number;
  first: string; last: string; classification: string; qualification: string };

export function DataCoverage() {
  const { data, error } = useApi<Coverage[]>('/api/data-coverage');
  return <section className="panel">
    <div className="panel-heading"><h2>Stored training history</h2></div>
    <p>The chart displays 300 recent candles. Training uses stored history independently.
      Date ranges may contain gaps; coverage and model qualification require separate review.</p>
    {error && <p role="alert">{error} Coverage records may be stale.</p>}
    {!data?.length ? <p>No stored history reported.</p> : <div className="table-scroll"><table>
      <thead><tr>{['Market', 'Source', 'Minutes', 'Candles', 'First UTC', 'Last UTC', 'Classification'].map(c => <th key={c}>{c}</th>)}</tr></thead>
      <tbody>{data.map(row => <tr key={`${row.symbol}:${row.source}:${row.timeframe}`}>
        <td>{row.symbol}</td><td>{row.source}</td><td>{row.timeframe / 60}</td>
        <td>{row.candles.toLocaleString()}</td><td>{row.first.slice(0, 16).replace('T', ' ')}</td>
        <td>{row.last.slice(0, 16).replace('T', ' ')}</td><td>{row.classification === 'SYNTHETIC_FIXTURE' ? 'Synthetic fixture — ineligible' : 'Provider history — unassessed'}</td>
      </tr>)}</tbody></table></div>}
  </section>;
}
