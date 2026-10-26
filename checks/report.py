from datetime import datetime

from fpdf import FPDF

from checks.audit_chain import read_entries, verify_chain
from checks.policy_map import match

STATUS_RGB = {"PASS": (14, 159, 110), "CONDITIONAL": (245, 158, 11),
              "BLOCK": (239, 68, 68), "HUMAN_REVIEW": (59, 130, 246)}


def _safe(text):
    """Built-in PDF fonts are Latin-1 only; replace anything else."""
    return (str(text).replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'")
            .replace("\u201c", '"').replace("\u201d", '"')
            .encode("latin-1", "replace").decode("latin-1"))


class Report(FPDF):
    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"AequiGate audit report - page {self.page_no()}", align="C")


def h1(pdf, text):
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(31, 58, 95)
    pdf.ln(3)
    pdf.cell(0, 8, _safe(text), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(200, 205, 215)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(2)


def para(pdf, text, size=10, bold=False, indent=0):
    pdf.set_font("Helvetica", "B" if bold else "", size)
    pdf.set_text_color(30, 30, 30)
    pdf.set_x(pdf.l_margin + indent)
    pdf.multi_cell(0, 5.5, _safe(text), new_x="LMARGIN", new_y="NEXT")


def build_report(record, run_id, metrics, findings, review_state, severity_fn):
    """record: governance record dict. metrics: list of (label, value, note).
    findings: list of (reason, action). Returns PDF bytes."""
    d = record["decision"]
    pdf = Report(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(31, 58, 95)
    pdf.cell(0, 10, "AI Release Audit Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 6, _safe(f"{record['system']['name']}  |  generated {datetime.now():%Y-%m-%d %H:%M}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, _safe(f"Evidence run: {run_id}"), new_x="LMARGIN", new_y="NEXT")

    # Decision banner
    pdf.ln(4)
    r, g, b = STATUS_RGB.get(d["status"], (90, 90, 90))
    pdf.set_fill_color(r, g, b)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 11, _safe(f"  DECISION: {d['status'].replace('_', ' ')}   (confidence {d['confidence']:.0%})"),
             fill=True, new_x="LMARGIN", new_y="NEXT")
    para(pdf, f"Human review state: {review_state}", bold=True)

    h1(pdf, "1. System")
    s = record["system"]
    para(pdf, f"Type: {s['system_type']}    Owner: {s['owner']}    Version: {s['version']}")
    para(pdf, f"Intended use: {s['intended_use']}")
    para(pdf, f"Out of scope: {s['out_of_scope']}")

    h1(pdf, "2. Key metrics")
    for label, val, note in metrics:
        para(pdf, f"- {label}: {val}" + (f"   ({note})" if note else ""))

    h1(pdf, "3. Findings and required corrective actions")
    if not findings:
        para(pdf, "No findings. All checks are within thresholds.")
    for i, (reason, action) in enumerate(findings, 1):
        para(pdf, f"{i}. [{severity_fn(reason)}] {reason}", bold=True)
        if action:
            para(pdf, f"Action: {action}", indent=6)
        tags = match(reason)
        if tags:
            para(pdf, "Supports: " + "; ".join(
                f"NIST {t['nist'].split(' (')[0]}, EU {t['eu'].split(' (')[0]}"
                for t in tags[:2]), size=9, indent=6)

    h1(pdf, "4. Documented assumptions")
    for a in record.get("assumptions", []) or ["None recorded"]:
        para(pdf, f"- {a}")
    h1(pdf, "5. Documented limitations")
    for lim in record.get("limitations", []) or ["None recorded"]:
        para(pdf, f"- {lim}")

    h1(pdf, "6. Human review history")
    mine = [e for e in read_entries() if e.get("system") == s["name"]]
    if not mine:
        para(pdf, "No reviews recorded yet. Release is not permitted until a reviewer approves.")
    for e in mine:
        para(pdf, f"- {e.get('time', '')}  {e.get('state', '')}  by {e.get('reviewer', '')}: "
                  f"{e.get('comment', '') or '(no comment)'}")
    ok, msg, _ = verify_chain()
    para(pdf, f"Audit log integrity: {'PASSED' if ok else 'FAILED'} - {msg}", bold=True)

    ok_release = d["status"] != "BLOCK" and review_state == "Approved"
    h1(pdf, "7. Release gate")
    para(pdf, "RELEASE ALLOWED" if ok_release else "RELEASE NOT ALLOWED", bold=True, size=12)
    if not ok_release:
        why = []
        if d["status"] == "BLOCK":
            why.append("decision is BLOCK")
        if review_state != "Approved":
            why.append(f"human review is '{review_state}', not Approved")
        para(pdf, "Reason: " + "; ".join(why))

    pdf.ln(6)
    para(pdf, "Sign-off: ______________________   Name: ______________________   Date: ____________", size=10)
    pdf.ln(2)
    para(pdf, "Automated evidence supports, but does not replace, human judgment. Thresholds are policy "
              "choices defined in configs/rules.yaml. Confidence intervals reflect sampling uncertainty only.",
         size=8)
    return bytes(pdf.output())
