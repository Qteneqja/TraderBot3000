import { useApi } from './api';

type Explanation = { summary: string; risks: string[]; limitations: string[] };
type Data = { status: string; enabled: boolean; provider: string; model: string; max_calls_per_day: number;
  records: { id: string; source_kind: string; state: string; facts: { symbol?: string; classification?: string };
    explanation: Explanation | null; error_type: string | null }[] };

export default function Narratives() {
  const { data, error } = useApi<Data>('/api/narratives');
  return <section className="panel" aria-label="AI commentary">
    <div className="panel-heading"><h2>AI commentary</h2><span className="badge">NARRATIVE ONLY</span></div>
    <p>DeepSeek explains recorded evidence. Commentary cannot place trades, change risk limits, activate models or supply training labels.</p>
    {error && <p role="alert">{error} Commentary records may be stale.</p>}
    <p>{data ? `${data.provider} / ${data.model}: ${data.status.replaceAll('_', ' ')}. Daily request cap: ${data.max_calls_per_day}.` : 'Commentary status unavailable.'}</p>
    {!data?.records?.length ? <p>No AI commentary recorded.</p> : data.records.map(row => <article className="model-record" key={row.id}>
      <h3>{row.facts.symbol || 'Recorded event'} · {row.source_kind.replaceAll('_', ' ')}</h3>
      <p>{row.facts.classification} · {row.state}</p>
      {row.explanation ? <><p>{row.explanation.summary}</p>
        {!!row.explanation.risks.length && <p>Risks: {row.explanation.risks.join(' ')}</p>}
        {!!row.explanation.limitations.length && <p>Limitations: {row.explanation.limitations.join(' ')}</p>}</>
        : <p>{row.error_type ? `Explanation unavailable (${row.error_type}).` : 'Waiting for a bounded commentary request.'} Quantitative decisions remain unchanged.</p>}
    </article>)}
    <p>AI text is untrusted commentary. Market-trained models and verified validation results remain separate. API calls do not fine-tune DeepSeek.</p>
  </section>;
}
