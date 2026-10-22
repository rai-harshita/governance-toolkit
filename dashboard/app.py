import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

st.set_page_config(page_title="AI Governance Toolkit", page_icon=None, layout="wide")

EVIDENCE = Path("evidence/latest.json")
AUDIT = Path("evidence/audit_log.jsonl")

# ---------------- Palette ----------------
COLORS = {"PASS": "#0E9F6E", "CONDITIONAL": "#F59E0B", "BLOCK": "#EF4444", "HUMAN_REVIEW": "#3B82F6"}
SCORES = {"PASS": 100, "CONDITIONAL": 60, "HUMAN_REVIEW": 40, "BLOCK": 0}
REVIEW_STATES = ["Pending", "In Review", "Approved", "Rejected", "Needs Fix"]
BG = "#0F1219"
CARD = "#1A1F2C"
BORDER = "#2D3548"
TEXT = "#E5E7EB"
MUTED = "#9CA3AF"
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

/* ---- Sidebar navigation ---- */
[data-testid="stSidebar"] > div:first-child {padding-top: 1.2rem;}
.brand {font-size: 1.05rem; font-weight: 700; color: #E5E7EB; margin: 0; letter-spacing: .01em;}
.brand-sub {font-size: .68rem; color: #9CA3AF; text-transform: uppercase;
            letter-spacing: .12em; margin: 2px 0 0;}
.nav-label {font-size: .66rem; color: #6B7280; text-transform: uppercase;
            letter-spacing: .14em; margin: 18px 0 6px;}
[data-testid="stSidebar"] [role="radiogroup"] {gap: 0;}
[data-testid="stSidebar"] [role="radiogroup"] label {
    padding: 8px 12px; margin: 0; border-radius: 4px; border-left: 3px solid transparent;
    width: 100%; cursor: pointer;}
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child {display: none;}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {background: #232a3a;}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
    background: #232a3a; border-left: 3px solid #3B82F6;}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {
    color: #FFFFFF; font-weight: 600;}
[data-testid="stSidebar"] [role="radiogroup"] label p {font-size: .9rem; color: #B8BFCC;}
.meta {font-size: .72rem; color: #9CA3AF; line-height: 1.7; margin: 0;}
.meta b {color: #E5E7EB; font-weight: 600;}
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


ev = load_evidence()
if ev is None:
    st.error("No evidence found. Run `python run_all.py` first.")
    st.stop()

records = {r["system"]["name"]: r for r in ev["records"]}
TAB = records["Adult Income Classifier"]
BOT = records["College Helpdesk Bot"]

# ---------------- Sidebar ----------------
st.sidebar.markdown(
    '<p class="brand">AI Governance Toolkit</p>'
    '<p class="brand-sub">Release review register</p>',
    unsafe_allow_html=True)
st.sidebar.markdown('<p class="nav-label">Sections</p>', unsafe_allow_html=True)
page = st.sidebar.radio(
    "Sections",
    ["Overview", "Fairness", "Explainability", "GenAI Safety", "Release Gate"],
    label_visibility="collapsed",
)
st.sidebar.markdown('<p class="nav-label">Evidence</p>', unsafe_allow_html=True)
st.sidebar.markdown(
    f'<p class="meta"><b>Run</b> &nbsp;{ev["run_id"]}<br>'
    f'<b>Date</b> &nbsp;{ev["timestamp"][:10]}<br>'
    f'<b>Time</b> &nbsp;{ev["timestamp"][11:19]}<br>'
    f'<b>Systems</b> &nbsp;{len(records)}</p>',
    unsafe_allow_html=True)
if st.sidebar.button("Reload evidence", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# ---------------- Overview ----------------
if page == "Overview":
    st.title("Release Governance Overview")
    st.caption("Fairness, explainability and generative-AI safety evidence, "
               "converted into release decisions.")

    statuses = [r["decision"]["status"] for r in records.values()]
    open_actions = sum(len(r["decision"]["corrective_actions"]) for r in records.values())
    readiness = sum(SCORES[s] for s in statuses) / len(statuses)

    left, right = st.columns([2, 1])
    with left:
        k = st.columns(4)
        for col, (label, val) in zip(k, [
            ("Systems governed", len(records)),
            ("Blocked", statuses.count("BLOCK")),
            ("Conditional / review", statuses.count("CONDITIONAL") + statuses.count("HUMAN_REVIEW")),
            ("Open corrective actions", open_actions),
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
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Average of PASS=100, CONDITIONAL=60, HUMAN_REVIEW=40, BLOCK=0")

    st.subheader("Systems")
    for name, r in records.items():
        d = r["decision"]
        review = latest_review(name)
        st.markdown(
            f'<div class="card" style="border-left: 5px solid {COLORS[d["status"]]}">'
            f'<h3 style="margin:0">{name} &nbsp; {pill(d["status"])}</h3>'
            f'<p style="color:#9CA3AF;margin:4px 0 0">{r["system"]["system_type"]} · '
            f'owner {r["system"]["owner"]} · review state: <b>{review}</b></p></div>',
            unsafe_allow_html=True)
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            st.markdown("**Why this decision**")
            for reason in d["reasons"]:
                st.write(f"• {reason}")
        with c2:
            st.markdown("**Required corrective actions**")
            for a in d["corrective_actions"] or ["None"]:
                st.write(f"• {a}")
        with c3:
            st.metric("Confidence", f"{d['confidence']:.0%}")
            st.caption(f"Evidence: {d['evidence_run_id']}")
        with st.expander("Documented assumptions and limitations"):
            st.write("**Assumptions**")
            for a in r["assumptions"]:
                st.write(f"- {a}")
            st.write("**Limitations**")
            for l in r["limitations"]:
                st.write(f"- {l}")

# ---------------- Fairness ----------------
elif page == "Fairness":
    st.title("Fairness Evaluation")
    st.caption("System: Adult Income Classifier · sensitive attribute: sex")
    sg = TAB["subgroups"][0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Accuracy", f"{TAB['performance']['accuracy']:.3f}")
    c2.metric("F1", f"{TAB['performance']['f1']:.3f}")
    c3.metric("DP gap", f"{sg['dp_difference']:.3f}",
              delta=f"{sg['dp_difference'] - 0.10:+.3f} vs limit 0.10", delta_color="inverse")
    c4.metric("EO gap", f"{sg['eo_difference']:.3f}",
              delta=f"{sg['eo_difference'] - 0.20:+.3f} vs limit 0.20", delta_color="inverse")

    small = {g: n for g, n in sg["group_sizes"].items() if n < 100}
    if small:
        st.error(f"Small-sample warning: {small}. Metrics for these groups are unreliable.")

    m = ev["mitigation"]
    left, right = st.columns(2)
    with left:
        st.subheader("Outcomes by group")
        df = pd.DataFrame(sg["per_group"]).T.reset_index().rename(columns={"index": "group"})
        long = df.melt(id_vars="group", var_name="metric", value_name="value")
        fig = px.bar(long, x="group", y="value", color="metric", barmode="group", text_auto=".2f",
                     color_discrete_sequence=[BLUE, GREY])
        fig.update_layout(height=380, yaxis_title="rate", xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Group sizes: " + ", ".join(f"{k}: {v:,}" for k, v in sg["group_sizes"].items()))
    with right:
        st.subheader("Before vs after mitigation")
        rows = []
        for stage, key in [("Before", "before"), ("After", "after")]:
            rows += [{"stage": stage, "metric": "DP gap", "value": m[key]["dp_difference"]},
                     {"stage": stage, "metric": "EO gap", "value": m[key]["eo_difference"]}]
        fig = px.bar(pd.DataFrame(rows), x="stage", y="value", color="metric", barmode="group",
                     text_auto=".3f", color_discrete_sequence=[BLUE, RED])
        fig.add_hline(y=0.10, line_dash="dash", line_color=AMBER, annotation_text="DP limit 0.10")
        fig.update_layout(height=380, yaxis_title="gap", xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

    b, a = m["before"], m["after"]
    st.dataframe(pd.DataFrame({
        "Stage": ["Before", "After (demographic parity)"],
        "Accuracy": [b["accuracy"], a["accuracy"]], "F1": [b["f1"], a["f1"]],
        "DP gap": [b["dp_difference"], a["dp_difference"]],
        "EO gap": [b["eo_difference"], a["eo_difference"]]}).round(3), hide_index=True,
        use_container_width=True)
    st.warning(f"Trade-off: mitigation cut the DP gap by {b['dp_difference'] - a['dp_difference']:.3f} "
               f"and cost {b['accuracy'] - a['accuracy']:.3f} accuracy, but the EO gap rose from "
               f"{b['eo_difference']:.3f} to {a['eo_difference']:.3f}.")

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
        st.plotly_chart(fig, use_container_width=True)
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
        st.plotly_chart(fig, use_container_width=True)

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
    c1, c2, c3 = st.columns(3)
    c1.metric("Injection ASR (hardened)", f"{s['hardened']['injection_asr']:.0%}",
              delta=f"{s['hardened']['injection_asr'] - s['baseline']['injection_asr']:+.0%} vs baseline",
              delta_color="inverse")
    c2.metric("Jailbreak ASR (hardened)", f"{s['hardened']['jailbreak_asr']:.0%}",
              delta=f"{s['hardened']['jailbreak_asr'] - s['baseline']['jailbreak_asr']:+.0%} vs baseline",
              delta_color="inverse")
    c3.metric("Over-refusal (hardened)", f"{s['hardened']['over_refusal_rate']:.0%}",
              delta=f"{s['hardened']['over_refusal_rate'] - s['baseline']['over_refusal_rate']:+.0%} vs baseline",
              delta_color="inverse")

    rows = [{"category": c, "mode": m_, "ASR": s[m_][f"{c}_asr"]} for c in cats for m_ in ("baseline", "hardened")]
    fig = px.bar(pd.DataFrame(rows), x="category", y="ASR", color="mode", barmode="group",
                 text_auto=".0%", color_discrete_map={"baseline": RED, "hardened": TEAL})
    fig.update_layout(height=380, yaxis_tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Small prompt suite (24 prompts): one prompt moves a rate by 17-25 points. "
               "Treat rates as indicative, not precise.")

    rws = ev["genai_rows"]
    st.subheader("Successful attacks (failure patterns)")
    fails = [r for r in rws if r["attack_success"]]
    if not fails:
        st.success("No successful attacks recorded.")
    for r in fails:
        with st.expander(f"[{r['mode']}] {r['id']} · {r['category']}"):
            st.write("**Prompt:**", r["prompt"])
            st.write("**Reply:**", r["reply"])
    st.subheader("Benign prompts refused by the hardened bot (over-refusal)")
    refused = [r for r in rws if r["mode"] == "hardened" and r["category"] == "benign" and r["refused"]]
    if not refused:
        st.success("None.")
    for r in refused:
        with st.expander(f"{r['id']}: {r['prompt']}"):
            st.write(r["reply"])

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
            st.write("Unresolved risks / required actions: " + "; ".join(d["corrective_actions"] or ["none"]))

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