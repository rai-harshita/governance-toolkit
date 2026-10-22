import numpy as np
from fairlearn.datasets import fetch_adult
from fairlearn.metrics import (
    MetricFrame, selection_rate, true_positive_rate,
    demographic_parity_difference, equalized_odds_difference,
)
from sklearn.compose import make_column_transformer, make_column_selector
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEED = 42


def load():
    data = fetch_adult(as_frame=True)
    X = data.data
    y = data.target
    # Adult labels can be strings like ">50K" or 0/1 depending on version
    if y.dtype == object or str(y.dtype) == "category":
        y = y.astype(str).str.contains(">50K").astype(int)
    else:
        y = y.astype(int)
    return train_test_split(X, y, test_size=0.3, random_state=SEED, stratify=y)


def make_model(clf):
    pre = make_column_transformer(
        (StandardScaler(), make_column_selector(dtype_include="number")),
        (OneHotEncoder(handle_unknown="ignore", sparse_output=False),
         make_column_selector(dtype_exclude="number")),
    )
    return make_pipeline(pre, clf)


def evaluate(y_true, y_pred, sensitive):
    mf = MetricFrame(
        metrics={"selection_rate": selection_rate, "tpr": true_positive_rate},
        y_true=y_true, y_pred=y_pred, sensitive_features=sensitive,
    )
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "f1": f1_score(y_true, y_pred),
        "dp_difference": demographic_parity_difference(y_true, y_pred, sensitive_features=sensitive),
        "eo_difference": equalized_odds_difference(y_true, y_pred, sensitive_features=sensitive),
        "per_group": mf.by_group.to_dict("index"),
        "group_sizes": sensitive.value_counts().to_dict(),
    }


def run(attr="sex"):
    Xtr, Xte, ytr, yte = load()
    print("Label values:", [int(v) for v in sorted(ytr.unique())],
          "| positive rate:", round(float(ytr.mean()), 3))
    results = {}
    for name, clf in [
        ("baseline_logreg", LogisticRegression(max_iter=1000)),
        ("selected_gb", HistGradientBoostingClassifier(random_state=SEED)),
    ]:
        model = make_model(clf).fit(Xtr, ytr)
        pred = model.predict(Xte)
        results[name] = evaluate(yte, pred, Xte[attr])
    return results


def run_mitigation(attr="sex", constraint="demographic_parity"):
    from fairlearn.postprocessing import ThresholdOptimizer

    Xtr, Xte, ytr, yte = load()
    base = make_model(HistGradientBoostingClassifier(random_state=SEED)).fit(Xtr, ytr)

    mitigated = ThresholdOptimizer(
        estimator=base,
        constraints=constraint,
        objective="accuracy_score",
        predict_method="predict_proba",
        prefit=True,
    )
    mitigated.fit(Xtr, ytr, sensitive_features=Xtr[attr])

    pred_before = base.predict(Xte)
    pred_after = mitigated.predict(Xte, sensitive_features=Xte[attr], random_state=SEED)

    return {
        "before": evaluate(yte, pred_before, Xte[attr]),
        "after": evaluate(yte, pred_after, Xte[attr]),
    }


def show(name, r):
    print(f"\n{name}")
    for k in ["accuracy", "f1", "dp_difference", "eo_difference"]:
        print(f"  {k}: {r[k]:.3f}")
    print("  group sizes:", r["group_sizes"])
    for g, m in r["per_group"].items():
        print(f"  {g}: selection_rate={m['selection_rate']:.3f}, tpr={m['tpr']:.3f}")


if __name__ == "__main__":
    results = run("sex")
    for name, r in results.items():
        show(name, r)

    mit = run_mitigation("sex")
    show("selected_gb BEFORE mitigation", mit["before"])
    show("selected_gb AFTER mitigation (demographic parity)", mit["after"])

    acc_cost = mit["before"]["accuracy"] - mit["after"]["accuracy"]
    gap_drop = mit["before"]["dp_difference"] - mit["after"]["dp_difference"]
    print(f"\nTRADE-OFF: DP gap reduced by {gap_drop:.3f}, accuracy cost {acc_cost:.3f}")
    