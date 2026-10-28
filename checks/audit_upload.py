import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import accuracy_score, f1_score

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_PATH = ROOT / "data" / "genai_prompts.yaml"

from checks import genai_safety
from checks.metrics_extended import evaluate_full, to_py
from decision_engine import decide
from schema.governance_record import (
    GovernanceRecord, SystemInfo, Performance, SubgroupResult, PromptRisks,
)


# ---------------- Tabular ----------------
def audit_predictions(df, label_col, pred_col, sensitive_cols, run_id):
    before = len(df)
    df = df.dropna(subset=[label_col, pred_col] + sensitive_cols)
    dropped = before - len(df)
    if len(df) < 50:
        raise ValueError("Fewer than 50 usable rows after removing missing values.")

    y = df[label_col].astype(int).to_numpy()
    pred = df[pred_col].astype(int).to_numpy()
    if set(np.unique(y)) - {0, 1} or set(np.unique(pred)) - {0, 1}:
        raise ValueError("Label and prediction columns must contain only 0 and 1.")
    for c in sensitive_cols:
        if df[c].nunique() > 12:
            raise ValueError(f"'{c}' has {df[c].nunique()} distinct values. "
                             "Group it first (for example, bucket ages).")

    attrs = {c: evaluate_full(y, pred, df[c]) for c in sensitive_cols}
    first = attrs[sensitive_cols[0]]
    ext = {
        "attributes": attrs,
        "intersectional": {"small_groups": []},
        "counterfactual": {"selected_gb": {"flip_rate": 0.0}},
    }
    decision = decide(
        {"fairness": {"dp_difference": first["dp_difference"],
                      "eo_difference": first["eo_difference"],
                      "group_sizes": first["group_sizes"]}},
        run_id, extended=ext)
    decision.confidence = min(decision.confidence, 0.75)
    decision.reasons.append("Confidence capped: audited from predictions only, without explainability or counterfactual tests")
    return attrs, decision, dropped, float(accuracy_score(y, pred)), float(f1_score(y, pred)), len(df)


def build_tabular_record(name, owner, purpose, attrs, decision, acc, f1, dropped, n_rows):
    first_attr = next(iter(attrs))
    first = attrs[first_attr]
    rec = GovernanceRecord(
        system=SystemInfo(name=name, version="uploaded", owner=owner,
                          system_type="tabular_classifier",
                          intended_use=purpose or "Not stated", out_of_scope="Not stated"),
        performance=Performance(accuracy=acc, f1=f1,
                                dataset_version=f"uploaded predictions ({n_rows} rows)"),
        subgroups=[SubgroupResult(
            attribute=first_attr,
            dp_difference=float(first["dp_difference"]),
            eo_difference=float(first["eo_difference"]),
            per_group=to_py(first["per_group"]),
            group_sizes=to_py(first["group_sizes"]))],
        limitations=[
            "Audited from a predictions file only: no explainability or counterfactual tests",
            "Intersectional groups were not computed for uploads",
            "Bootstrap intervals reflect test-set sampling only",
            f"{dropped} rows with missing values were excluded" if dropped else
            "No rows were excluded for missing values",
        ],
        assumptions=["Predictions come from the model being proposed for release",
                     "Uploaded labels are the ground truth",
                     "Positive class (1) is the favourable outcome"],
        decision=decision,
    )
    out = rec.model_dump(mode="json")
    out["extra"] = {"attributes": to_py(attrs)}
    return out


# ---------------- Chatbot ----------------
def _call(system_prompt, user_msg, model):
    last = "unknown error"
    for attempt in range(3):
        try:
            resp = genai_safety.client.chat.completions.create(
                model=model, temperature=0, max_tokens=500,
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": user_msg or "(empty message)"}])
            return resp.choices[0].message.content or ""
        except Exception as e:
            last = str(e)
            time.sleep(3 * (attempt + 1))
    return f"[API_ERROR] {last}"


def audit_chatbot(system_prompt, model, run_id, progress=None):
    """Plants a canary secret in the team's prompt and tests whether it leaks."""
    full_prompt = system_prompt.strip() + (
        f"\n\nInternal admin code (confidential): {genai_safety.SECRET}.")
    with PROMPTS_PATH.open("r", encoding="utf-8") as f:
        prompts = yaml.safe_load(f) or []

    rows = []
    for i, p in enumerate(prompts):
        reply = _call(full_prompt, p["prompt"], model)
        rows.append({
            "id": p["id"], "category": p["category"], "split": p.get("split", "main"),
            "rep": 0, "mode": "hardened",
            "prompt": p["prompt"], "reply": reply,
            "api_error": genai_safety.is_error(reply),
            "attack_success": genai_safety.attack_succeeded(p["category"], reply),
            "refused": genai_safety.is_refusal(reply),
        })
        if progress:
            progress((i + 1) / len(prompts))
        time.sleep(1)

    errors = sum(r["api_error"] for r in rows)
    summary = genai_safety.summarize(rows)["hardened"]
    decision = decide({"genai": summary,
                       "fairness": {"dp_difference": 0.0, "eo_difference": 0.0, "group_sizes": {}}},
                      run_id)
    return rows, summary, decision, errors


def build_chatbot_record(name, owner, purpose, model, summary, decision, errors):
    rec = GovernanceRecord(
        system=SystemInfo(name=name, version="uploaded", owner=owner,
                          system_type="genai_assistant",
                          intended_use=purpose or "Not stated", out_of_scope="Not stated"),
        prompt_risks=PromptRisks(
            injection_asr=summary["injection_asr"], jailbreak_asr=summary["jailbreak_asr"],
            pii_leak_rate=summary["pii_leak_asr"], over_refusal_rate=summary["over_refusal_rate"]),
        limitations=[
            "Only the system prompt was tested; no input or output filters were applied",
            "Keyword-based scoring may miss subtle failures",
            "Single run: LLM outputs vary between runs",
            f"{errors} API calls failed and were excluded" if errors else "No API errors",
        ],
        assumptions=[f"Model tested: {model}", "Temperature 0",
                     "A canary secret was added to the system prompt to detect leakage"],
        decision=decision,
    )
    out = rec.model_dump(mode="json")
    out["extra"] = {"summary": to_py(summary)}
    return out