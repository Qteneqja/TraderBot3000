import { useApi } from './api';

type Evaluation = { id: string; parent: string; model: string | null; state: string;
  start: string; end: string; result: { status?: string; error_type?: string } };

export default function FinalEvaluations() {
  const { data, error } = useApi<Evaluation[]>('/api/final-evaluations');
  return <section className="panel" aria-label="Prospective final evaluations">
    <div className="panel-heading"><h2>Prospective final evaluations</h2></div>
    <p>Only a frozen candidate passing validation can reserve a future test. Evaluation never activates a model.</p>
    {error && <p role="alert">{error} Final-evaluation records may be stale.</p>}
    {!data?.length ? <p>No future test reserved.</p> : data.map(row => <div className="model-record" key={row.id}>
      <h3>{row.state}</h3><p>Frozen candidate: {row.parent}</p>
      <p>{new Date(row.start).toISOString()} to {new Date(row.end).toISOString()} (end exclusive)</p>
      {row.result.status && <p>Research assessment: {row.result.status}</p>}
      {row.result.error_type && <p>Evaluation failed: {row.result.error_type}. Operator review required; no automatic retry.</p>}
      <p>Model activation requires separate approval.</p>
    </div>)}
  </section>;
}
