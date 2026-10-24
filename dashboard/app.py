import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

st.set_page_config(page_title="AI Governance Toolkit", page_icon=None, layout="wide")

EVIDENCE = Path("evidence/latest.json")
AUDIT = Path("evidence/audit_log.jsonl")
RISKS = Path("evidence/risk_register.json")

# ---------------- Palette ----------------
COLORS = {"PASS": "#0E9F6E", "CONDITIONAL": "#F59E0B", "BLOCK": "#EF4444", "HUMAN_REVIEW": "#3B82F6"}
SCORES = {"PASS": 100, "CONDITIONAL": 60, "HUMAN_REVIEW": 40, "BLOCK": 0}
REVIEW_STATES = ["Pending", "In Review", "Approved", "Rejected", "Needs Fix"]
TEXT = "#E5E7EB"
BORDER = "#2D3548"
BLUE = "#3B82F6"
TEAL = "#0E9F6E"
RED = "#EF4444"
AMBER = "#F59E0B"
GREY = "#64748B"

pio.templates["gov_dark"] = go.layout.Template(layout=dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT),
    xaxis=dict(gridcolor=BORDER, linecolor=BORDER, zerolinecolor=BORDER),
    yaxis=dict(gridcolor=BORDER, linecolor=BORDER, zerolinecolor=BORDER),
    legend=dict(font=dict(color=TEXT)),
))
pio.templates.default = "gov_dark"

st.markdown("""
<style>
.block-container {padding-top: 2rem; max-width: 1200px;}
#MainMenu, footer {visibility: hidden;}
[data-testid="stSidebar"] {background: #1A1F2C; border-right: 1px solid #2D3548;}
.card {border: 1px solid #2D3548; border-radius: 6px; padding: 14px 18px;
       margin-bottom: 12px; background: #1A1F2C;}
.pill {display:inline-block; padding: 2px 10px; border-radius: 3px; color: #0F1219;
       font-weight: 700; font-size: 0.78rem; letter-spacing: .05em; text-transform: uppercase;}
.kpi {border: 1px solid #2D3548; border-radius: 6px; padding: 14px 16px; background: #1A1F2C;
      min-height: 112px;}
.kpi h2 {margin: 0; font-size: 1.8rem; color: #E5E7EB;}
.kpi p {margin: 0; color: #9CA3AF; font-size: .8rem; text-transform: uppercase; letter-spacing: .04em;}
h1, h2, h3 {color: #E5E7EB;}
[data-testid="stMetric"] {background: #1A1F2C; border: 1px solid #2D3548;
       border-radius: 6px; padding: 12px 14px;}
[data-testid="stExpander"], [data-testid="stForm"] {border-color: #2D3548;}

[data-testid="stSidebar"] > div:first-child {padding-top: 1.2rem;}
[data-testid="stSidebar"] .brand {font-size: 1.05rem !important; font-weight: 700;
    color: #E5E7EB; margin: 0; line-height: 1.3;}
[data-testid="stSidebar"] .brand-sub {font-size: .68rem !important; color: #9CA3AF;
    text-transform: uppercase; letter-spacing: .12em; margin: 2px 0 0; line-height: 1.3;}
[data-testid="stSidebar"] .nav-label {font-size: .66rem !important; color: #6B7280;
    text-transform: uppercase; letter-spacing: .14em; margin: 18px 0 6px;}
[data-testid="stSidebar"] .meta {font-size: .74rem !important; color: #9CA3AF;
    line-height: 1.7; margin: 0;}
[data-testid="stSidebar"] .meta b {color: #E5E7EB; font-weight: 600;}

[data-testid="stSidebar"] .stButton > button {
    width: 100%; justify-content: flex-start; text-align: left;
    background: transparent; color: #B8BFCC; border: none;
    border-left: 3px solid transparent; border-radius: 4px;
    padding: 6px 12px; box-shadow: none; min-height: 0;}
[data-testid="stSidebar"] .stButton > button:hover {background: #232a3a; color: #FFFFFF;}
[data-testid="stSidebar"] .stButton > button[kind="primary"],
[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-primary"] {
    background: #232a3a; color: #FFFFFF; font-weight: 600; border-left: 3px solid #3B82F6;}
</style>
""", unsafe_allow_html=True)


