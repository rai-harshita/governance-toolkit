s = open("dashboard/app.py", encoding="utf-8").read()
checks = [
    "bg-layer", "hero-wrap", "wordmark", "def logo", "authenticate(",
    'elif page == "Audit a System"', 'elif page == "Policy Mapping"',
    "build_report(", "verify_chain()", "append_entry(", "load_uploads()", "ROLE_PAGES",
]
for k in checks:
    print(("OK      " if k in s else "MISSING ") + k)