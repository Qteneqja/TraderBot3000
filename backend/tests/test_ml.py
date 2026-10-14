import numpy as np

from app.indicators.features import compute, frame
from app.machine_learning.training import barrier_labels, chronological_partitions, scores, train
from app.market_data.fixtures import demo_candles


def test_purged_split_has_no_label_overlap():
    parts = chronological_partitions(1000, 12)
    for before, after in zip(parts, parts[1:]):
        assert before[-1] + 12 < after[0]


def test_final_incomplete_horizon_unlabeled():
    labels = barrier_labels(compute(frame(demo_candles(count=100))), horizon=12)
    assert np.isnan(labels[-12:]).all()
    assert set(labels[np.isfinite(labels)]) <= {0, 1, 2}


def test_calibration_scores_are_measured():
    report = scores(np.array([0, 1, 2]), np.array([[0.8, 0.1, 0.1], [0.1, 0.8, 0.1], [0.1, 0.1, 0.8]]))
    assert abs(report["multiclass_brier"] - 0.06) < 1e-10
    assert sum(b["count"] for b in report["reliability"]) == 3


def test_training_creates_experimental_artifact_only(tmp_path):
    report = train(demo_candles(count=360), tmp_path)
    assert report["status"] == "EXPERIMENTAL"
    assert report["execution_validated"] is False
    assert report["source"] == "fixture"
    assert (tmp_path / f"{report['version']}.joblib").exists()
    assert report["partitions"]["calibration"][1] < report["partitions"]["test"][0]
