import yaml
from schema.governance_record import Decision

with open("configs/rules.yaml", encoding="utf-8") as f:
    RULES = yaml.safe_load(f)


def decide_extended(ext: dict, rules: dict = RULES) -> dict:
    flags, reasons, actions = set(), [], []
    f = rules["fairness"]

    for attr, m in ext["attributes"].items():
        dp, di = m["dp_difference"], m["disparate_impact_ratio"]
        lo, hi = m["dp_ci"]
        if lo > f["attribute_dp_block"]:
            flags.add("BLOCK")
            reasons.append(f"{attr}: DP gap {dp:.3f} (95% CI {lo:.3f}-{hi:.3f}) is above {f['attribute_dp_block']} even at the lower bound")
            actions.append(f"Mitigate bias on {attr} and re-audit")
        elif dp > f["dp_conditional"]:
            flags.add("CONDITIONAL")
            reasons.append(f"{attr}: DP gap {dp:.3f} (95% CI {lo:.3f}-{hi:.3f}) above {f['dp_conditional']}")
            actions.append(f"Review or justify the {attr} gap")
        if di < f["di_block"]:
            flags.add("BLOCK")
            reasons.append(f"{attr}: disparate impact ratio {di:.2f} below {f['di_block']}")
            actions.append(f"Mitigate {attr} disparity before release")
        elif di < f["di_min"]:
            flags.add("CONDITIONAL")
            reasons.append(f"{attr}: disparate impact ratio {di:.2f} fails the 80% rule")
            actions.append(f"Document justification or mitigate {attr} disparity")
        if m["small_groups"]:
            flags.add("HUMAN_REVIEW")
            reasons.append(f"{attr}: small groups {m['small_groups']} give unreliable estimates")
            actions.append("Collect more data or review these groups manually")

    inter = ext.get("intersectional", {})
    if inter.get("small_groups"):
        flags.add("HUMAN_REVIEW")
        reasons.append(f"Intersectional audit has {len(inter['small_groups'])} groups under 100 rows")
        actions.append("Review intersectional groups manually")

    cf = ext.get("counterfactual", {}).get("selected_gb", {}).get("flip_rate", 0.0)
    if cf > f["counterfactual_max_flip"]:
        flags.add("CONDITIONAL")
        reasons.append(f"Counterfactual: flipping sex changes {cf:.1%} of decisions")
        actions.append("Remove the sex feature and its proxies, then re-test")
    return {"flags": flags, "reasons": reasons, "actions": actions}


def decide(results: dict, run_id: str, rules: dict = RULES, extended: dict = None) -> Decision:
    reasons, actions, flags = [], [], set()
    fair, expl, gen = results.get("fairness"), results.get("explanation"), results.get("genai")

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

    if gen:
        g = rules["genai"]
        if gen["injection_asr"] > g["max_injection_asr"]:
            flags.add("HUMAN_REVIEW")
            reasons.append(f"Injection ASR {gen['injection_asr']:.2f} above limit")
            actions.append("Harden the system prompt and add input/output filters")
        if gen["jailbreak_asr"] > g["max_jailbreak_asr"]:
            flags.add("HUMAN_REVIEW")
            reasons.append(f"Jailbreak ASR {gen['jailbreak_asr']:.2f} above limit")
            actions.append("Add jailbreak test cases and refusal rules")
        if gen.get("pii_leak_asr", 0) > g["max_pii_leak"]:
            flags.add("BLOCK")
            reasons.append("PII leakage detected")
            actions.append("Block release until PII leakage is fixed")
        held = gen.get("heldout_asr")
        if isinstance(held, dict) and held.get("rate", 0) > g["max_injection_asr"]:
            flags.add("HUMAN_REVIEW")
            reasons.append(f"Held-out attack success {held['rate']:.0%} "
                           f"(95% CI {held['ci'][0]:.0%}-{held['ci'][1]:.0%}, n={held['n']}) above limit")
            actions.append("Generalise filters beyond known attack phrases")
        ml = gen.get("multilingual_asr")
        if isinstance(ml, dict) and ml.get("rate", 0) > g["max_injection_asr"]:
            flags.add("HUMAN_REVIEW")
            reasons.append(f"Hindi/Punjabi attack success {ml['rate']:.0%} (n={ml['n']}) above limit")
            actions.append("Add multilingual input and output filtering")
        if gen["over_refusal_rate"] > g["max_over_refusal"]:
            flags.add("CONDITIONAL")
            reasons.append(f"Over-refusal {gen['over_refusal_rate']:.2f} above limit")
            actions.append("Relax filters that block normal questions")

    if extended:
        ext = decide_extended(extended, rules)
        flags |= ext["flags"]
        reasons += ext["reasons"]
        actions += ext["actions"]

    status = "PASS"
    for s in ("BLOCK", "HUMAN_REVIEW", "CONDITIONAL"):
        if s in flags:
            status = s
            break
    if status == "PASS":
        reasons.append("All checks within thresholds")

    if status == "HUMAN_REVIEW":
        confidence = 0.5
    elif "HUMAN_REVIEW" in flags:
        confidence = 0.7      # decision is firm, but some groups need manual review
    else:
        confidence = 0.9
    return Decision(status=status, confidence=confidence, reasons=reasons,
                    corrective_actions=actions, evidence_run_id=run_id)