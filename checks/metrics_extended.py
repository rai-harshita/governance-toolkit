import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
from fairlearn.metrics import (
    MetricFrame, selection_rate, true_positive_rate, false_positive_rate,
    demographic_parity_difference, demographic_parity_ratio, equalized_odds_difference,
)
from fairlearn.postprocessing import ThresholdOptimizer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score

from checks.fairness import load, make_model, SEED

N_BOOT = 200
MIN_GROUP = 100

METRICS = {
    "selection_rate": selection_rate,
    "tpr": true_positive_rate,
    "fpr": false_positive_rate,
    "precision": lambda y, p: precision_score(y, p, zero_division=0),
    "accuracy": accuracy_score,
}


def bootstrap_ci(stat_fn, y, pred, s, n_boot=N_BOOT):
    rng = np.random.default_rng(SEED)
    n = len(y)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        try:
            vals.append(stat_fn(y[idx], pred[idx], s[idx]))
        except ValueError:
            continue
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return [round(float(lo), 4), round(float(hi), 4)]


def evaluate_full(y, pred, s):
    """Full fairness profile for one model and one sensitive attribute."""
    y = np.asarray(y)
    pred = np.asarray(pred)
    s = np.asarray(s).astype(str)

    mf = MetricFrame(metrics=METRICS, y_true=y, y_pred=pred, sensitive_features=s)
    gaps = mf.difference()
    sizes = pd.Series(s).value_counts()

    dp = demographic_parity_difference(y, pred, sensitive_features=s)
    dp_fn = lambda yy, pp, ss: demographic_parity_difference(yy, pp, sensitive_features=ss)
    acc_fn = lambda yy, pp, ss: accuracy_score(yy, pp)

    return {
        "accuracy": accuracy_score(y, pred),
        "f1": f1_score(y, pred),
        "dp_difference": dp,
        "dp_ci": bootstrap_ci(dp_fn, y, pred, s),
        "accuracy_ci": bootstrap_ci(acc_fn, y, pred, s),
        "disparate_impact_ratio": demographic_parity_ratio(y, pred, sensitive_features=s),
        "eo_difference": equalized_odds_difference(y, pred, sensitive_features=s),
        "equal_opportunity_gap": gaps["tpr"],
        "fpr_gap": gaps["fpr"],
        "accuracy_gap": gaps["accuracy"],
        "per_group": mf.by_group.round(4).to_dict("index"),
        "group_sizes": sizes.to_dict(),
        "small_groups": [g for g, n in sizes.items() if n < MIN_GROUP],
    }


def counterfactual_sex_flip(model, X):
    """Flip only `sex` and measure how much the model output changes."""
    cf = X.copy()
    cf["sex"] = cf["sex"].astype(str).map({"Male": "Female", "Female": "Male"})
    p0, p1 = model.predict_proba(X)[:, 1], model.predict_proba(cf)[:, 1]
    return {
        "flip_rate": float(np.mean((p0 >= 0.5) != (p1 >= 0.5))),
        "mean_abs_prob_change": float(np.mean(np.abs(p0 - p1))),
        "max_abs_prob_change": float(np.max(np.abs(p0 - p1))),
    }


