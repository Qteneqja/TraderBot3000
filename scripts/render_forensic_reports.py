"""Render sanitized measured evidence; never runs training or opens a final test."""

import argparse
import json
from pathlib import Path


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str, row))+' |' for row in rows])+'\n'


def render(forensics, hypotheses, native, output):
    output.mkdir(parents=True, exist_ok=True)
    models = [m for scope in forensics['scopes'] for m in scope['models']]
    text = ['# Measured model root-cause analysis', '',
        'Measured 2026-10-15 UTC. Diagnostic only; no execution authority. Original final-test outcomes remain sealed.', '',
        '## Data and label definitions', '',
        ('The original twelve-bar label is stop=0, target=1, timeout=2. It asks whether a target at least 2.5R away is reached within one hour after a valid next-bar entry. It is not the probability of any profitable exit. '
        'The stop is at least 1.5 ATR or ten instrument ticks. Target rounding preserves reward outward. Same-bar stop/target ambiguity uses stop first. '
        'Entry drift is conditioned on the modeled next-open quote. Warm-up/context and the entire outcome window must be contiguous. No gaps are filled.'), '',
        'The current research code contract is `'+forensics['plan']['code']['core']['sha256']+'`. '
        'The forensic scanner exactly matches the original training features and labels under the same modeled costs in regression tests. '
        'Runtime feature parity is tested at the same quote/time. This does not prove parity with future broker fills, variable intrabar spreads or a different order type.', '',
        table(['Symbol', 'Prefix candles', 'Final seal (UTC)'], [(s['scope']['symbol'], s['scope']['input_candles']['count'],
            s['scope']['sealed_before']) for s in forensics['scopes']]),
        '## Outcomes before model selection', '',
        ('Counts include overlapping proposals, not independent trades or a risk-approved portfolio. Drift rejections are reported separately; gap counts are windows, not candidate counts. '
        'Per-direction, regime, declared DST-aware London/New York session and fixed ATR-volatility segments, holding durations, full exit-bar MFE/MAE envelopes and exploratory block intervals are in the immutable JSON.'), '',
        table(['Symbol', 'Strategy', 'Generated', 'Drift rejected', 'Valid', 'Stop', 'Timeout', 'Target', 'Target %'],
            [(s['scope']['symbol'], name, x['counts'].get('generated_candidates', 0),
              x['counts'].get('entry_drift_rejections', 0), x['summary']['candidates'],
              x['summary']['outcome_counts'].get('0', 0), x['summary']['outcome_counts'].get('2', 0),
              x['summary']['outcome_counts'].get('1', 0), f"{100*x['summary']['target_frequency']:.2f}")
             for s in forensics['scopes'] for name, x in s['outcomes'].items()]),
        '## Raw versus calibrated probabilities', '',
        ('The comparison uses identical validation rows for each raw/calibrated pair. A common per-symbol final seal can truncate the original validation period; full stored validation metrics remain separate. '
        'All 19 calibrated models improve both Brier and log loss versus their raw estimators on these matched rows. Some still lose to the training-frequency baseline. '
        'This supports retaining calibration; it does not establish reliable high-probability opportunities. All calibrated maxima remain below .80. '
        'The catalog preserves metadata for all 57 registered versions; incompatible historical/fixture artifacts are not rescored as current models.'), '',
        table(['Model', 'Matched n', 'Raw max', 'Cal max', 'Raw Brier', 'Cal Brier', 'Baseline Brier'],
            [(m['model'], m['diagnostic_validation_samples'], f"{m['raw']['target_quantiles']['1']:.4f}",
              f"{m['calibrated']['target_quantiles']['1']:.4f}", f"{m['raw']['multiclass_brier']:.4f}",
              f"{m['calibrated']['multiclass_brier']:.4f}", f"{m['class_frequency_baseline']['multiclass_brier']:.4f}") for m in models]),
        ('Six raw-probability sklearn log-loss normalization warnings were emitted in the forensic run; values were not silently adjusted. '
        'The horizon-filter test/run also emits a NumPy generic-timedelta deprecation warning. Neither warning is a repaired production defect. '
        'No evidence here supports removing calibration or lowering the .80 threshold.'), '',
        '## Separate expected-value diagnostic', '',
        ('Training-only mean net R for stop, target and timeout outcomes is weighted by calibrated three-class probabilities. This accounts for empirical timeout returns in research only. '
        'Eighteen models select no positive-EV validation candidates. GBP XGBoost selects three, whose observed average is -0.3604R. '
        'That result has insufficient sample size and no execution authority. The deterministic risk policy remains unchanged.'), '',
        '## BTC native fault', '',
        'The original corrected campaign child exited -11 after registering the BTC logistic model, without a completed batch result. The old failed run remains failed. '
        'Its historical stack is unavailable. The new bounded reproduction separately completed verified logistic loading, base and doubled-cost validation replay (zero trades each), '
        'then two single-thread LightGBM fit/calibration/serialization cycles. Reloaded predictions matched exactly. '
        'Observed maximum RSS was 819620 KiB; feature memory was '+str(native['feature_memory_bytes'])+' bytes. '
        'The declared cap was 4 GiB address space and 900 CPU seconds; all reported native pools had one thread. '
        'Status: **NOT_REPRODUCED_UNDER_DECLARED_SINGLE_THREAD_LIMITS**. Original cause: **UNRESOLVED**. '
        'This does not prove that thread count caused the original fault or repair historical evidence.', '',
        '## Decision', '',
        ('The target event is rare, entry drift removes many proposals, calibration reduces unsupported confidence, and the bounded alternatives do not show robust positive candidate returns. '
        'No new production model fits are justified by these results. Deep learning is deferred until a causal hypothesis has enough independent evidence and a fair bounded baseline comparison. '
        'See [strategy comparisons](STRATEGY_COMPARISON.md), [cost evidence](EXECUTION_COST_VALIDATION.md) and [experiment registry](RESEARCH_EXPERIMENT_REGISTRY.md).'), '']
    (output/'MODEL_ROOT_CAUSE_ANALYSIS.md').write_text('\n'.join(text), encoding='utf-8')
    rows = []
    for c in hypotheses['cases']:
        s, case = c['summary'], c['case']
        interval = s.get('uncertainty', {}).get('mean_candidate_net_r_95_interval')
        rows.append((c['symbol'], case['strategy'], case['filter'], case['horizon'], s['candidates'],
            f"{100*s.get('target_frequency', 0):.2f}", f"{s.get('mean_net_r', 0):.4f}",
            ', '.join(f'{v:.4f}' for v in interval) if interval else 'UNKNOWN'))
    text = ['# Bounded strategy comparisons', '',
        'Measured 2026-10-15 UTC. All twenty preregistered cases are reported. No new production model was fitted or qualified.', '',
        ('Trend immediate entries were measured at 6/12/24/48 five-minute bars; trend pullback plus completed-hour trend confirmation at 12/48; '
        'breakout immediate and prior-bar breakout/retest confirmation at 12/48, each on EUR/USD and GBP/USD. '
        'Filters use completed current/prior bars and only hours containing twelve observed five-minute bars, joined at hour completion. '
        'They filter existing market proposals; they do not simulate limit-order execution. Different horizons receive separate diagnostic outcome schema identifiers.'), '',
        table(['Symbol', 'Strategy', 'Entry filter', 'Bars', 'Candidates', 'Target %', 'Mean net R', 'Exploratory 95% mean-R interval'], rows), '',
        ('All immediate-entry trend/breakout means remain negative. EUR pullback has positive sample means but only 46/44 candidates, and both intervals cross zero. '
        'GBP pullback and both breakout-retest hypotheses have negative means. No comparison supplies robust positive evidence or sufficient calibrated trade activity.'), '',
        ('Holding windows overlap. Intervals use 2,000 circular five-calendar-day block resamples with seed 42; they are exploratory, not multiplicity-adjusted discoveries or portfolio return bounds. '
        'The JSON also reports common-candidate paired horizon subsets (1,677 EUR and 2,614 GBP trend candidates) so changing gap/end exclusions is visible. '
        'This is a candidate-return comparison, not portfolio profit factor, drawdown, walk-forward qualification or a final test. '
        'Historical commission, financing, fills and CAD conversions remain unverified; the old estimated costs were frozen for comparability.'), '',
        ('Next defensible step: obtain cost evidence and a separately preregistered hypothesis with enough candidates. '
        'Do not select the sparse positive EUR subset, retune on its observed outcomes, or call a longer horizon an improved deployed model.'), '']
    (output/'STRATEGY_COMPARISON.md').write_text('\n'.join(text), encoding='utf-8')
    (output/'RESEARCH_EXPERIMENT_REGISTRY.md').write_text('\n'.join([
        '# Research experiment registry', '',
        ('All entries below were declared and audit-persisted before execution on 2026-10-15 UTC. '
        'No threshold, promotion policy, risk setting or original research attempt was changed. Files are in the ignored research-data volume.'), '',
        table(['Experiment', 'ID', 'Scope', 'Result'], [
            ('Forensic outcomes/calibration', forensics['experiment'], '4 assets / 6 strategies / 19 compatible models; all 57 metadata cataloged', 'COMPLETED; no authority'),
            ('BTC native reproduction', '47a9b03d41c7615e1b327fbb33322a16440c836bd33dbff67db48c5fc3417086', '2 diagnostic LightGBM fits only; no registry publication', native['status']),
            ('Entry/horizon ablations', '53cb8ebd1333cfab7628669e9a42a9fb7affb324d5458f802db85080adeb9cf6', '20 declared EUR/GBP cases; zero model fits', 'COMPLETED; no robust positive evidence')]), '',
        ('The forensic directory is `/app/data/reports/forensics/ID`; native reproduction is `/app/data/reports/native-reproductions/ID`; '
        'hypotheses are `/app/data/reports/hypotheses/ID`. Each contains immutable plan/claim/result files and append-only stage checkpoints. '
        'Plans bind code hashes, frozen data/cost manifests, final seals and resource caps. Existing claims reject automatic reruns. '
        'Do not delete a claim, overwrite a report, retry an old failed attempt or edit a declared implementation to reuse its identity.'), '',
        ('The previous corrected campaign remains preserved in [its qualification report](FINAL_MODEL_QUALIFICATION_REPORT.md). '
        'The new completed BTC diagnostic replay does not convert that failed campaign into a successful batch. '
        'No genuinely future final-test reservation exists. Research declarations are not activation or broker authorization.'), '']), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--forensics', type=Path, required=True)
    parser.add_argument('--hypotheses', type=Path, required=True)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('docs'))
    args = parser.parse_args()
    render(*(json.loads(p.read_text()) for p in (args.forensics, args.hypotheses, args.native)), args.output)
