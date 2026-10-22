import numpy as np
import pandas as pd
import shap
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_selection import mutual_info_classif
from sklearn.inspection import permutation_importance

from checks.fairness import load, make_model, SEED


def feature_names(model):
    return list(model[:-1].get_feature_names_out())


def shap_importance(model, X):
    """Mean |SHAP| per transformed feature."""
    Xt = model[:-1].transform(X)
    clf = model[-1]
    f = lambda data: clf.predict_proba(data)[:, 1]
    background = Xt[:100]
    explainer = shap.Explainer(f, background)
    values = explainer(Xt).values
    return np.abs(values).mean(axis=0)


def top_k(importances, names, k=10):
    order = np.argsort(importances)[::-1][:k]
    return [names[i] for i in order]


def run():
    Xtr, Xte, ytr, yte = load()
    model = make_model(HistGradientBoostingClassifier(random_state=SEED)).fit(Xtr, ytr)
    names = feature_names(model)

    sample = Xte.sample(300, random_state=SEED)

    # 1) Global SHAP
    shap_imp = shap_importance(model, sample)
    shap_top = top_k(shap_imp, names)

    # 2) Baseline: permutation importance (on original columns)
    perm = permutation_importance(
        model, Xte.sample(1000, random_state=SEED), yte.loc[Xte.sample(1000, random_state=SEED).index],
        n_repeats=3, random_state=SEED,
    )
    perm_top = list(pd.Series(perm.importances_mean, index=Xte.columns)
                    .sort_values(ascending=False).index[:10])

    # 3) Stability: add small noise to numeric columns, recompute SHAP, rank-correlate
    noisy = sample.copy()
    rng = np.random.default_rng(SEED)
    for col in noisy.select_dtypes("number").columns:
        noisy[col] = noisy[col] + rng.normal(0, 0.05 * noisy[col].std(), len(noisy))
    shap_noisy = shap_importance(model, noisy)
    stability = float(spearmanr(shap_imp, shap_noisy)[0])

    # 4) Proxy detection: how much does each original feature reveal sex?
    X_num = Xte.copy()
    for col in X_num.select_dtypes(exclude="number").columns:
        X_num[col] = X_num[col].astype("category").cat.codes
    X_num = X_num.drop(columns=["sex"])
    sex = (Xte["sex"] == "Female").astype(int)
    mi = pd.Series(mutual_info_classif(X_num, sex, random_state=SEED), index=X_num.columns)
    flagged = list(mi[mi > 0.05].sort_values(ascending=False).index)

    return {
        "method": "SHAP (permutation explainer)",
        "top_features": shap_top,
        "permutation_top": perm_top,
        "stability": round(stability, 3),
        "flagged_proxies": flagged,
        "proxy_scores": mi.sort_values(ascending=False).round(3).to_dict(),
    }


if __name__ == "__main__":
    r = run()
    print("SHAP top features:", r["top_features"])
    print("Permutation top features (baseline):", r["permutation_top"])
    print("Stability (Spearman):", r["stability"])
    print("Flagged proxies for sex:", r["flagged_proxies"])
    print("Proxy scores:", r["proxy_scores"])