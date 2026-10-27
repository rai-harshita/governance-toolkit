from pathlib import Path

ROOT = Path(__file__).resolve().parent
s = (ROOT / "dashboard" / "app.py").read_text(encoding="utf-8")
checks = [
    "bg-layer", "hero-wrap", "wordmark", "def logo", "authenticate(",
    'elif page == "Audit a System"', 'elif page == "Policy Mapping"',
    "build_report(", "verify_chain()", "append_entry(", "load_uploads()", "ROLE_PAGES",
]
for k in checks:
    print(("OK      " if k in s else "MISSING ") + k)