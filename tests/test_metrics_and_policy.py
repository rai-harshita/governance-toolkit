import numpy as np

from checks.metrics_extended import evaluate_full
from checks.policy_map import match


def test_equal_selection_rates_give_zero_gap():
    s = np.array(["A", "B"] * 100)
    pred = np.tile([1, 1, 0, 0], 50)          # each group is selected 50% of the time
    r = evaluate_full(pred, pred, s)
    assert r["dp_difference"] == 0 and r["disparate_impact_ratio"] == 1.0
    assert r["small_groups"] == []


def test_fully_biased_model_has_maximum_gap():
    s = np.array(["A", "B"] * 100)
    y = np.tile([1, 1, 0, 0], 50)
    pred = (s == "A").astype(int)             # only group A is ever selected
    r = evaluate_full(y, pred, s)
    assert r["dp_difference"] > 0.9 and r["disparate_impact_ratio"] < 0.1


def test_confidence_interval_contains_the_estimate():
    # Group A is selected about 60% of the time, group B about 40%: a clear gap of 0.2
    rng = np.random.default_rng(0)
    s = np.array(["A", "B"] * 300)
    y = rng.integers(0, 2, 600)
    pred = np.where(s == "A", rng.random(600) < 0.6, rng.random(600) < 0.4).astype(int)
    r = evaluate_full(y, pred, s)
    lo, hi = r["dp_ci"]
    assert r["dp_difference"] > 0.1
    assert lo <= r["dp_difference"] <= hi
    assert hi - lo < 0.2          # the interval is informative, not absurdly wide


def test_small_groups_are_flagged():
    s = np.array(["A"] * 190 + ["B"] * 10)
    y = np.tile([1, 0], 100)
    r = evaluate_full(y, y, s)
    assert r["small_groups"] == ["B"]


def test_policy_map_links_findings_to_clauses():
    hits = match("age_group: disparate impact ratio 0.11 below 0.5")
    assert hits and "NIST" not in hits[0]["check"] and hits[0]["nist"].startswith("MEASURE")


def test_policy_map_returns_nothing_for_unrelated_text():
    assert match("all good") == []