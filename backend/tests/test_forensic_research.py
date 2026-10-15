"""Explicit fixtures verify diagnostic parity; they are not model qualification."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from app.backtesting.simulator import FillAssumptions
from app.machine_learning.candidate_training import CANDIDATE_FEATURES, dataset, prediction_features
from app.market_data.fixtures import demo_candles
from app.research.costs import disclosed_terms, spread_summary
from app.research.forensics import (
    block_interval,
    outcome_report,
    probability_report,
    scan_outcomes,
    session_name,
)
from app.research.hypotheses import confirmation_masks
from app.research.lab import implementation, write_json
from app.schemas.domain import Quote
from app.strategies.registry import evaluate

D = Decimal


def test_experiment_tampering_and_repeated_claims_fail_before_database_access(tmp_path):
    from app.machine_learning.policy import digest
    from app.research.hypotheses import run as hypotheses_run
    from app.research.lab import run as forensic_run
    from app.research.reproduce import run as reproduce_run

    folder = tmp_path/'tampered'
    folder.mkdir()
    write_json(folder/'plan.json', {})
    for run in (forensic_run, hypotheses_run, reproduce_run):
        with pytest.raises(ValueError):
            run(None, folder)
        assert not (folder/'claimed.json').exists()
    plan = {'code': implementation(), 'authority': 'DIAGNOSTIC_ONLY'}
    claimed = tmp_path/digest(plan)
    claimed.mkdir()
    write_json(claimed/'plan.json', plan)
    write_json(claimed/'claimed.json', {'automatic_retry': False})
    with pytest.raises(FileExistsError):
        forensic_run(None, claimed)
    with pytest.raises(FileExistsError):
        write_json(claimed/'plan.json', {})


def test_confirmation_filters_cannot_read_future_or_uncompleted_hours():
    candles = demo_candles(count=700)
    samples = pd.DataFrame({'time': [c.time+timedelta(seconds=300) for c in candles[400:500]],
                            'direction_name': ['LONG', 'SHORT']*50})
    before = confirmation_masks(candles[:500], samples, D('.00001'))
    after = confirmation_masks(candles, samples, D('.00001'))
    for name in before:
        pd.testing.assert_series_equal(before[name], after[name])
    # An extreme future price must not change any already completed decision.
    changed = candles[:500]+[c.model_copy(update={'open': c.open*2, 'high': c.high*2,
        'low': c.low*2, 'close': c.close*2}) for c in candles[500:]]
    extreme = confirmation_masks(changed, samples, D('.00001'))
    for name in before:
        pd.testing.assert_series_equal(before[name], extreme[name])


def test_diagnostic_labels_and_features_match_original_training_and_runtime():
    candles = demo_candles(count=600)
    costs = FillAssumptions(D('.00002'), D('.00001'))
    original, excluded = dataset(candles, D('.00001'), 'trend', costs)
    rows, counts = scan_outcomes(candles, D('.00001'), costs, ['trend'])
    assert not rows.empty
    columns = CANDIDATE_FEATURES + ['candidate_id', 'label', 'label_end', 'net_r', 'time']
    pd.testing.assert_frame_equal(original[columns], rows[columns])
    assert counts['trend'].get('entry_drift_rejections', 0) == excluded['entry_drift']
    first = rows.iloc[0]
    proposal = next(c for c in evaluate(candles, first.time, D('.00001'), ['trend']) if c.id == first.candidate_id)
    next_bar = next(c for c in candles if c.time == first.time)
    quote = Quote(symbol=proposal.symbol, source=proposal.source, time=first.time,
                  bid=next_bar.open-costs.spread/2, ask=next_bar.open+costs.spread/2)
    assert prediction_features(proposal, quote) == {key: first[key] for key in CANDIDATE_FEATURES}
    report = outcome_report(rows, counts)['trend']
    assert report['summary']['candidates'] == len(original)
    assert sum(report['summary']['outcome_counts'].values()) == len(original)


def test_horizon_requires_complete_outcomes_and_future_candles_do_not_change_prefix_labels():
    candles = demo_candles(count=250)
    costs = FillAssumptions(D('.00002'), D('.00001'))
    prefix, _ = scan_outcomes(candles[:180], D('.00001'), costs, ['trend'], horizon=6)
    all_rows, _ = scan_outcomes(candles, D('.00001'), costs, ['trend'], horizon=6)
    safe = all_rows[all_rows.label_end <= candles[179].time+timedelta(seconds=300)]
    pd.testing.assert_frame_equal(prefix.reset_index(drop=True), safe.reset_index(drop=True))
    with pytest.raises(ValueError):
        scan_outcomes(candles, D('.00001'), costs, ['trend'], horizon=1)


def test_probability_thresholds_are_counts_and_have_no_authority():
    p = np.array([[.1, .8, .1], [.2, .6, .2], [.3, .4, .3]])
    report = probability_report(np.array([1, 0, 2]), p)
    assert report['target_threshold_counts_diagnostic_only'] == {'0.5': 2, '0.6': 2, '0.7': 1, '0.8': 1}
    assert report['actual_class_counts'] == [1, 1, 1]
    assert report['execution_authority'] is False
    with pytest.raises(ValueError):
        probability_report(np.array([1]), [[0, 2, 0]])


def test_sessions_use_declared_local_clocks_and_empty_evidence_stays_unknown():
    assert session_name(datetime(2026, 7, 1, 13, tzinfo=timezone.utc)) == 'OVERLAP'
    assert session_name(datetime(2026, 7, 1, 8, tzinfo=timezone.utc)) == 'LONDON'
    assert session_name(datetime(2026, 7, 1, 0, tzinfo=timezone.utc)) == 'OTHER'
    assert block_interval(pd.DataFrame()) is None


def test_missing_cost_terms_are_unknown_and_observed_financing_is_not_historical_proof():
    missing = disclosed_terms({})
    assert missing['commission']['classification'] == missing['financing']['classification'] == 'UNKNOWN'
    observed = disclosed_terms({'commission': {'commission': '0', 'unitsTraded': '1000000', 'minimumCommission': '0'},
        'financing': {'longRate': '-.04', 'shortRate': '.02', 'financingDaysOfWeek': [
            {'dayOfWeek': 'WEDNESDAY', 'daysCharged': 3}]}})
    assert observed['commission']['terms']['commission'] == '0'
    assert observed['financing']['classification'] == 'OBSERVED'
    assert observed['financing']['historical_applicability'] == 'UNKNOWN'
    with pytest.raises(ValueError):
        disclosed_terms({'commission': {'commission': '0', 'unitsTraded': '0', 'minimumCommission': '0'}})


def test_spread_statistics_use_observed_decimal_close_components():
    candles = demo_candles(count=2)
    rows = [c.model_copy(update={'provenance': {'bid': {'c': '1.1'}, 'ask': {'c': ask}}})
            for c, ask in zip(candles, ['1.10002', '1.10004'], strict=True)]
    observed = spread_summary(rows)
    assert observed['bid_ask_close_samples'] == 2
    assert D(observed['quantiles_nearest_rank']['0.5']) == D('.00002')
    assert D(observed['quantiles_nearest_rank']['1']) == D('.00004')
    assert spread_summary(candles)['quantiles_nearest_rank'] is None
