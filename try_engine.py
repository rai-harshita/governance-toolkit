from decision_engine import decide

good = {
    "fairness": {"dp_difference": 0.05, "eo_difference": 0.05, "group_sizes": {"M": 500, "F": 400}},
    "explanation": {"stability": 0.95, "proxy_scores": {"relationship": 0.10}},
    "genai": {"injection_asr": 0.0, "jailbreak_asr": 0.0, "pii_leak_asr": 0.0, "over_refusal_rate": 0.05},
}
cases = {
    "PASS": good,
    "CONDITIONAL": {**good, "fairness": {**good["fairness"], "dp_difference": 0.15}},
    "BLOCK": {**good, "fairness": {**good["fairness"], "dp_difference": 0.30}},
    "HUMAN_REVIEW": {**good, "genai": {**good["genai"], "injection_asr": 0.20}},
    "HUMAN_REVIEW (missing data)": {"genai": good["genai"]},
    "HUMAN_REVIEW (tiny subgroup)": {**good, "fairness": {**good["fairness"], "group_sizes": {"M": 500, "F": 20}}},
}
for name, res in cases.items():
    d = decide(res, run_id="demo")
    print(f"{name:<30} -> {d.status:<13} conf={d.confidence}  reasons={d.reasons}")