import { useCallback, useEffect, useState } from 'react';

export type Candle = { time: string; open: string; high: string; low: string; close: string; volume: string };
export type Signal = { id: string; time: string; symbol: string; strategy: string; status: string; reasons: string[];
  payload: { direction: string; entry: string; stop: string; target: string; regime: string;
    probability: string | null; source: string; invalidation: string } };
export type Order = { id: string; symbol: string; direction: string; units: string; state: string; entry: string;
  stop: string; target: string; pnl: string | null; fees_paid: string; execution: { source?: string };
  opened_at: string; close_reason: string | null };
export type Overview = { mode: string; demo: boolean; open_positions: number; pending_orders: number;
  planned_risk: number; signals: number; model_status: string;
  account: { balance: number; equity: number; day_start: number; week_start: number; suspended: boolean;
    reconciled: boolean; updated_at: string }; server_time: string;
  quotes: { symbol: string; bid: number; ask: number; time: string; stale: boolean }[] };
export type Strategy = { id: string; name: string; regimes: string[]; status: string; version: string };
export type Model = { id: string; status: string; created_at: string; metadata_json: { family: string; source: string;
  symbol: string; test?: { multiclass_brier: number; log_loss: number; samples: number }; limitations?: string[] } };
export type System = { database: string; oanda: string; coinbase: string; llm: string; telegram: string;
  economic_calendar: string; events: { id: number; time: string; kind: string; detail: Record<string, unknown> }[] };

export function useApi<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  const refresh = useCallback(() => setRevision(r => r + 1), []);
  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    async function load() {
      try {
        const response = await fetch(path, { signal: controller.signal });
        if (!response.ok) throw new Error(`API unavailable (${response.status}). Check the backend and database.`);
        const json = await response.json();
        setData(json); setError('');
      } catch (e) {
        if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Connection failed');
      }
    }
    void load();
    const timer = setInterval(() => void load(), 15000);
    return () => { controller.abort(); clearInterval(timer); };
  }, [path, revision]);
  return { data, error, refresh };
}