# ---------------- Helpers ----------------
@st.cache_data
def load_evidence():
    if not EVIDENCE.exists():
        return None
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def read_audit():
    if not AUDIT.exists():
        return []
    return [json.loads(line) for line in AUDIT.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_risk_overrides():
    if not RISKS.exists():
        return {}
    return json.loads(RISKS.read_text(encoding="utf-8"))


def pill(status):
    return f'<span class="pill" style="background:{COLORS[status]}">{status.replace("_", " ")}</span>'


def clean(name):
    return name.split("__", 1)[-1]


def latest_review(system_name):
    state = "Pending"
    for e in read_audit():
        if e["system"] == system_name:
            state = e["state"]
    return state


def severity(reason):
    low = reason.lower()
    if any(k in low for k in ["exceeds block", "even at the lower bound", "below 0.5", "pii"]):
        return "High"
    if "over-refusal" in low:
        return "Low"
    return "Medium"


def finding_pairs(r):
    """(reason, action) pairs, duplicates removed, sorted High -> Low."""
    d = r["decision"]
    acts = d["corrective_actions"] + [""] * len(d["reasons"])
    pairs = [(a, b) for a, b in zip(d["reasons"], acts) if not a.startswith("All checks")]
    if any(a.startswith("sex: DP gap") for a, _ in pairs):
        pairs = [(a, b) for a, b in pairs if not a.startswith("DP gap ")]
    rank = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(pairs, key=lambda p: rank[severity(p[0])])


def build_risks(records):
    overrides = read_risk_overrides()
    due_default = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
    rows = []
    for name, r in records.items():
        for reason, action in finding_pairs(r):
            o = overrides.get(f"{name}|{reason}", {})
            rows.append({
                "System": name, "Risk": reason, "Severity": severity(reason),
                "Corrective action": action or "Review manually",
                "Owner": o.get("owner", r["system"]["owner"]),
                "Status": o.get("status", "Open"),
                "Due date": o.get("due", due_default),
            })
    return rows


def show_chart(fig):
    st.plotly_chart(fig, use_container_width=True)


ev = load_evidence()
if ev is None:
    st.error("No evidence found. Run `python run_all.py` first.")
    st.stop()

records = {r["system"]["name"]: r for r in ev["records"]}
TAB = records["Adult Income Classifier"]
ext = ev.get("extended")

# ---------------- Sidebar ----------------
PAGES = ["Overview", "Fairness", "Model Comparison", "Intersectional", "Explainability",
         "GenAI Safety", "Risk Register", "Release Gate"]
if "page" not in st.session_state:
    st.session_state.page = "Overview"

st.sidebar.markdown(
    '<p class="brand">AI Governance Toolkit</p>'
    '<p class="brand-sub">Release review register</p>',
    unsafe_allow_html=True)
st.sidebar.markdown('<p class="nav-label">Sections</p>', unsafe_allow_html=True)
for p_ in PAGES:
    active = st.session_state.page == p_
    if st.sidebar.button(p_, key=f"nav_{p_}", use_container_width=True,
                         type="primary" if active else "secondary"):
        st.session_state.page = p_
        st.rerun()
page = st.session_state.page

st.sidebar.markdown('<p class="nav-label">Evidence</p>', unsafe_allow_html=True)
st.sidebar.markdown(
    f'<p class="meta"><b>Run</b> &nbsp;{ev["run_id"]}<br>'
    f'<b>Date</b> &nbsp;{ev["timestamp"][:10]}<br>'
    f'<b>Time</b> &nbsp;{ev["timestamp"][11:19]}<br>'
    f'<b>Systems</b> &nbsp;{len(records)}</p>',
    unsafe_allow_html=True)
st.sidebar.write("")
if st.sidebar.button("Reload evidence", key="reload", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

if page in ("Model Comparison", "Intersectional") and not ext:
    st.warning("Extended metrics not found in the evidence file. Run `python run_all.py` again.")
    st.stop()

# ---------------- Overview ----------------
if page == "Overview":
    st.title("Release Governance Overview")
    st.caption("Fairness, explainability and generative-AI safety evidence, "
               "converted into release decisions.")

    statuses = [r["decision"]["status"] for r in records.values()]
    risks_all = build_risks(records)
    open_risks = sum(1 for x in risks_all if x["Status"] != "Resolved")
    high_risks = sum(1 for x in risks_all if x["Status"] != "Resolved" and x["Severity"] == "High")
    readiness = sum(SCORES[s] for s in statuses) / len(statuses)

    left, right = st.columns([2, 1])
    with left:
        k = st.columns(4)
        for col, (label, val) in zip(k, [
            ("Systems governed", len(records)),
            ("Blocked", statuses.count("BLOCK")),
            ("Open risks", open_risks),
            ("High severity open", high_risks),
        ]):
            col.markdown(f'<div class="kpi"><p>{label}</p><h2>{val}</h2></div>', unsafe_allow_html=True)
    with right:
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=readiness,
            title={"text": "Release readiness"},
            gauge={"axis": {"range": [0, 100]}, "bar": {"color": TEAL},
                   "steps": [{"range": [0, 40], "color": "#3B1D22"},
                             {"range": [40, 80], "color": "#3A2E14"},
                             {"range": [80, 100], "color": "#12301F"}]}))
        fig.update_layout(height=230, margin=dict(l=10, r=10, t=40, b=0))
        show_chart(fig)
        st.caption("Average of PASS=100, CONDITIONAL=60, HUMAN_REVIEW=40, BLOCK=0")

    st.subheader("Systems")

    def key_metrics(r):
        if r["system"]["system_type"] == "tabular_classifier" and ext:
            at = ext["attributes"]
            worst = max(at, key=lambda a: at[a]["dp_difference"])
            return [
                ("Worst DP gap", f"{at[worst]['dp_difference']:.3f}", f"Attribute: {worst}. Block above 0.20"),
                ("Lowest DI ratio", f"{min(v['disparate_impact_ratio'] for v in at.values()):.2f}",
                 "80% rule: at least 0.80"),
                ("Sex-flip changes", f"{ext['counterfactual']['selected_gb']['flip_rate']:.1%}", "Limit 2%"),
                ("Accuracy", f"{r['performance']['accuracy']:.3f}", "Selected model"),
            ]
        p = r["prompt_risks"]
        return [
            ("Injection ASR", f"{p['injection_asr']:.0%}", "Limit 5%"),
            ("Jailbreak ASR", f"{p['jailbreak_asr']:.0%}", "Limit 5%"),
            ("PII leakage", f"{p['pii_leak_rate']:.0%}", "Limit 0%"),
            ("Over-refusal", f"{p['over_refusal_rate']:.0%}", "Limit 15%"),
        ]

    for name, r in records.items():
        d = r["decision"]
        review = latest_review(name)
        findings = finding_pairs(r)
        st.markdown(
            f'<div class="card" style="border-left: 5px solid {COLORS[d["status"]]}">'
            f'<h3 style="margin:0">{name} &nbsp; {pill(d["status"])}</h3>'
            f'<p style="color:#9CA3AF;margin:4px 0 0">{r["system"]["system_type"]} · '
            f'owner {r["system"]["owner"]} · review state: <b>{review}</b> · '
            f'confidence {d["confidence"]:.0%} · {len(findings)} findings</p></div>',
            unsafe_allow_html=True)

        mcols = st.columns(4)
        for col, (label, val, note) in zip(mcols, key_metrics(r)):
            col.metric(label, val, help=note)

        st.markdown("**Top findings and required actions**")
        if not findings:
            st.write("No findings. All checks are within thresholds.")
        for reason, action in findings[:3]:
            st.write(f"**[{severity(reason)}]** {reason}")
            if action:
                st.caption(f"Action: {action}")
        if len(findings) > 3:
            with st.expander(f"Show all {len(findings)} findings"):
                for reason, action in findings[3:]:
                    st.write(f"**[{severity(reason)}]** {reason}")
                    if action:
                        st.caption(f"Action: {action}")
        with st.expander("Documented assumptions and limitations"):
            st.write("**Assumptions**")
            for a in r["assumptions"]:
                st.write(f"- {a}")
            st.write("**Limitations**")
            for l in r["limitations"]:
                st.write(f"- {l}")
        st.caption(f"Evidence: {d['evidence_run_id']}")
        st.write("")

