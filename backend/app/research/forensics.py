"""Causal candidate/outcome diagnostics on a declared pre-final prefix only."""

from collections import Counter
from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from app.backtesting.simulator import simulate_trade
from app.indicators.features import compute, frame
from app.machine_learning.candidate_training import CANDIDATE_FEATURES, prediction_features
from app.machine_learning.training import scores
from app.schemas.domain import Quote
from app.strategies.registry import candidates_from_row

D = Decimal


def session_name(when):
    # Declared research session features, not broker opening/holiday calendars.
    london = 8 <= when.astimezone(ZoneInfo('Europe/London')).hour < 17
    new_york = 8 <= when.astimezone(ZoneInfo('America/New_York')).hour < 17
    return 'OVERLAP' if london and new_york else 'LONDON' if london else 'NEW_YORK' if new_york else 'OTHER'


def scan_outcomes(candles, tick, costs, strategies, *, horizon=12, stage=None):
    """Instrument the same proposal/drift/simulator definitions without changing training."""
    if horizon not in (6, 12, 24, 48) or not strategies:
        raise ValueError('A bounded predeclared horizon and strategy set are required')
    data = compute(frame(candles))
    if len(data) != len(candles) or list(data.index) != [c.time for c in candles]:
        raise ValueError('Only ordered complete candles from one scope are supported')
    if len(candles) < 60+horizon:
        raise ValueError('Insufficient prefix for full context and outcome windows')
    timeframe = candles[0].timeframe
    breaks = np.r_[0, np.cumsum(np.diff(data.index.asi8) != timeframe*1_000_000_000)]
    counters = {name: Counter() for name in strategies}
    records = []
    for i in range(59, len(candles)-horizon):
        if stage and i % 10000 == 0:
            stage('SCAN_PROGRESS', {'bar': i, 'candles': len(candles)})
        if breaks[i+horizon] != breaks[i-59]:
            for count in counters.values():
                count['gap_windows_not_evaluated'] += 1
            continue
        bar = candles[i]
        when = bar.time + timedelta(seconds=timeframe)
        row = data.iloc[i]
        for candidate in candidates_from_row(row, bar.symbol, timeframe, bar.source, when, tick, strategies):
            count = counters[candidate.strategy]
            count['generated_candidates'] += 1
            quote = Quote(symbol=bar.symbol, source=bar.source, time=when,
                          bid=candles[i+1].open-costs.spread/2, ask=candles[i+1].open+costs.spread/2)
            market = quote.ask if candidate.direction == 'LONG' else quote.bid
            distance = abs(candidate.entry-candidate.stop)
            if abs(market-candidate.entry) > max(distance*D('.1'), tick*2):
                count['entry_drift_rejections'] += 1
                continue
            future = candles[i+1:i+horizon+1]
            result = simulate_trade(future, candidate.direction, candidate.entry, candidate.stop,
                                    candidate.target, D(1), costs)
            if result['status'] != 'CLOSED':
                count['unfilled_or_invalidated'] += 1
                continue
            count['valid_candidates'] += 1
            label = 1 if result['reason'] == 'TAKE_PROFIT' else 2 if result['reason'] == 'TIMEOUT' else 0
            side = D(1) if candidate.direction == 'LONG' else D(-1)
            fill, half = D(result['entry']), costs.spread/2
            held = future[:result['bars']]
            favourable = max(D(0), max((b.high-half-fill if side > 0 else fill-b.low-half) for b in held))
            adverse = max(D(0), max((fill-b.low+half if side > 0 else b.high+half-fill) for b in held))
            records.append(prediction_features(candidate, quote) | {
                'time': when, 'label_end': future[-1].time+timedelta(seconds=timeframe),
                'strategy': candidate.strategy, 'direction_name': candidate.direction, 'regime': candidate.regime,
                'session': session_name(when), 'volatility_state': 'LOW' if row.atr_pct < .00015 else
                    'HIGH' if row.atr_pct > .025 else 'NORMAL',
                'label': label, 'reason': result['reason'], 'bars': result['bars'],
                'net_per_unit': result['pnl'], 'fees_per_unit': result['fees'],
                'net_r': float(D(result['pnl'])/distance),
                'favourable_r_bar_envelope': float(favourable/distance),
                'adverse_r_bar_envelope': float(adverse/distance),
                'candidate_id': candidate.id,
            })
    return pd.DataFrame(records), {key: dict(value) for key, value in counters.items()}


def block_interval(samples, *, draws=2000):
    """Exploratory daily-block interval, not policy acceptance or selection correction."""
    if samples.empty:
        return None
    days = samples.time.dt.floor('D')
    grouped = samples.assign(day=days, target=(samples.label == 1).astype(int)).groupby('day').agg(
        count=('label', 'size'), targets=('target', 'sum'), total_r=('net_r', 'sum'))
    grouped = grouped.reindex(pd.date_range(grouped.index.min(), grouped.index.max(), freq='D'), fill_value=0)
    rng = np.random.default_rng(42)
    starts = rng.integers(0, len(grouped), size=(draws, int(np.ceil(len(grouped)/5))))
    indices = ((starts[..., None]+np.arange(5)) % len(grouped)).reshape(draws, -1)[:, :len(grouped)]
    counts = grouped['count'].to_numpy()[indices].sum(axis=1)
    valid = counts > 0
    frequencies = grouped.targets.to_numpy()[indices].sum(axis=1)[valid]/counts[valid]
    means = grouped.total_r.to_numpy()[indices].sum(axis=1)[valid]/counts[valid]
    return {'method': 'Exploratory circular five-calendar-day blocks; seed 42', 'draws': draws,
            'target_frequency_95_interval': np.quantile(frequencies, [.025, .975]).tolist(),
            'mean_candidate_net_r_95_interval': np.quantile(means, [.025, .975]).tolist(),
            'limitations': 'Candidate windows overlap; not portfolio P&L, simultaneous inference or qualification.'}


