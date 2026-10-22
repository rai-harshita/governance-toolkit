import yaml
from collections import Counter

REQUIRED = ["id", "system", "category", "input", "expected", "assumption", "acceptance"]

with open("data/test_cases.yaml", encoding="utf-8") as f:
    cases = yaml.safe_load(f)

problems = 0
for c in cases:
    missing = [k for k in REQUIRED if k not in c]
    if missing:
        problems += 1
        print(f"{c.get('id', '?')} is missing: {missing}")

print("Total cases:", len(cases))
print("By category:", dict(Counter(c["category"] for c in cases)))
print("By system:", dict(Counter(c["system"] for c in cases)))
print("All cases complete" if problems == 0 else f"{problems} cases have problems")