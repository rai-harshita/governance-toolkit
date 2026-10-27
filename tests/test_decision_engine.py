from decision_engine import decide

GOOD = {
    "fairness": {"dp_difference": 0.05, "eo_difference": 0.05, "group_sizes": {"M": 500, "F": 400}},
    "explanation": {"stability": 0.95, "proxy_scores": {"relationship": 0.10}},
    "genai": {"injection_asr": 0.0, "jailbreak_asr": 0.0, "pii_leak_asr": 0.0, "over_refusal_rate": 0.05},
}


def with_fair(**kw):
    return {**GOOD, "fairness": {**GOOD["fairness"], **kw}}


def with_gen(**kw):
    return {**GOOD, "genai": {**GOOD["genai"], **kw}}


def test_pass_when_everything_within_limits():
    d = decide(GOOD, "t")
    assert d.status == "PASS" and d.confidence == 0.9
    assert d.reasons == ["All checks within thresholds"]


def test_conditional_on_moderate_dp_gap():
    d = decide(with_fair(dp_difference=0.15), "t")
    assert d.status == "CONDITIONAL" and d.corrective_actions


def test_block_on_large_dp_gap():
    assert decide(with_fair(dp_difference=0.30), "t").status == "BLOCK"


def test_equalized_odds_gap_triggers_conditional():
    assert decide(with_fair(eo_difference=0.33), "t").status == "CONDITIONAL"


def test_human_review_on_injection_attacks():
    d = decide(with_gen(injection_asr=0.20), "t")
    assert d.status == "HUMAN_REVIEW" and d.confidence == 0.5


def test_pii_leak_blocks_release():
    assert decide(with_gen(pii_leak_asr=0.05), "t").status == "BLOCK"


def test_over_refusal_is_conditional():
    assert decide(with_gen(over_refusal_rate=0.30), "t").status == "CONDITIONAL"


def test_missing_fairness_goes_to_human_review():
    d = decide({"genai": GOOD["genai"]}, "t")
    assert d.status == "HUMAN_REVIEW"
    assert "Fairness results missing" in d.reasons


def test_tiny_subgroup_goes_to_human_review():
    d = decide(with_fair(group_sizes={"M": 500, "F": 20}), "t")
    assert d.status == "HUMAN_REVIEW"


def test_unstable_explanations_are_conditional():
    bad = {**GOOD, "explanation": {"stability": 0.4, "proxy_scores": {}}}
    assert decide(bad, "t").status == "CONDITIONAL"


def test_strong_proxy_feature_is_conditional():
    bad = {**GOOD, "explanation": {"stability": 0.95, "proxy_scores": {"relationship": 0.27}}}
    assert decide(bad, "t").status == "CONDITIONAL"


def test_block_outranks_other_findings():
    res = with_fair(dp_difference=0.30)
    res["genai"] = {**GOOD["genai"], "injection_asr": 0.5}
    assert decide(res, "t").status == "BLOCK"


def ext(dp=0.05, di=0.95, ci=(0.04, 0.06), small=()):
    return {"attributes": {"race": {"dp_difference": dp, "disparate_impact_ratio": di,
                                    "dp_ci": list(ci), "small_groups": list(small)}},
            "intersectional": {"small_groups": []},
            "counterfactual": {"selected_gb": {"flip_rate": 0.0}}}


def test_extended_low_disparate_impact_blocks():
    assert decide(GOOD, "t", extended=ext(di=0.31)).status == "BLOCK"


def test_extended_80_percent_rule_is_conditional():
    assert decide(GOOD, "t", extended=ext(di=0.70)).status == "CONDITIONAL"


def test_extended_ci_lower_bound_above_limit_blocks():
    assert decide(GOOD, "t", extended=ext(dp=0.25, ci=(0.23, 0.27))).status == "BLOCK"


def test_extended_small_groups_need_human_review():
    assert decide(GOOD, "t", extended=ext(small=["Other"])).status == "HUMAN_REVIEW"


def test_extended_counterfactual_flips_are_conditional():
    e = ext()
    e["counterfactual"]["selected_gb"]["flip_rate"] = 0.05
    assert decide(GOOD, "t", extended=e).status == "CONDITIONAL"


def test_evidence_run_id_is_recorded():
    assert decide(GOOD, "run_123").evidence_run_id == "run_123"