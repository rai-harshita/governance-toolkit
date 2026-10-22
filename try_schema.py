from pydantic import ValidationError
from schema.governance_record import GovernanceRecord, SystemInfo, Performance

system = SystemInfo(
    name="Adult Income Classifier", version="1.0", owner="Harshita",
    system_type="tabular_classifier",
    intended_use="Educational demo of income prediction",
    out_of_scope="Real hiring or lending decisions",
)

# 1) Incomplete record: only the system section is filled
incomplete = GovernanceRecord(system=system)
print("Incomplete record OK, performance =", incomplete.performance)

# 2) Complete-ish record
full = GovernanceRecord(
    system=system,
    performance=Performance(accuracy=0.86, f1=0.70, dataset_version="adult-v1"),
    limitations=["Trained on 1994 census data"],
)
print(full.model_dump_json(indent=2)[:300])

# 3) Invalid record: accuracy 1.5 should be rejected
try:
    Performance(accuracy=1.5, f1=0.7, dataset_version="adult-v1")
except ValidationError as e:
    print("Invalid record correctly rejected")