import { useState } from 'react';
import { useApi } from './api';

type Prediction = {
  id: number; model_id: string; symbol: string; time: string; mode: string;
  prediction: { probability_target: number; probability_stop: number; probability_timeout: number;
    execution_allowed: false; quote_assumption?: string };
  candidate: { direction: string; source: string };
};

export default function ShadowPanel() {
  const { data, error } = useApi<Prediction[]>('/api/predictions');
  const [mode, setMode] = useState('ALL');
  const records = (data ?? []).filter(p => mode === 'ALL' || p.mode === mode);
  const percent = (value: number) => `${(value*100).toFixed(1)}%`;
  return <section className="panel events" aria-label="Shadow model observations">
    <div className="panel-heading"><div><h2>Shadow observations</h2><p className="muted" style={{marginTop: 8, fontSize: 10}}>
      Experimental model estimates. Never order approvals. Replay quotes use explicit historical cost assumptions.</p></div>
      <select aria-label="Filter prediction mode" value={mode} onChange={e => setMode(e.target.value)}>
        <option value="ALL">All observations</option><option value="SHADOW">Streaming shadow</option><option value="SHADOW_REPLAY">Historical replay</option>
      </select></div>
    {error && <p className="error-banner" role="alert">{error}</p>}
    {!records.length ? <div className="empty"><h3>No shadow observations</h3><p>Explicitly deploy a compatible candidate model to shadow mode, then replay history or evaluate current quotes. Shadow models cannot execute trades.</p></div> :
      <div className="table-scroll"><table><thead><tr><th>Time (UTC)</th><th>Instrument</th><th>Target first</th><th>Stop first</th><th>Timeout</th><th>Source / mode</th></tr></thead><tbody>
        {records.map(p => <tr key={p.id}><td title={p.model_id}>{new Date(p.time).toISOString().replace('T', ' ').slice(0,16)}</td>
          <td>{p.symbol.replace('_','/').replace('-','/')}<small>{p.candidate.direction}</small></td>
          <td className="mono">{percent(p.prediction.probability_target)}</td><td className="mono">{percent(p.prediction.probability_stop)}</td>
          <td className="mono">{percent(p.prediction.probability_timeout)}</td><td><span className="badge amber">{p.candidate.source === 'fixture' ? 'SYNTHETIC' : p.candidate.source}</span><small>{p.mode === 'SHADOW_REPLAY' ? 'Historical replay' : 'Streaming shadow'} · No execution</small></td></tr>)}
      </tbody></table></div>}
  </section>;
}
