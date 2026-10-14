import { useApi } from './api';

type Deployment = { id: string; model_id: string; review_id: string; current: boolean;
  operator: string; reason: string; created_at: string; rollback_of: string | null };
type Run = { id: string; status: string; classification: string; samples: number;
  healthy_observed_seconds: string; model_observed_seconds: string; unhealthy_samples: number;
  worker_instances: number; continuity_breaks: number; recorder_stale: boolean;
  latest: { issues: string[]; deployments: string[] } | null };

export default function PaperTrials() {
  const deployments = useApi<Deployment[]>('/api/paper-deployments');
  const runs = useApi<Run[]>('/api/paper-runs');
  return <section className="panel events" aria-label="Paper trials and recording">
    <div className="panel-heading"><div><h2>Paper trials</h2><p className="muted">
      Audited deployments and measured operating time. Broker execution remains disabled.</p></div></div>
    {(deployments.error || runs.error) && <p className="error-banner" role="alert">{deployments.error || runs.error}</p>}
    {!deployments.data?.length ? <div className="empty"><h3>No paper model deployed</h3>
      <p>Research screening and explicit operator approval are required before a model can enter a paper trial.</p></div>
      : deployments.data.map(item => <div className="model-record" key={item.id}>
        <h3>{item.model_id} <span className="badge amber">{item.current ? 'CURRENT PAPER TRIAL' : 'HISTORICAL'}</span></h3>
        <p>{item.operator} · {new Date(item.created_at).toLocaleString()} · {item.reason}</p>
        <p>Deployment: {item.id}{item.rollback_of ? ` · Restored from ${item.rollback_of}` : ''}</p>
      </div>)}
    <div className="panel-heading"><h2>Trading recorder</h2></div>
    {!runs.data?.length ? <div className="empty"><h3>No recording started</h3>
      <p>Start a recording from the local operator CLI. No elapsed trial time is assumed.</p></div>
      : runs.data.map(run => <div className="model-record" key={run.id}>
        <h3>{run.classification.replaceAll('_', ' ')} <span className="badge amber">{run.status}</span></h3>
        <p>{run.id} · {run.status === 'RUNNING' ? (run.recorder_stale ? 'Recorder stale or waiting' : 'Recorder reporting') : 'Recording stopped'}</p>
        <div className="metric-row">
          <span>Healthy observed time<strong>{(Number(run.healthy_observed_seconds) / 3600).toFixed(2)} h</strong></span>
          <span>Time with paper models<strong>{(Number(run.model_observed_seconds) / 3600).toFixed(2)} h</strong></span>
          <span>Samples with issues<strong>{run.unhealthy_samples} / {run.samples}</strong></span>
        </div>
        <p>{run.worker_instances} worker instances · {run.continuity_breaks} continuity breaks</p>
        {run.latest?.issues.length ? <p>Latest issues: {run.latest.issues.map(issue => issue.toLowerCase().replaceAll('_', ' ')).join(' · ')}</p> : null}
        <p>Observations only. No automatic model acceptance or broker approval.</p>
      </div>)}
  </section>;
}
