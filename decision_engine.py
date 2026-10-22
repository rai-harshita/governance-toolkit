import yaml
from schema.governance_record import Decision

with open("configs/rules.yaml", encoding="utf-8") as f:
    RULES = yaml.safe_load(f)


def decide(results: dict, run_id: str, rules: dict = RULES) -> Decision:
    """results may contain: fairness, explanation, genai (each optional).
    Returns a Decision. Severity order: BLOCK > HUMAN_REVIEW > CONDITIONAL > PASS."""
    reasons, actions = [], []
    flags = set()

    fair = results.get("fairness")
    expl = results.get("explanation")
    gen = results.get("genai")

    # ---- Fairness ----
    if fair:
        sizes = fair.get("group_sizes", {})
        if sizes and min(sizes.values()) < rules["min_group_size"]:
            flags.add("HUMAN_REVIEW")
            reasons.append(f"Insufficient data: smallest subgroup has {min(sizes.values())} rows")
            actions.append("Collect more data for the small subgroup or review manually")

        dp = fair["dp_difference"]
        if dp > rules["fairness"]["dp_block"]:
            flags.add("BLOCK")
            reasons.append(f"DP gap {dp:.3f} exceeds block limit {rules['fairness']['dp_block']}")
            actions.append("Apply bias mitigation and re-run the audit")
        elif dp > rules["fairness"]["dp_conditional"]:
            flags.add("CONDITIONAL")
            reasons.append(f"DP gap {dp:.3f} exceeds {rules['fairness']['dp_conditional']}")
            actions.append("Apply threshold mitigation, then re-check")

        eo = fair.get("eo_difference")
        if eo is not None and eo > rules["fairness"]["eo_conditional"]:
            flags.add("CONDITIONAL")
            reasons.append(f"EO gap {eo:.3f} exceeds {rules['fairness']['eo_conditional']}")
            actions.append("Review trade-off: reducing one fairness gap increased another")
    else:
        flags.add("HUMAN_REVIEW")
        reasons.append("Fairness results missing")
        actions.append("Run the fairness check")

    # ---- Explainability ----
    if expl:
        if expl["stability"] < rules["explanation"]["min_stability"]:
            flags.add("CONDITIONAL")
            reasons.append(f"Explanation stability {expl['stability']:.3f} below {rules['explanation']['min_stability']}")
            actions.append("Investigate unstable features")
        high = {k: v for k, v in expl.get("proxy_scores", {}).items()
                if v > rules["explanation"]["max_proxy_score"]}
        if high:
            flags.add("CONDITIONAL")
            reasons.append(f"Strong proxy features for a sensitive attribute: {high}")
            actions.append("Remove or audit proxy features; document the justification")

    # ---- GenAI safety ----
    if gen:
        if gen["injection_asr"] > rules["genai"]["max_injection_asr"]:
            flags.add("HUMAN_REVIEW")
            reasons.append(f"Injection ASR {gen['injection_asr']:.2f} above limit")
            actions.append("Harden the system prompt and add input/output filters")
        if gen["jailbreak_asr"] > rules["genai"]["max_jailbreak_asr"]:
            flags.add("HUMAN_REVIEW")
            reasons.append(f"Jailbreak ASR {gen['jailbreak_asr']:.2f} above limit")
            actions.append("Add jailbreak test cases and refusal rules")
        if gen.get("pii_leak_asr", 0) > rules["genai"]["max_pii_leak"]:
            flags.add("BLOCK")
            reasons.append("PII leakage detected")
            actions.append("Block release until PII leakage is fixed")
        if gen["over_refusal_rate"] > rules["genai"]["max_over_refusal"]:
            flags.add("CONDITIONAL")
            reasons.append(f"Over-refusal {gen['over_refusal_rate']:.2f} above limit")
            actions.append("Relax filters that block normal questions")

    # ---- Final status ----
    for status in ("BLOCK", "HUMAN_REVIEW", "CONDITIONAL"):
        if status in flags:
            break
    else:
        status = "PASS"
        reasons.append("All checks within thresholds")

    # Confidence: lower when data is missing or review is needed
    confidence = 0.9
    if "HUMAN_REVIEW" in flags:
        confidence = 0.5
    elif not (fair and expl) and not gen:
        confidence = 0.6

    return Decision(status=status, confidence=confidence, reasons=reasons,
                    corrective_actions=actions, evidence_run_id=run_id)