def summarize(samples):
    if samples.empty:
        return {'candidates': 0, 'outcome_counts': {}, 'mean_net_per_unit': None}
    amounts = sorted(D(str(v)) for v in samples.net_per_unit)
    n = len(amounts)
    median = amounts[n//2] if n % 2 else (amounts[n//2-1]+amounts[n//2])/2
    return {'candidates': n, 'outcome_counts': {str(k): int(v) for k, v in samples.label.value_counts().items()},
            'target_frequency': float((samples.label == 1).mean()),
            'mean_net_per_unit': str(sum(amounts, D(0))/n), 'median_net_per_unit': str(median),
            'mean_net_r': float(samples.net_r.mean()),
            'mean_favourable_r_bar_envelope': float(samples.favourable_r_bar_envelope.mean()),
            'mean_adverse_r_bar_envelope': float(samples.adverse_r_bar_envelope.mean()),
            'holding_bars_quantiles': {str(q): float(samples.bars.quantile(q)) for q in (0, .25, .5, .75, 1)},
            'uncertainty': block_interval(samples)}


def outcome_report(samples, counters):
    report = {}
    for strategy, counts in counters.items():
        rows = samples[samples.strategy == strategy] if not samples.empty else samples
        segments = {}
        if not rows.empty:
            for key in ('direction_name', 'regime', 'session', 'volatility_state'):
                segments[key] = {str(name): summarize(part) for name, part in rows.groupby(key)}
        report[strategy] = {'counts': counts, 'summary': summarize(rows), 'segments': segments}
    return report


def probability_report(labels, probabilities):
    values = np.asarray(probabilities, dtype=float)
    if not len(labels) or values.shape != (len(labels), 3) or not np.isfinite(values).all() or (values < 0).any() or (
            values > 1).any() or not np.allclose(values.sum(axis=1), 1):
        raise ValueError('Invalid three-outcome predictions')
    return scores(labels, values) | {
        'target_quantiles': {str(q): float(np.quantile(values[:, 1], q)) for q in (0, .25, .5, .75, .95, 1)},
        'target_threshold_counts_diagnostic_only': {str(t): int((values[:, 1] >= t).sum()) for t in (.5, .6, .7, .8)},
        'actual_class_counts': np.bincount(labels, minlength=3).tolist(), 'execution_authority': False}


def diagnose_model(version, model, samples):
    meta = version.metadata_json
    if samples.empty:
        return {'model': version.id, 'status': 'INSUFFICIENT_PRE_FINAL_PREFIX', 'execution_authority': False}
    rows = samples[samples.strategy == meta['strategy']]
    parts = {key: rows[(rows.time >= pd.Timestamp(bounds[0])) & (rows.time <= pd.Timestamp(bounds[1]))]
             for key, bounds in meta['partitions'].items() if key in ('train', 'calibration', 'validation')}
    train, valid = parts['train'], parts['validation']
    if train.empty or valid.empty:
        return {'model': version.id, 'status': 'INSUFFICIENT_PRE_FINAL_PREFIX', 'execution_authority': False}
    features = valid[CANDIDATE_FEATURES]
    if not np.isfinite(features.to_numpy()).all():
        raise ValueError('Nonfinite validation features')
    calibrated = model.predict_proba(features)
    raw = model.estimator.predict_proba(features)
    reference = np.bincount(train.label.to_numpy(dtype=int), minlength=3)/len(train)
    means = np.array([train[train.label == label].net_r.mean() for label in range(3)])
    if not np.isfinite(means).all():
        raise ValueError('All training outcomes are required for conditional-return diagnostics')
    full_ev = calibrated @ means
    ev_selected = valid[full_ev > 0]
    return {'model': version.id, 'status': 'DIAGNOSTIC_ONLY', 'artifact_sha256': meta['artifact_sha256'],
            'recorded_full_validation': meta['validation'], 'diagnostic_validation_samples': len(valid),
            'recorded_validation_samples': meta['sample_counts']['validation'],
            'diagnostic_scope': 'Only validation samples whose full outcomes precede the declared common final seal',
            'raw': probability_report(valid.label.to_numpy(dtype=int), raw),
            'calibrated': probability_report(valid.label.to_numpy(dtype=int), calibrated),
            'class_frequency_baseline': probability_report(valid.label.to_numpy(dtype=int), np.tile(reference, (len(valid), 1))),
            'class_mean_net_r_training_only': means.tolist(), 'validation_observed_mean_net_r': float(valid.net_r.mean()),
            'predicted_full_outcome_mean_net_r': float(full_ev.mean()),
            'positive_ev_diagnostic_candidates': len(ev_selected),
            'positive_ev_observed_mean_net_r': float(ev_selected.net_r.mean()) if len(ev_selected) else None,
            'uncertainty': block_interval(valid),
            'ev_limitations': 'Training conditional outcome means; selection research, overlapping candidates, no portfolio or execution authority.',
            'execution_authority': False}
