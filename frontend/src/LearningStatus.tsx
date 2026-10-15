import { useApi } from './api';

type Learning = { schedules: { id: string; enabled: boolean; symbol: string; families: string[];
  strategy: string; interval_days: number; next_due: string }[]; runs: { id: string; state: string; final_test?: string;
  candidates: { model?: string; family: string; status: string; validation?: { multiclass_brier: number } }[] }[];
  outcomes: { mode: string; status: string; count: number }[] };

export default function LearningStatus() {
  const { data, error } = useApi<Learning>('/api/learning');
  return <section className="panel" aria-label="Controlled learning">
    <div className="panel-heading"><h2>Controlled learning</h2></div>
    <p>Retraining registers experimental candidates. Model activation requires separate operator approval and qualifying final evidence.</p>
    {error && <p role="alert">{error} Learning records may be stale.</p>}
    {!data?.schedules?.length ? <p>No research schedule enabled.</p> : data.schedules.map(s => <div className="model-record" key={s.id}>
      <h3>{s.symbol} · {s.strategy} · {s.enabled ? 'Scheduled' : 'Disabled'}</h3>
      <p>Every {s.interval_days} days · Next due {new Date(s.next_due).toLocaleString()} · {s.families.join(', ')}</p>
    </div>)}
    {data?.runs?.map(run => <div className="model-record" key={run.id}>
      <h3>Research run · {run.state}</h3><p>{run.final_test?.replaceAll('_', ' ') || 'Final test not approved'}</p>
      {run.candidates.map(c => <p key={c.family}>{c.family}: {c.status}{c.validation ? ` · Validation Brier ${c.validation.multiclass_brier.toFixed(4)}` : ''}</p>)}
    </div>)}
    <p>{data?.outcomes?.map(o => `${o.mode} ${o.status}: ${o.count}`).join(' · ') || 'No attributed closed outcomes reported.'}</p>
    <p>Fixture diagnostics, quarantined records, paper outcomes and broker outcomes retain separate classifications.</p>
  </section>;
}
