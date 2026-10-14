import { useState } from 'react';
import { Activity, ArrowDownLeft, ArrowUpRight, Bell, BookOpen, Boxes, ChevronRight, CircleHelp,
  Cpu, FlaskConical, LayoutDashboard, Radio, RefreshCw, Shield, ShieldCheck, SlidersHorizontal,
  TrendingUp, Wallet } from 'lucide-react';
import Chart from './Chart';
import ShadowPanel from './ShadowPanel';
import { useApi, type Candle, type Model, type Order, type Overview, type Signal, type Strategy, type System } from './api';

const nav = [
  { label: 'Overview', icon: LayoutDashboard }, { label: 'Markets', icon: TrendingUp },
  { label: 'AI signals', icon: Activity }, { label: 'Trade journal', icon: BookOpen },
  { label: 'Strategies', icon: Boxes }, { label: 'Model lab', icon: Cpu },
  { label: 'Risk controls', icon: ShieldCheck }, { label: 'System health', icon: Radio },
];
const symbols = ['EUR_USD', 'GBP_USD', 'BTC-USD', 'ETH-USD'];
const displaySymbol = (s: string) => s.replace('_', '/').replace('-', '/');
const money = (n: number | string | undefined) => n === undefined ? '—' : new Intl.NumberFormat('en-US',
  { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(+n);
const human = (s: string) => s.toLowerCase().replaceAll('_', ' ');
const pct = (n: number) => `${(n * 100).toFixed(1)}%`;
const price = (n: string | number, s: string) => (+n).toFixed(s.includes('_') ? 5 : 2);

export function Badge({ children, tone = '' }: { children: React.ReactNode; tone?: string }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

function Empty({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="empty"><FlaskConical size={28}/><h3>{title}</h3><p>{children}</p></div>;
}

function SignalTable({ signals, onSelect }: { signals: Signal[]; onSelect: (s: Signal) => void }) {
  return <div className="table-scroll"><table><thead><tr><th>Instrument / strategy</th><th>Direction</th>
    <th>Entry</th><th>Probability</th><th>Status</th><th></th></tr></thead><tbody>
    {signals.map(s => <tr key={s.id} onClick={() => onSelect(s)}><td><strong>{displaySymbol(s.symbol)}</strong>
      <small>{human(s.strategy)}</small></td><td><span className={s.payload.direction === 'LONG' ? 'positive' : 'negative'}>
        {s.payload.direction === 'LONG' ? <ArrowUpRight size={14}/> : <ArrowDownLeft size={14}/>} {s.payload.direction}</span></td>
      <td className="mono">{price(s.payload.entry, s.symbol)}</td><td className="muted">{s.payload.probability === null ? 'Uncalibrated' : pct(+s.payload.probability)}</td>
      <td><Badge tone={s.status === 'APPROVED' ? 'green' : 'amber'}>{human(s.status)}</Badge></td>
      <td><button className="icon-button" aria-label={`Inspect ${displaySymbol(s.symbol)} ${s.strategy} signal`} onClick={e => { e.stopPropagation(); onSelect(s); }}><ChevronRight size={16}/></button></td></tr>)}
  </tbody></table>{!signals.length && <Empty title="No signals yet">Candidates appear here after market evaluation. Rejected opportunities are retained.</Empty>}</div>;
}

export default function App() {
  const [page, setPage] = useState('Overview');
  const [symbol, setSymbol] = useState('EUR_USD');
  const [timeframe, setTimeframe] = useState(300);
  const [selected, setSelected] = useState<Signal | null>(null);
  const [filter, setFilter] = useState('ALL');
  const overview = useApi<Overview>('/api/overview');
  const signals = useApi<Signal[]>('/api/signals');
  const candles = useApi<{ source: string; candles: Candle[] }>(`/api/candles?symbol=${symbol}&timeframe=${timeframe}`);
  const orders = useApi<Order[]>('/api/orders');
  const strategies = useApi<Strategy[]>('/api/strategies');
  const models = useApi<Model[]>('/api/models');
  const risk = useApi<Record<string, number | boolean>>('/api/risk');
  const system = useApi<System>('/api/system');
  const data = overview.data;
  const error = overview.error || signals.error || candles.error || orders.error || strategies.error || models.error || risk.error || system.error;
  const last = candles.data?.candles.at(-1);
  const previous = candles.data?.candles.at(-2);
  const change = last && previous ? (+last.close/+previous.close-1) : null;
  const equity = +(data?.account.equity ?? 0);
  const refresh = () => [overview, signals, candles, orders, strategies, models, risk, system].forEach(r => r.refresh());
  const title = page === 'Overview' ? 'Your trading command center' : page;
  const subtitle: Record<string, string> = {
    Overview: 'A clear view of your markets, decisions, and risk.', Markets: 'Completed candles. Traceable sources. No invented prices.',
    'AI signals': 'Every opportunity, including the ones worth passing on.', 'Trade journal': 'A durable record of executions and outcomes.',
    Strategies: 'Testable market hypotheses, built independently.', 'Model lab': 'Evidence before confidence. Validation before deployment.',
    'Risk controls': 'Deterministic limits with final authority over every entry.', 'System health': 'Visibility into every part of the trading pipeline.',
  };

  return <div className="app-shell">
    <aside className="sidebar"><a href="#" className="brand" onClick={e => { e.preventDefault(); setPage('Overview'); }}>
      <span className="brand-icon"><Shield size={23}/></span><span>AEGIS<span className="brand-light">TRADE</span><small>INTELLIGENCE, WITH DISCIPLINE</small></span></a>
      <div className="workspace"><span className="workspace-avatar">A</span><div>Trading workspace<small>Personal · Research</small></div><SlidersHorizontal size={14}/></div>
      <div className="nav-label">WORKSPACE</div><nav>{nav.map(({ label, icon: Icon }) => <button key={label}
        className={page === label ? 'nav-item active' : 'nav-item'} onClick={() => setPage(label)} aria-current={page === label ? 'page' : undefined}>
        <Icon size={18}/><span>{label}</span>{label === 'AI signals' && <span className="nav-count">{signals.data?.length ?? 0}</span>}
      </button>)}</nav>
      <div className="sidebar-bottom"><div className="guard-card"><ShieldCheck size={19}/><strong>Designed to abstain</strong><p>No validated edge?<br/>No trade. Your limits come first.</p></div>
        <button className="nav-item" onClick={() => setPage('System health')}><CircleHelp size={18}/>Connection & setup</button>
        <div className="profile"><span className="avatar">OP</span><div>Local operator<small>Read-only dashboard</small></div><span className="status-dot"/></div></div>
    </aside>
    <div className="main-shell"><header className="topbar"><div className="breadcrumb">Workspace <ChevronRight size={13}/><span>{page}</span></div>
      <div className="top-actions"><span className="connection"><span className={`status-dot ${error ? 'red' : ''}`}/>{error ? 'Connection issue' : data ? 'API connected' : 'Connecting'}</span>
        <span className="divider"/><Badge tone="green">{data?.mode.replace('_', ' ') ?? '—'}</Badge><button className="icon-button" aria-label="View system events" onClick={() => setPage('System health')}><Bell size={18}/></button></div></header>
      <main><div className="heading"><div><div className="eyebrow">AEGISTRADE INTELLIGENCE</div><h1>{title}</h1><p>{subtitle[page]}</p></div>
        <button className="button" onClick={refresh}><RefreshCw size={14}/>Refresh</button></div>
      {error && <div role="alert" className="error-banner">{error} Displayed records may be stale.</div>}
      {data?.demo && <div className="demo-banner"><FlaskConical size={17}/><span><strong>Offline research workspace</strong> · Charts use labeled synthetic fixtures. Account funds are simulated.</span><span className="banner-tail">NO REAL MONEY</span></div>}
      {(page === 'Overview' || page === 'Markets') && <>
        {page === 'Overview' && <section className="stat-grid" aria-label="Account overview">
          <Stat label="Paper account equity" value={money(data?.account.equity)} icon={<Wallet size={17}/>} detail="USD · Simulated capital"/>
          <Stat label="Daily P&L" value={data ? money(equity-(+data.account.day_start)) : '—'} icon={<TrendingUp size={17}/>} detail="Includes marked open positions"/>
          <Stat label="Open positions" value={data ? `${data.open_positions} / 3` : '—'} icon={<Boxes size={17}/>} detail={`${data?.pending_orders ?? 0} pending orders`}/>
          <Stat label="Planned portfolio risk" value={data ? pct(equity ? data.planned_risk/equity : 0) : '—'} icon={<ShieldCheck size={17}/>} detail="1.5% maximum planned risk"/>
        </section>}
        <div className="market-grid"><section className="panel market-panel"><div className="panel-heading"><div className="panel-title"><TrendingUp size={17}/><h2>Market overview</h2></div><Badge>{candles.data?.source === 'fixture' ? 'SYNTHETIC FIXTURE' : candles.data?.source ?? 'NO DATA'}</Badge></div>
          <div className="market-tabs">{symbols.map(s => <button key={s} className={s === symbol ? 'selected' : ''} onClick={() => setSymbol(s)}>{displaySymbol(s)}<small>{s.includes('_') ? 'FOREX' : 'CRYPTO'}</small></button>)}</div>
          <div className="chart-toolbar"><div><strong className="chart-price">{last ? price(last.close, symbol) : '—'}</strong><span className={change !== null && change >= 0 ? 'positive' : 'negative'}>{change !== null ? `${change >= 0 ? '+' : ''}${pct(change)}` : ''}</span><small>Last completed candle · {last ? new Date(last.time).toLocaleDateString('en-CA', { timeZone: 'UTC' }) + ' UTC' : 'Awaiting data'}</small></div>
            <div className="timeframes">{[[60, '1m'], [300, '5m'], [900, '15m'], [3600, '1h']].map(([v, label]) => <button key={v} className={timeframe === v ? 'selected' : ''} onClick={() => setTimeframe(+v)}>{label}</button>)}</div></div>
          <Chart candles={candles.data?.candles ?? []} symbol={symbol}/><div className="chart-footer"><span><span className="status-dot amber-dot"/> {data?.demo ? 'Historical synthetic demonstration · Not a live quote' : 'Provider candles · Verify feed freshness before execution'}</span><span>UTC</span></div>
        </section><aside className="market-aside"><section className="panel guard-panel"><div className="panel-heading"><div className="panel-title"><ShieldCheck size={17}/><h2>Execution guard</h2></div><span className="status-dot"/></div>
          <div className="guard-visual"><ShieldCheck size={32}/></div><h3>Capital preservation first.</h3><p>New entries require current data, a validated model, and independent risk approval.</p>
          <div className="check-row"><span>Real-money execution</span><Badge>DISABLED</Badge></div><div className="check-row"><span>Model calibration</span><Badge tone="amber">UNVALIDATED</Badge></div><div className="check-row"><span>New paper entries</span><Badge tone="amber">{data?.account.suspended ? 'SUSPENDED' : 'AWAITING EVIDENCE'}</Badge></div>
          <button className="text-button" onClick={() => setPage('Risk controls')}>Inspect risk controls <ArrowUpRight size={15}/></button></section>
          <section className="panel research-note"><span className="eyebrow"><Cpu size={14}/> RESEARCH STATUS</span><h3>Confidence is earned.</h3><p>No calibrated probability is published until a model has supporting validation results.</p><button className="text-button" onClick={() => setPage('Model lab')}>Open model lab <ArrowUpRight size={15}/></button></section></aside></div>
      </>}
      {(page === 'Overview' || page === 'AI signals') && <section className="panel signals-panel"><div className="panel-heading"><div className="panel-title"><Activity size={17}/><h2>{page === 'Overview' ? 'Latest opportunities' : 'Signal decisions'}</h2><span className="count">{signals.data?.length ?? 0}</span></div>
        {page === 'Overview' ? <button className="text-button" onClick={() => setPage('AI signals')}>View all signals <ChevronRight size={14}/></button> : <select aria-label="Filter signal status" value={filter} onChange={e => setFilter(e.target.value)}><option value="ALL">All decisions</option><option value="APPROVED">Approved</option><option value="REJECTED">Rejected</option></select>}</div>
        <SignalTable signals={(signals.data ?? []).filter(s => page === 'Overview' || filter === 'ALL' || s.status === filter).slice(0, page === 'Overview' ? 4 : 100)} onSelect={setSelected}/></section>}
      {page === 'Trade journal' && <section className="panel"><div className="panel-heading"><h2>Execution history</h2><Badge>PAPER PORTFOLIO</Badge></div>
        {!orders.data?.length ? <Empty title="A clean trading journal">No executions recorded. Once a qualified paper trade is filled, its lifecycle and outcome will appear here.</Empty> :
          <div className="table-scroll"><table><thead><tr>{['Instrument', 'Direction', 'Units', 'Entry', 'Stop', 'Target', 'Status', 'Fees paid', 'Net P&L'].map(c => <th key={c}>{c}</th>)}</tr></thead><tbody>{orders.data.map(o => <tr key={o.id}><td>{displaySymbol(o.symbol)}</td><td>{o.direction}</td><td>{o.units}</td><td>{price(o.entry, o.symbol)}</td><td>{price(o.stop, o.symbol)}</td><td>{price(o.target, o.symbol)}</td><td><Badge>{o.state}</Badge></td><td>{money(o.fees_paid)}</td><td>{o.pnl === null ? 'Open' : money(o.pnl)}</td></tr>)}</tbody></table></div>}</section>}
      {page === 'Strategies' && <div className="card-grid">{strategies.data?.map((s, i) => <section key={s.id} className="panel strategy-card"><div className="strategy-index">0{i+1}<Badge>RESEARCH · V{s.version}</Badge></div><h2>{s.name}</h2><p>Eligible in {s.regimes.map(human).join(', ')} conditions.</p><div className="check-row"><span>Validated trading edge</span><Badge tone="amber">NOT ESTABLISHED</Badge></div><small>Deterministic signals · Independent risk approval</small></section>)}</div>}
      {page === 'Model lab' && <section className="panel"><div className="panel-heading"><div className="panel-title"><Cpu size={18}/><h2>Model registry</h2></div><Badge>EXPLICIT PROMOTION ONLY</Badge></div>
        {!models.data?.length ? <Empty title="Evidence starts with research">No trained model has been registered. Import provider history, run chronological training, then inspect calibration and execution costs before deployment.</Empty> : models.data.map(m => <div className="model-record" key={m.id}><h3>{m.id} <Badge tone="amber">{m.status}</Badge></h3><p>{m.metadata_json.family} · {m.metadata_json.symbol} · {m.metadata_json.source}</p><div className="metric-row"><span>Brier score <strong>{m.metadata_json.test?.multiclass_brier.toFixed(4) ?? '—'}</strong></span><span>Log loss <strong>{m.metadata_json.test?.log_loss.toFixed(4) ?? '—'}</strong></span><span>Test observations <strong>{m.metadata_json.test?.samples ?? '—'}</strong></span></div><p>{m.metadata_json.limitations?.join(' · ')}</p></div>)}</section>}
      {page === 'Risk controls' && <><div className="risk-intro panel"><ShieldCheck size={32}/><div><h2>Risk has the final word.</h2><p>Controls are enforced by the backend. This dashboard is read-only. Changes require operator authentication and server-side validation.</p></div><Badge tone="green">LIVE DISABLED</Badge></div><div className="card-grid">{risk.data && Object.entries(risk.data).filter(([k]) => k !== 'live_enabled').map(([k, v]) => <section className="panel risk-card" key={k}><span>{human(k)}</span><strong>{typeof v === 'number' ? (k.includes('loss') || k.includes('risk') && !k.includes('reward') || k.includes('threshold') ? pct(v) : v) : String(v)}</strong><small>Enforced before every new entry</small></section>)}</div></>}
      {page === 'System health' && <><div className="card-grid">{system.data && Object.entries(system.data).filter(([k]) => k !== 'events').map(([k, v]) => <section className="panel service-card" key={k}><Radio size={18}/><h3>{human(k)}</h3><Badge tone={v === 'CONNECTED' ? 'green' : 'amber'}>{human(String(v))}</Badge></section>)}</div><section className="panel events"><div className="panel-heading"><h2>Operational events</h2><Badge>PERSISTED AUDIT LOG</Badge></div>{system.data?.events.length ? system.data.events.map(e => <div className="event" key={e.id}><span className="status-dot"/><div><strong>{human(e.kind)}</strong><p>{JSON.stringify(e.detail)}</p></div><time>{new Date(e.time).toLocaleString()}</time></div>) : <Empty title="No operational events">Worker heartbeats and failures are recorded here.</Empty>}</section></>}
      {page === 'Model lab' && <ShadowPanel/>}
      <footer><span><Shield size={13}/> AegisTrade AI <span className="muted">/</span> Research before risk.</span><span>Local workspace · v0.1.0</span></footer>
      </main></div>
    {selected && <div className="modal-backdrop" onClick={() => setSelected(null)}><section className="modal panel" role="dialog" aria-modal="true" aria-label="Signal details" onClick={e => e.stopPropagation()}><div className="panel-heading"><h2>{displaySymbol(selected.symbol)} · {human(selected.strategy)}</h2><button className="button" onClick={() => setSelected(null)}>Close</button></div><div className="modal-body"><Badge tone="amber">{selected.status}</Badge><p>{selected.payload.source === 'fixture' ? 'Synthetic demonstration signal. Not a real market recommendation.' : 'Recorded quantitative candidate.'}</p><div className="metric-row"><span>Entry<strong>{price(selected.payload.entry, selected.symbol)}</strong></span><span>Stop-loss<strong>{price(selected.payload.stop, selected.symbol)}</strong></span><span>Take-profit<strong>{price(selected.payload.target, selected.symbol)}</strong></span></div><h3>Decision reasons</h3>{selected.reasons.map(r => <p key={r} className="reason">{human(r)}</p>)}<h3>Invalidation</h3><p>{selected.payload.invalidation}</p><h3>AI explanation</h3><p>Unavailable. This decision is produced by deterministic rules; no LLM narrative has been generated.</p></div></section></div>}
  </div>;
}

function Stat({ label, value, detail, icon }: { label: string; value: string; detail: string; icon: React.ReactNode }) {
  return <article className="stat panel"><div><span>{label}</span>{icon}</div><strong>{value}</strong><small>{detail}</small></article>;
}
