import { useApi } from './api';

type Review = { id: string; model_id: string; status: string; created_at: string;
  report: { reasons: string[]; checks: Record<string, boolean>; execution_allowed: false;
    policy: { version: string }; remaining_gates: string[] } };

export default function ModelReviews() {
  const { data, error } = useApi<Review[]>('/api/model-reviews');
  return <section className="panel events" aria-label="Model acceptance reviews">
    <div className="panel-heading"><div><h2>Acceptance reviews</h2><p className="muted" style={{ marginTop: 8, fontSize: 10 }}>
      Predeclared research criteria. Passing these checks does not enable trading.</p></div></div>
    {error && <p className="error-banner" role="alert">{error}</p>}
    {!data?.length ? <div className="empty"><h3>No acceptance reviews yet</h3><p>Assess a registered model to inspect data provenance, calibration, net results and cost sensitivity.</p></div> : data.map(review =>
      <div className="model-record" key={review.id}>
        <h3>{review.model_id} <span className="badge amber">{review.status.replaceAll('_', ' ')}</span></h3>
        <p>{review.report.policy.version} · {new Date(review.created_at).toLocaleString()} · Review alone grants no trading permission</p>
        <div className="metric-row"><span>Checks passed <strong>{Object.values(review.report.checks).filter(Boolean).length} / {Object.keys(review.report.checks).length}</strong></span></div>
        {review.report.reasons.length > 0 && <p>Unmet criteria: {review.report.reasons.map(reason => reason.toLowerCase().replaceAll('_', ' ')).join(' · ')}</p>}
        <p>Still required: {review.report.remaining_gates.join(' · ')}</p>
      </div>)}
  </section>;
}