# ---------------- Fairness ----------------
elif page == "Fairness":
    st.title("Fairness Evaluation")
    st.caption("System: Adult Income Classifier · selected model (gradient boosting)")
    sg = TAB["subgroups"][0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Accuracy", f"{TAB['performance']['accuracy']:.3f}")
    c2.metric("F1", f"{TAB['performance']['f1']:.3f}")
    c3.metric("DP gap (sex)", f"{sg['dp_difference']:.3f}",
              delta=f"{sg['dp_difference'] - 0.10:+.3f} vs limit 0.10", delta_color="inverse")
    c4.metric("EO gap (sex)", f"{sg['eo_difference']:.3f}",
              delta=f"{sg['eo_difference'] - 0.20:+.3f} vs limit 0.20", delta_color="inverse")

    if ext:
        attrs = ext["attributes"]
        st.subheader("Gaps across sensitive attributes, with 95% confidence intervals")
        names = list(attrs)
        dp = [attrs[a]["dp_difference"] for a in names]
        lo = [attrs[a]["dp_ci"][0] for a in names]
        hi = [attrs[a]["dp_ci"][1] for a in names]
        left, right = st.columns(2)
        with left:
            fig = go.Figure(go.Bar(
                x=names, y=dp, marker_color=BLUE, text=[f"{v:.3f}" for v in dp], textposition="outside",
                error_y=dict(type="data", symmetric=False, color=TEXT,
                             array=[h - d for h, d in zip(hi, dp)],
                             arrayminus=[d - l for d, l in zip(dp, lo)])))
            fig.add_hline(y=0.10, line_dash="dash", line_color=AMBER, annotation_text="conditional 0.10")
            fig.add_hline(y=0.20, line_dash="dash", line_color=RED, annotation_text="block 0.20")
            fig.update_layout(height=380, title="Demographic parity gap", yaxis_title="gap")
            show_chart(fig)
        with right:
            di = [attrs[a]["disparate_impact_ratio"] for a in names]
            colors = [RED if v < 0.5 else AMBER if v < 0.8 else TEAL for v in di]
            fig = go.Figure(go.Bar(x=names, y=di, marker_color=colors,
                                   text=[f"{v:.2f}" for v in di], textposition="outside"))
            fig.add_hline(y=0.80, line_dash="dash", line_color=TEAL, annotation_text="80% rule")
            fig.add_hline(y=0.50, line_dash="dash", line_color=RED, annotation_text="block 0.50")
            fig.update_layout(height=380, title="Disparate impact ratio (higher is fairer)",
                              yaxis_range=[0, 1.1])
            show_chart(fig)
        st.caption("Intervals reflect test-set sampling only (200 bootstrap resamples), "
                   "not variation from retraining the model.")

        st.dataframe(pd.DataFrame({
            "Attribute": names,
            "DP gap": dp,
            "95% CI": [f"{l:.3f} to {h:.3f}" for l, h in zip(lo, hi)],
            "DI ratio": di,
            "EO gap": [attrs[a]["eo_difference"] for a in names],
            "Equal-opportunity gap": [attrs[a]["equal_opportunity_gap"] for a in names],
            "FPR gap": [attrs[a]["fpr_gap"] for a in names],
            "Small groups": [", ".join(map(str, attrs[a]["small_groups"])) or "none" for a in names],
        }).round(3), hide_index=True, use_container_width=True)

    st.subheader("Outcomes by group (sex)")
    df = pd.DataFrame(sg["per_group"]).T.reset_index().rename(columns={"index": "group"})
    long = df.melt(id_vars="group", var_name="metric", value_name="value")
    fig = px.bar(long, x="group", y="value", color="metric", barmode="group", text_auto=".2f",
                 color_discrete_sequence=[BLUE, GREY])
    fig.update_layout(height=340, yaxis_title="rate", xaxis_title=None)
    show_chart(fig)
    st.caption("Group sizes: " + ", ".join(f"{k}: {v:,}" for k, v in sg["group_sizes"].items()))

# ---------------- Model Comparison ----------------
elif page == "Model Comparison":
    st.title("Model Comparison and Counterfactual Tests")
    st.caption("All variants evaluated on the same test split, sensitive attribute: sex.")
    mc = ext["model_comparison_sex"]
    labels = {"baseline_logreg": "Baseline (logistic regression)",
              "selected_gb": "Selected (gradient boosting)",
              "gb_without_sex": "Selected, sex column removed",
              "gb_mitigated_dp": "Mitigated for demographic parity",
              "gb_mitigated_eo": "Mitigated for equalized odds"}
    table = pd.DataFrame([{
        "Model": labels.get(k, k), "Accuracy": v["accuracy"], "F1": v["f1"],
        "DP gap": v["dp_difference"],
        "DP 95% CI": f"{v['dp_ci'][0]:.3f} to {v['dp_ci'][1]:.3f}",
        "DI ratio": v["disparate_impact_ratio"], "EO gap": v["eo_difference"],
        "FPR gap": v["fpr_gap"]} for k, v in mc.items()])
    st.dataframe(table.round(3), hide_index=True, use_container_width=True)

    gaps = pd.DataFrame([{"Model": labels.get(k, k), "DP gap": v["dp_difference"],
                          "EO gap": v["eo_difference"]} for k, v in mc.items()])
    long = gaps.melt(id_vars="Model", var_name="Gap", value_name="value")
    fig = px.bar(long, x="Model", y="value", color="Gap", barmode="group", text_auto=".3f",
                 color_discrete_sequence=[BLUE, RED])
    fig.add_hline(y=0.10, line_dash="dash", line_color=AMBER, annotation_text="limit 0.10")
    fig.update_layout(height=400, xaxis_title=None, yaxis_title="gap")
    show_chart(fig)

    worst = {k: max(v["dp_difference"], v["eo_difference"]) for k, v in mc.items()}
    best = min(worst, key=worst.get)
    st.info(f"Lowest worst-case gap: **{labels.get(best, best)}** "
            f"(max of DP and EO gap = {worst[best]:.3f}, accuracy {mc[best]['accuracy']:.3f}). "
            "Mitigating one gap raises the other, so choose by which harm matters most for the use case.")
    ns = mc["gb_without_sex"]["dp_difference"]
    st.warning(f"Removing the sex column leaves the DP gap at {ns:.3f} "
               f"(was {mc['selected_gb']['dp_difference']:.3f}): proxy features carry the same signal.")

    st.subheader("Counterfactual test: flip sex, keep everything else")
    cf = ext["counterfactual"]
    cols = st.columns(len(cf))
    for col, (name, c) in zip(cols, cf.items()):
        with col:
            st.markdown(f"**{labels.get(name, name)}**")
            st.metric("Decisions changed", f"{c['flip_rate']:.2%}",
                      delta=f"{c['flip_rate'] - 0.02:+.2%} vs limit 2%", delta_color="inverse")
            st.metric("Mean probability change", f"{c['mean_abs_prob_change']:.3f}")
            st.metric("Largest probability change", f"{c['max_abs_prob_change']:.3f}")

# ---------------- Intersectional ----------------
elif page == "Intersectional":
    st.title("Intersectional Fairness (sex × race)")
    inter = ext["intersectional"]
    c1, c2, c3 = st.columns(3)
    c1.metric("DP gap across groups", f"{inter['dp_difference']:.3f}")
    c2.metric("DI ratio", f"{inter['disparate_impact_ratio']:.3f}")
    c3.metric("Groups under 100 rows", len(inter["small_groups"]))

    rows = []
    for g, v in inter["per_group"].items():
        n = inter["group_sizes"][g]
        rows.append({"Group": g, "n": n, "Selection rate": v["selection_rate"], "TPR": v["tpr"],
                     "Reliability": "Small sample" if n < 100 else "OK"})
    df = pd.DataFrame(rows).sort_values("Selection rate")
    fig = px.bar(df, x="Selection rate", y="Group", orientation="h", color="Reliability",
                 color_discrete_map={"OK": BLUE, "Small sample": AMBER},
                 text=df["n"].map(lambda v: f"n={v:,}"))
    fig.update_layout(height=460, yaxis_title=None)
    show_chart(fig)
    st.caption("Amber bars have fewer than 100 rows. Their rates are unreliable and are routed to human review.")
    st.dataframe(df.round(3), hide_index=True, use_container_width=True)

# ---------------- Explainability ----------------
elif page == "Explainability":
    st.title("Explainability Findings")
    ex = TAB["explanation"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Method", "SHAP")
    c2.metric("Stability (Spearman)", f"{ex['stability']:.3f}",
              delta="above 0.70 limit" if ex["stability"] >= 0.7 else "below limit")
    c3.metric("Proxy features flagged", len(ex["flagged_proxies"]))

    left, right = st.columns(2)
    with left:
        st.subheader("Top features (SHAP rank)")
        feats = [clean(f) for f in ex["top_features"]][::-1]
        fig = px.bar(x=list(range(1, len(feats) + 1)), y=feats, orientation="h",
                     labels={"x": "importance rank (higher bar = more important)", "y": ""})
        fig.update_traces(marker_color=BLUE)
        fig.update_layout(height=420)
        show_chart(fig)
        if any("sex" in f for f in feats):
            st.error("The model uses `sex` directly. This is a direct fairness risk.")
    with right:
        st.subheader("Proxy risk: how much does a feature reveal sex?")
        ps = pd.Series(ev["proxy_scores"]).sort_values().tail(8)
        fig = px.bar(x=ps.values, y=ps.index, orientation="h",
                     labels={"x": "mutual information with sex", "y": ""})
        fig.update_traces(marker_color=[RED if v > 0.20 else AMBER if v > 0.05 else GREY
                                        for v in ps.values])
        fig.add_vline(x=0.20, line_dash="dash", line_color=RED, annotation_text="limit 0.20")
        fig.update_layout(height=420)
        show_chart(fig)

    st.subheader("SHAP vs permutation importance (baseline method)")
    st.dataframe(pd.DataFrame({
        "Rank": range(1, 11),
        "SHAP": [clean(f) for f in ex["top_features"]],
        "Permutation": ev["permutation_top"]}), hide_index=True, use_container_width=True)
    st.info("Where both methods agree, the explanation is more credible. "
            "Note: `fnlwgt` is a census sampling weight, so its proxy score is likely noise.")

# ---------------- GenAI Safety ----------------
elif page == "GenAI Safety":
    st.title("Generative AI Safety Evaluation")
    s = ev["genai_summary"]
    cats = ["injection", "jailbreak", "pii_leak", "bias", "hallucination"]

    def asr(mode, cat):
        v = s[mode][f"{cat}_asr"]
        return v["rate"] if isinstance(v, dict) else v

    def ci_str(mode, key):
        v = s[mode].get(key)
        if v is None:
            return ""
        if isinstance(v, dict):
            return f"95% CI [{v['ci'][0]:.0%}–{v['ci'][1]:.0%}], n={v['n']}"
        return ""

    c1, c2, c3 = st.columns(3)
    c1.metric("Injection ASR (hardened)", f"{asr('hardened','injection'):.0%}",
              delta=f"{asr('hardened','injection') - asr('baseline','injection'):+.0%} vs baseline",
              delta_color="inverse")
    c2.metric("Jailbreak ASR (hardened)", f"{asr('hardened','jailbreak'):.0%}",
              delta=f"{asr('hardened','jailbreak') - asr('baseline','jailbreak'):+.0%} vs baseline",
              delta_color="inverse")
    c3.metric("Over-refusal (hardened)", f"{s['hardened']['over_refusal_rate']:.0%}",
              delta=f"{s['hardened']['over_refusal_rate'] - s['baseline']['over_refusal_rate']:+.0%} vs baseline",
              delta_color="inverse")

    rows = [{"category": c, "mode": m_, "ASR": asr(m_, c)} for c in cats for m_ in ("baseline", "hardened")]
    fig = px.bar(pd.DataFrame(rows), x="category", y="ASR", color="mode", barmode="group",
                 text_auto=".0%", color_discrete_map={"baseline": RED, "hardened": TEAL})
    fig.update_layout(height=380, yaxis_tickformat=".0%")
    show_chart(fig)
    st.caption("Rates are indicative at this prompt-suite size. "
               "Intervals are wide — see the CI column below.")

    # Extended metrics table (only shown when new keys are present)
    ext_keys = ["heldout_asr", "multilingual_asr", "multilingual_over_refusal"]
    if any(k in s["hardened"] for k in ext_keys):
        st.subheader("Extended metrics (held-out and multilingual splits)")
        ext_rows = []
        for key in ext_keys + ["over_refusal_ci"]:
            v_h = s["hardened"].get(key)
            v_b = s["baseline"].get(key)
            if v_h is None:
                continue
            label = key.replace("_", " ").title()
            b_rate = v_b["rate"] if isinstance(v_b, dict) else (v_b or 0)
            h_rate = v_h["rate"] if isinstance(v_h, dict) else (v_h or 0)
            h_ci = f"[{v_h['ci'][0]:.0%}–{v_h['ci'][1]:.0%}]" if isinstance(v_h, dict) else ""
            ext_rows.append({"Metric": label, "Baseline": f"{b_rate:.0%}",
                             "Hardened": f"{h_rate:.0%}", "Hardened 95% CI": h_ci,
                             "n": v_h.get("n", "") if isinstance(v_h, dict) else ""})
        st.dataframe(pd.DataFrame(ext_rows), hide_index=True, use_container_width=True)

        rq_h = s["hardened"].get("refusal_quality")
        rq_b = s["baseline"].get("refusal_quality")
        if rq_h is not None:
            st.metric("Refusal quality (hardened)", f"{rq_h:.2f}",
                      delta=f"{rq_h - (rq_b or 0):+.2f} vs baseline",
                      help="0 = cold/empty refusal, 1 = refuses and redirects helpfully")

    rws = ev["genai_rows"]
    st.subheader("Successful attacks (failure patterns)")
    fails = [r for r in rws if r["attack_success"]]
    if not fails:
        st.success("No successful attacks recorded.")
    for r in fails:
        split_tag = f" · {r['split']}" if r.get("split", "main") != "main" else ""
        with st.expander(f"[{r['mode']}] {r['id']} · {r['category']}{split_tag}"):
            st.write("**Prompt:**", r["prompt"])
            st.write("**Reply:**", r["reply"])
    st.subheader("Benign prompts refused by the hardened bot (over-refusal)")
    refused = [r for r in rws if r["mode"] == "hardened" and r["category"] == "benign" and r["refused"]]
    if not refused:
        st.success("None.")
    for r in refused:
        with st.expander(f"{r['id']}: {r['prompt']}"):
            st.write(r["reply"])

# ---------------- Risk Register ----------------
elif page == "Risk Register":
    st.title("Risk Register")
    st.caption("Every unresolved finding from the latest audit, with an owner, status and due date. "
               "Edit the Owner, Status and Due date columns, then save.")
    rows = build_risks(records)
    if not rows:
        st.success("No risks recorded.")
        st.stop()

    df = pd.DataFrame(rows)
    df.insert(0, "ID", [f"R-{i + 1:02d}" for i in range(len(df))])
    openr = df[df["Status"] != "Resolved"]
    k = st.columns(4)
    for col, (label, val) in zip(k, [
        ("Total risks", len(df)), ("Open", int((df["Status"] == "Open").sum())),
        ("In progress", int((df["Status"] == "In progress").sum())),
        ("High severity open", int((openr["Severity"] == "High").sum()))]):
        col.markdown(f'<div class="kpi"><p>{label}</p><h2>{val}</h2></div>', unsafe_allow_html=True)
    st.write("")

    edited = st.data_editor(
        df, hide_index=True, use_container_width=True, key="risk_editor",
        disabled=["ID", "System", "Risk", "Severity", "Corrective action"],
        column_config={
            "Status": st.column_config.SelectboxColumn(options=["Open", "In progress", "Resolved"]),
            "Risk": st.column_config.TextColumn(width="large"),
            "Corrective action": st.column_config.TextColumn(width="medium"),
        })
    if st.button("Save risk register"):
        data = {f"{r['System']}|{r['Risk']}": {"owner": r["Owner"], "status": r["Status"], "due": r["Due date"]}
                for _, r in edited.iterrows()}
        RISKS.write_text(json.dumps(data, indent=2), encoding="utf-8")
        st.success("Risk register saved.")
    st.caption("Severity rule: High = block-level finding; Medium = threshold breach or "
               "unreliable data; Low = usability trade-off.")

# ---------------- Release Gate ----------------
elif page == "Release Gate":
    st.title("Release Gate and Human Review")
    st.caption("A system may be released only if it is not BLOCKED and a human reviewer has Approved it.")

    for name, r in records.items():
        d = r["decision"]
        review = latest_review(name)
        ok = d["status"] != "BLOCK" and review == "Approved"
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.subheader(name)
            c2.markdown(pill(d["status"]), unsafe_allow_html=True)
            c3.markdown("**RELEASE ALLOWED**" if ok else "**RELEASE NOT ALLOWED**")
            st.write(f"Review state: **{review}**")
            if not ok:
                blockers = []
                if d["status"] == "BLOCK":
                    blockers.append("Decision is BLOCK")
                if review != "Approved":
                    blockers.append(f"Human review not approved (currently {review})")
                st.write("Blockers: " + "; ".join(blockers))
            top = [a for _, a in finding_pairs(r) if a][:3]
            st.write("Top required actions: " + ("; ".join(top) if top else "none"))

    st.subheader("Record a review")
    with st.form("review_form", clear_on_submit=True):
        system = st.selectbox("System", list(records))
        state = st.selectbox("New state", REVIEW_STATES)
        reviewer = st.text_input("Reviewer name")
        comment = st.text_area("Comment")
        if st.form_submit_button("Save review"):
            if not reviewer.strip():
                st.error("Reviewer name is required.")
            else:
                entry = {"time": datetime.now().isoformat(timespec="seconds"), "system": system,
                         "state": state, "reviewer": reviewer.strip(), "comment": comment.strip(),
                         "run_id": ev["run_id"]}
                with AUDIT.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                st.success("Saved to audit log.")
                st.rerun()

    st.subheader("Audit log")
    log = read_audit()
    if log:
        st.dataframe(pd.DataFrame(log).iloc[::-1], hide_index=True, use_container_width=True)
    else:
        st.info("No reviews recorded yet.")