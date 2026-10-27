import pytest
from pydantic import ValidationError

from schema.governance_record import Decision, GovernanceRecord, Performance, SystemInfo


def system():
    return SystemInfo(name="Demo", version="1.0", owner="Team", system_type="tabular_classifier",
                      intended_use="Test", out_of_scope="Production")


def test_incomplete_record_is_valid():
    rec = GovernanceRecord(system=system())
    assert rec.performance is None and rec.decision is None and rec.subgroups == []


def test_accuracy_out_of_range_rejected():
    with pytest.raises(ValidationError):
        Performance(accuracy=1.5, f1=0.7, dataset_version="v1")


def test_unknown_system_type_rejected():
    with pytest.raises(ValidationError):
        SystemInfo(name="x", version="1", owner="o", system_type="robot", intended_use="a", out_of_scope="b")


def test_unknown_decision_status_rejected():
    with pytest.raises(ValidationError):
        Decision(status="MAYBE", confidence=0.5, reasons=[], corrective_actions=[], evidence_run_id="r")


def test_confidence_must_be_between_0_and_1():
    with pytest.raises(ValidationError):
        Decision(status="PASS", confidence=1.4, reasons=[], corrective_actions=[], evidence_run_id="r")


def test_record_round_trips_through_json():
    rec = GovernanceRecord(system=system(), performance=Performance(accuracy=0.8, f1=0.6, dataset_version="v1"))
    again = GovernanceRecord.model_validate_json(rec.model_dump_json())
    assert again.performance.accuracy == 0.8