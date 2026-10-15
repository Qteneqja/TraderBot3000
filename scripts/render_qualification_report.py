"""Render recorded validation evidence without training, scoring or opening test data."""

import argparse
import json
from pathlib import Path


def render(report):
    lines = [
        '# Final model qualification report', '',
        f"Evidence snapshot: {report['as_of']}. Campaign: `{report['campaign']}`.", '',
        '**Decision: NOT QUALIFIED. No model is eligible for activation. The genuinely future final test has NOT STARTED.**', '',
        ('This is an actual provider-data selection report. It is not a passing final-test certificate. '
        'Final model scores and final portfolio results remain sealed. All registered models remain EXPERIMENTAL.'), '',
        (f"Strategy/evaluation source contract: `{report['current_code_sha256']}`. "
        f"Predeclared contract: `{report['declared_code_sha256']}`. "
        'The strategy identity remains v1; exact evaluated source is bound by this hash, rather than a retroactively changed artifact.'), '',
        '## Completed model comparisons', '',
        ('Lower multiclass Brier is better. Calibration error is target reliability error, not win rate. '
        'Every completed model below produced zero base and doubled-cost validation trades at the unchanged 80% threshold.'), '',
        '| Asset / strategy | Family | Model version | Brier / class baseline | Calibration error | Calibration / validation samples |',
        '| --- | --- | --- | --- | --- | --- |',
    ]
    for batch in report['batches']:
        for candidate in batch['candidates']:
            if not candidate.get('model'):
                continue
            c = candidate
            lines.append(f"| {batch['symbol']} / {batch['strategy']} | {c['family']} | `{c['model']}` | "
                f"{c['validation']['multiclass_brier']:.6f} / {c['class_frequency_baseline']['multiclass_brier']:.6f} | "
                f"{c['validation']['target_calibration_error']:.6f} | "
                f"{c['sample_counts']['calibration']} / {c['sample_counts']['validation']} |")
    lines += ['', '## Exact evidence and failed checks', '',
              ('Input intervals below are stored candle timestamps. Partition intervals are candidate decision timestamps; '
              'the trainer purges overlapping outcome windows. Test timestamps identify the sealed historical partition, '
              'which does not replace a new prospective final period.'), '']
    for batch in report['batches']:
        lines += [f"### {batch['symbol']} / {batch['strategy']}: {batch['state']}", '',
                  f"Durable run: `{batch['run']}`.", '',
                  'Cost assumptions: ' + '; '.join(f'{k}={v}' for k, v in batch['plan']['costs'].items()) + '.', '',
                  f"Cost provenance/limitations: {batch['plan']['cost_evidence']}", '']
        if batch.get('failure'):
            lines += [(f"Batch failed: `{json.dumps(batch['failure'], sort_keys=True)}`. "
                      'No automatic retry or successful evaluation is inferred.'), '']
        for c in batch['candidates']:
            if not c.get('model'):
                lines += [f"- {c['family']}: FAILED — {c.get('reason') or c.get('error_type') or 'No completed evidence'}."]
                continue
            screen = c['validation_screen']
            metrics = screen['metrics']
            prerequisites = []
            if c['sample_counts']['calibration'] < report['policy']['minimum_calibration_samples']:
                prerequisites.append('CALIBRATION_SAMPLE_COUNT')
            if len(c['walk_forward']) != report['policy']['walk_forward_folds'] or any(
                    f['status'] != 'EVALUATED' for f in c['walk_forward']):
                prerequisites.append('WALK_FORWARD_VERIFIED')
            lines += [(f"- `{c['model']}`: artifact SHA256 `{c['artifact_sha256']}`; "
                      f"dataset/configuration SHA256 `{c['dataset_sha256']}`."),
                      f"  Input: `{json.dumps(c['input_candles'], sort_keys=True)}`.",
                      f"  Partitions: `{json.dumps(c['partitions'], sort_keys=True)}`.",
                      (f"  Coverage: {c['coverage']['session_coverage']:.8f}; usable days: {c['coverage']['usable_days']}. "
                      f"Current code matches: {c['strategy_code_matches_current']}; policy matches: {c['policy_matches_current']}."),
                      (f"  Validation trades: {metrics['trades']}; net return: {metrics['net_return']}; "
                      f"drawdown: {metrics['max_drawdown']}; profit factor: {metrics['profit_factor']}; "
                      f"expectancy: {metrics['expectancy']}. Doubled-cost trades: {screen['stressed_metrics']['trades']}."),
                      '  Failed validation economics/calibration checks: ' + ', '.join(c['failed_validation_checks']) + '.',
                      '  Additional recorded prerequisite failures: ' + (', '.join(prerequisites) or 'none in these two checks') + '.',
                      '  Walk-forward states: ' + ', '.join(fold['status'] for fold in c['walk_forward']) + '.',
                      f"  Validation target-probability histogram (bins [0,.1) through [.9,1]): `{c['prediction_reference_validation_only']}`.", '']
        lines += ['']
    p = report['policy']
    lines += ['## Qualification criteria and future-test status', '',
              (f"Policy `{p['version']}` / SHA256 `{p['sha256']}` remains unchanged: "
              '180 history/usable days, 99% session completeness, three pre-test walk-forward folds, '
              '200 calibration samples, 30-day partitions, 100 trades and 20 active days per partition, '
              'positive net return/expectancy, profit factor at least 1.2, drawdown at most 8%, '
              'target calibration error at most .05, Brier better than the training-frequency baseline, '
              'positive block-bootstrap lower bound and positive doubled-cost activity/returns.'), '',
              ('Zero-trade return and drawdown equal zero because there was no exposure. Profit factor, win rate, '
              'entry/exit statistics and expectancy are undefined; they are not profitable or safe performance evidence. '
              'The no-trade return baseline is zero. Some models improve Brier alone, but that does not qualify them.'), '',
              ('The observed validation probability histograms explain abstention: none of the completed models '
              'reaches .80. Sparse mean-reversion/volatility hypotheses fail sample requirements before fitting. '
              'Changing thresholds to obtain activity would change the question, not validate these models.'), '',
              ('No passing candidate, reservation, final-test timestamp, final-test artifact or final-test score exists. '
              'A qualifying frozen candidate would require a disjoint genuinely future observation period of at least '
              '45 days, plus the full 12 five-minute-bar outcome horizon. That clock has not started. '
              'Future evaluation runs once without refitting, and failure consumes the attempt.'), '',
              ('Independent executable fee/slippage/financing evidence, regime/portfolio review, explicit PAPER approval '
              'and a formal elapsed paper trial remain outstanding. OANDA practice requires the additional broker '
              'acceptance sequence. Real-money execution remains unsupported.'), '',
              ('The failed BTC batch registered logistic artifact `candidate-logistic-e2979ef54ebcefd8` before its '
              'native child exited -11. Preserve it as incomplete evidence; no completed base/stress batch result '
              'or qualification is inferred. The native root cause is unresolved. Isolated crash tracing is added '
              'for future research children; it does not repair or retry that past process.'), '',
              '## Reproduction', '',
              ('The immutable full JSON is in the ignored research volume at '
              '`data/reports/activation-corrected-validation-completed-20261015.json`. '
              'It contains exact run IDs, plans, costs, hashes, sample counts, partitions, walk-forward metrics and failed checks. '
              'The declaration was persisted before fitting. The nine campaign schedules were disabled after all jobs '
              'were claimed to prevent unintended annual repeats; the original twelve weekly schedules are unchanged.'), '',
              '```powershell',
              'docker compose exec backend python -m app.cli research-campaign-report activation-corrected-20261015-v1 --output data/reports/NEW-UNIQUE.json',
              '.venv/Scripts/python.exe scripts/render_qualification_report.py data/reports/activation-corrected-validation-completed-20261015.json --output docs/FINAL_MODEL_QUALIFICATION_REPORT.md',
              '```', '',
              ('Rendering does not evaluate markets or modify model state. New experiments must preserve the old '
              'attempts, use predeclared plans and keep final observations separate. No test or policy gate was weakened.'), '']
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.write_text(render(json.loads(args.source.read_text(encoding='utf-8'))), encoding='utf-8')
