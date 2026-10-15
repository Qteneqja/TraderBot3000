import { useApi } from './api';

type Diagnostic = {
  as_of: string; active_paper_deployments: number; first_entry_blocker: string;
  workers: Record<string, { state: string }>;
  signals: { stored_counts: Record<string, number>; sample_count: number; rejection_reasons: Record<string, number>;
    provider_sample_count?: number; provider_rejection_reasons?: Record<string, number> };
  telegram: { status: string; delivery_evidence: string; counts: Record<string, number>;
    last_preflight_failure?: { time: string; error_code: string } | null;
    latest_attempt: { state: string; error_code: string | null; delivered_at: string | null } | null };
};

export default function ActivationStatus() {
  const { data, error } = useApi<Diagnostic>('/api/activation-diagnostic');
  return <section className="panel"><div className="panel-heading"><h2>Trading activation diagnostic</h2>
    <span className="badge amber">{data?.active_paper_deployments ? 'RUNTIME CHECKS REQUIRED' : 'AWAITING QUALIFIED MODEL'}</span></div>
    {error && <p role="alert">Diagnostic unavailable. Displayed evidence may be stale.</p>}
    {!data ? <p>Waiting for recorded activation evidence.</p> : <>
      <p>Entry status: {data.first_entry_blocker}. No order is forced to demonstrate activity.</p>
      <p>Stored unique decisions: {Object.entries(data.signals.stored_counts).map(([state, count]) => `${state}: ${count}`).join(' · ') || 'none'}.</p>
      <div className="table-scroll"><table><thead><tr><th>Rejection reason</th><th>Count</th></tr></thead>
        <tbody>{Object.entries(data.signals.provider_rejection_reasons ?? data.signals.rejection_reasons).map(([reason, count]) => <tr key={reason}><td>{reason}</td><td>{count}</td></tr>)}</tbody></table></div>
      <p>Provider rejection sample: {data.signals.provider_sample_count ?? 'unavailable'} within the latest {data.signals.sample_count} stored decisions (maximum 500). Total stored counts include legacy fixtures. One decision can have multiple reasons.</p>
      <p>Workers: {Object.entries(data.workers).map(([name, worker]) => `${name}: ${worker.state}`).join(' · ')}.</p>
      <p>Telegram automatic delivery: {data.telegram.status}. Delivery evidence: {data.telegram.delivery_evidence}.</p>
      {data.telegram.last_preflight_failure && <p>Recorded connectivity failure: {data.telegram.last_preflight_failure.error_code}
        {' '}at {data.telegram.last_preflight_failure.time}.</p>}
      {data.telegram.latest_attempt && <p>Latest message attempt: {data.telegram.latest_attempt.state}
        {data.telegram.latest_attempt.error_code ? ` (${data.telegram.latest_attempt.error_code})` : ''}.
        {data.telegram.latest_attempt.delivered_at ? ` API confirmed at ${data.telegram.latest_attempt.delivered_at}.` : ''}</p>}
      <small>As of {data.as_of}. A connectivity test does not verify real trade notifications. PAPER and broker practice remain separate environments.</small>
    </>}
  </section>;
}
