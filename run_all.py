import json
import sys
from datetime import datetime
from pathlib import Path

from checks import fairness, explain, genai_safety, metrics_extended   # NEW: metrics_extended
from decision_engine import decide
from schema.governance_record import (
    GovernanceRecord, SystemInfo, Performance, SubgroupResult,
    Explanation, PromptRisks,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
EVIDENCE_DIR = ROOT / "evidence"
EVIDENCE_DIR.mkdir(exist_ok=True)


def to_py(obj):
    """Convert numpy types so json.dump works."""
    if hasattr(obj, "item"):
        return obj.item()
    if isinstance(obj, dict):
        return {str(k): to_py(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_py(v) for v in obj]
    return obj


def main():
    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    print("Run ID:", run_id)

    # ---------- System 1: tabular classifier ----------
    print("Running fairness checks...")
    fair = fairness.run("sex")["selected_gb"]
    mit = fairness.run_mitigation("sex")

    print("Running explainability checks...")
    expl = explain.run()

    print("Running extended fairness metrics...")          # NEW
    ext = to_py(metrics_extended.run())                    # NEW

    tab_results = {
        "fairness": {
            "dp_difference": fair["dp_difference"],
            "eo_difference": fair["eo_difference"],
            "group_sizes": fair["group_sizes"],
        },
        "explanation": {
            "stability": expl["stability"],
            "proxy_scores": expl["proxy_scores"],
        },
    }
    tab_decision = decide(to_py(tab_results), run_id, extended=ext)   # NEW: extended=ext

    tab_record = GovernanceRecord(
        system=SystemInfo(
            name="Adult Income Classifier", version="1.0", owner="Harshita",
            system_type="tabular_classifier",
            intended_use="Educational demo of income prediction",
            out_of_scope="Real hiring or lending decisions",
        ),
        performance=Performance(
            accuracy=float(fair["accuracy"]), f1=float(fair["f1"]),
            dataset_version="UCI Adult (fairlearn fetch_adult)",
        ),
        subgroups=[SubgroupResult(
            attribute="sex",
            dp_difference=float(fair["dp_difference"]),
            eo_difference=float(fair["eo_difference"]),
            per_group=to_py(fair["per_group"]),
            group_sizes=to_py(fair["group_sizes"]),
        )],
        explanation=Explanation(
            method=expl["method"], top_features=expl["top_features"],
            stability=float(expl["stability"]), flagged_proxies=expl["flagged_proxies"],
        ),
        limitations=[
            "Trained on 1994 census data",
            "Stability tested only with small numeric noise on 300 rows",
            "Only sex was audited in the basic check; see extended metrics for race, age and intersections",
            "Bootstrap intervals reflect test-set sampling only, not retraining variance",   # NEW
            "Age gap may partly reflect legitimate career-stage differences",                # NEW
        ],
        assumptions=["Test split is 30%, seed 42", "Positive class is income > 50K"],
        decision=tab_decision,
    )

    # ---------- System 2: GenAI helpdesk bot ----------
    print("Running GenAI safety checks (this makes API calls)...")
    rows = genai_safety.run()
    summary = genai_safety.summarize(rows)
    hardened = summary["hardened"]

    gen_decision = decide({"genai": hardened, "fairness": {
        "dp_difference": 0.0, "eo_difference": 0.0, "group_sizes": {}}}, run_id)

    gen_record = GovernanceRecord(
        system=SystemInfo(
            name="College Helpdesk Bot", version="1.0", owner="Harshita",
            system_type="genai_assistant",
            intended_use="Answer admissions, fee and hostel questions",
            out_of_scope="Sharing student data or internal codes",
        ),
        prompt_risks=PromptRisks(
            injection_asr=hardened["injection_asr"],
            jailbreak_asr=hardened["jailbreak_asr"],
            pii_leak_rate=hardened["pii_leak_asr"],
            over_refusal_rate=hardened["over_refusal_rate"],
        ),
        limitations=[
            "Keyword-based scoring may miss subtle failures",
            "Small prompt suite (24 prompts)",
            "Input blocklist overlaps with test prompts",
        ],
        assumptions=[f"LLM used: {genai_safety.MODEL}", "Temperature 0"],
        decision=gen_decision,
    )

    # ---------- Save evidence ----------
    evidence = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "records": [tab_record.model_dump(mode="json"), gen_record.model_dump(mode="json")],
        "mitigation": to_py({"before": mit["before"], "after": mit["after"]}),
        "extended": ext,                                   # NEW
        "genai_summary": summary,
        "genai_rows": rows,
        "proxy_scores": to_py(expl["proxy_scores"]),
        "permutation_top": expl["permutation_top"],
    }
    out = EVIDENCE_DIR / f"{run_id}.json"
    out.write_text(json.dumps(to_py(evidence), indent=2, ensure_ascii=False), encoding="utf-8")
    (EVIDENCE_DIR / "latest.json").write_text(out.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"\nSaved {out}")
    for r in (tab_record, gen_record):
        d = r.decision
        print(f"{r.system.name}: {d.status} (confidence {d.confidence})")
        for reason in d.reasons:
            print("   -", reason)


if __name__ == "__main__":
    main()