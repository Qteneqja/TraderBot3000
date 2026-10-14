import { useApi } from './api';

type Status = { account_reference: string; current: boolean; currency: string; reconciled: boolean;
  suspended: boolean; synchronized_at: string; approval_scope: string; order_states: Record<string, number> };

export default function PracticeStatus() {
  const { data, error } = useApi<Status[]>('/api/practice-status');
  return <section className="panel" aria-label="OANDA practice readiness">
    <div className="panel-heading"><h2>OANDA practice readiness</h2></div>
    {error && <p role="alert">{error} Practice status may be stale.</p>}
    {!data?.length ? <p>No durable practice reconciliation recorded. Read-only checks and explicit approval precede submission.</p> :
      data.map(row => <div className="model-record" key={row.account_reference}>
        <h3>{row.currency} practice account {row.current ? '· Current configuration' : '· Historical configuration'}</h3>
        <p>Reconciliation: {row.reconciled ? 'Consistent' : 'Unresolved'} · New entries: {row.suspended ? 'Suspended' : 'Subject to risk checks'}</p>
        <p>Approval: {row.approval_scope.replaceAll('_', ' ')} · Updated {new Date(row.synchronized_at).toLocaleString()}</p>
        <p>{Object.entries(row.order_states).map(([state, count]) => `${state}: ${count}`).join(' · ') || 'No practice orders recorded.'}</p>
      </div>)}
    <p>Read-only connectivity is separate from confirmed fills, protection and lifecycle approval. Real-money execution remains unsupported.</p>
  </section>;
}
