from pathlib import Path

root = Path(".").resolve()
print("Project root:", root)
print()
for name in ["login_page.py", "theme.py", "decision_engine.py"]:
    found = [str(p.relative_to(root)) for p in root.rglob(name) if ".venv" not in p.parts]
    print(f"{name:20}", found if found else "NOT FOUND ANYWHERE")

print("\nFirst 22 lines of dashboard/app.py:\n")
for i, line in enumerate(Path("dashboard/app.py").read_text(encoding="utf-8").splitlines()[:22], 1):
    print(f"{i:2}  {line}")