def run():
    Xtr, Xte, ytr, yte = load()
    Xte = Xte.copy()
    Xte["age_group"] = pd.cut(Xte["age"], [0, 29, 49, 120],
                              labels=["<30", "30-49", "50+"]).astype(str)

    # ---- Models ----
    lr = make_model(LogisticRegression(max_iter=1000)).fit(Xtr, ytr)
    gb = make_model(HistGradientBoostingClassifier(random_state=SEED)).fit(Xtr, ytr)
    gb_nosex = make_model(HistGradientBoostingClassifier(random_state=SEED)).fit(
        Xtr.drop(columns=["sex"]), ytr)

    to_dp = ThresholdOptimizer(estimator=gb, constraints="demographic_parity",
                               objective="accuracy_score", predict_method="predict_proba", prefit=True)
    to_dp.fit(Xtr, ytr, sensitive_features=Xtr["sex"])
    to_eo = ThresholdOptimizer(estimator=gb, constraints="equalized_odds",
                               objective="accuracy_score", predict_method="predict_proba", prefit=True)
    to_eo.fit(Xtr, ytr, sensitive_features=Xtr["sex"])

    feats = [c for c in Xte.columns if c != "age_group"]
    preds = {
        "baseline_logreg": lr.predict(Xte[feats]),
        "selected_gb": gb.predict(Xte[feats]),
        "gb_without_sex": gb_nosex.predict(Xte[feats].drop(columns=["sex"])),
        "gb_mitigated_dp": to_dp.predict(Xte[feats], sensitive_features=Xte["sex"], random_state=SEED),
        "gb_mitigated_eo": to_eo.predict(Xte[feats], sensitive_features=Xte["sex"], random_state=SEED),
    }

    out = {"model_comparison_sex": {}, "attributes": {}, "intersectional": {}, "counterfactual": {}}

    # 1) All model variants measured on sex
    for name, pred in preds.items():
        out["model_comparison_sex"][name] = evaluate_full(yte, pred, Xte["sex"])

    # 2) Selected model across several sensitive attributes
    for attr in ["sex", "race", "age_group"]:
        out["attributes"][attr] = evaluate_full(yte, preds["selected_gb"], Xte[attr])

    # 3) Intersectional: sex x race
    inter = Xte["sex"].astype(str) + " / " + Xte["race"].astype(str)
    out["intersectional"] = evaluate_full(yte, preds["selected_gb"], inter)

    # 4) Counterfactual sex flip (selected model and baseline)
    out["counterfactual"]["selected_gb"] = counterfactual_sex_flip(gb, Xte[feats])
    out["counterfactual"]["baseline_logreg"] = counterfactual_sex_flip(lr, Xte[feats])

    return out


def to_py(o):
    if hasattr(o, "item"):
        return o.item()
    if isinstance(o, dict):
        return {str(k): to_py(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_py(v) for v in o]
    return o


if __name__ == "__main__":
    r = run()

    print("\n=== MODEL COMPARISON (attribute: sex) ===")
    print(f"{'model':<18}{'acc':>7}{'DP gap':>8}{'DP 95% CI':>16}{'DI ratio':>10}{'EO gap':>8}{'FPR gap':>9}")
    for name, m in r["model_comparison_sex"].items():
        ci = f"[{m['dp_ci'][0]:.3f},{m['dp_ci'][1]:.3f}]"
        print(f"{name:<18}{m['accuracy']:>7.3f}{m['dp_difference']:>8.3f}{ci:>16}"
              f"{m['disparate_impact_ratio']:>10.3f}{m['eo_difference']:>8.3f}{m['fpr_gap']:>9.3f}")

    print("\n=== SELECTED MODEL ACROSS ATTRIBUTES ===")
    for attr, m in r["attributes"].items():
        print(f"{attr:<10} DP gap {m['dp_difference']:.3f} CI {m['dp_ci']}  "
              f"DI ratio {m['disparate_impact_ratio']:.3f}  small groups: {m['small_groups']}")

    inter = r["intersectional"]
    print("\n=== INTERSECTIONAL (sex x race) ===")
    print(f"DP gap {inter['dp_difference']:.3f}  DI ratio {inter['disparate_impact_ratio']:.3f}  "
          f"small groups: {inter['small_groups']}")
    for g, v in sorted(inter["per_group"].items(), key=lambda kv: kv[1]["selection_rate"]):
        print(f"  {g:<38} n={inter['group_sizes'][g]:<6} selection_rate={v['selection_rate']:.3f}")

    print("\n=== COUNTERFACTUAL (flip sex only) ===")
    for name, c in r["counterfactual"].items():
        print(f"{name:<16} flip rate {c['flip_rate']:.2%}  mean prob change {c['mean_abs_prob_change']:.3f}"
              f"  max {c['max_abs_prob_change']:.3f}")

    evidence_dir = ROOT / "evidence"
    evidence_dir.mkdir(exist_ok=True)
    (evidence_dir / "metrics_extended.json").write_text(
        json.dumps(to_py(r), indent=2), encoding="utf-8")
    print("\nSaved evidence/metrics_extended.json")