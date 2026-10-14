import { useEffect, useRef } from 'react';
import { CandlestickSeries, ColorType, createChart, type UTCTimestamp } from 'lightweight-charts';
import type { Candle } from './api';

export default function Chart({ candles, symbol }: { candles: Candle[]; symbol: string }) {
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!host.current || !candles.length) return;
    const chart = createChart(host.current, {
      autoSize: true, height: 360,
      layout: { background: { type: ColorType.Solid, color: '#11181e' }, textColor: '#71808c',
        fontFamily: 'ui-monospace, SFMono-Regular, Consolas, monospace', fontSize: 11 },
      grid: { vertLines: { color: '#1a242b' }, horzLines: { color: '#1a242b' } },
      rightPriceScale: { borderColor: '#26313a' },
      timeScale: { borderColor: '#26313a', timeVisible: true, secondsVisible: false },
      crosshair: { vertLine: { color: '#6b8a8c' }, horzLine: { color: '#6b8a8c' } },
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#51d8ac', downColor: '#e77583', wickUpColor: '#51d8ac', wickDownColor: '#e77583',
      borderVisible: false, priceFormat: { type: 'price', precision: symbol.includes('_') ? 5 : 2,
        minMove: symbol.includes('_') ? 0.00001 : 0.01 },
    });
    series.setData(candles.map(c => ({ time: Math.floor(Date.parse(c.time)/1000) as UTCTimestamp,
      open: +c.open, high: +c.high, low: +c.low, close: +c.close })));
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [candles, symbol]);
  return <div className="chart" ref={host} aria-label={`${symbol} candlestick chart`} role="img">
    {!candles.length && <div className="empty">No candles available for this market and timeframe.</div>}
  </div>;
}
