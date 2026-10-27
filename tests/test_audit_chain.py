import json

import pytest

from checks import audit_chain


@pytest.fixture(autouse=True)
def isolated_log(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_chain, "AUDIT", tmp_path / "audit_log.jsonl")


def add(n):
    for i in range(n):
        audit_chain.append_entry({"system": "S", "state": "In Review", "reviewer": f"r{i}", "comment": ""})


def rewrite(transform):
    lines = audit_chain.AUDIT.read_text(encoding="utf-8").splitlines()
    audit_chain.AUDIT.write_text("\n".join(transform(lines)) + "\n", encoding="utf-8")


def test_empty_log_is_valid():
    ok, _, bad = audit_chain.verify_chain()
    assert ok and bad is None


def test_untouched_chain_is_valid():
    add(3)
    assert audit_chain.verify_chain()[0]


def test_entries_are_linked():
    add(2)
    first, second = audit_chain.read_entries()
    assert second["prev_hash"] == first["hash"]
    assert first["prev_hash"] == audit_chain.GENESIS


def test_editing_an_entry_is_detected():
    add(3)

    def tamper(lines):
        e = json.loads(lines[1])
        e["state"] = "Approved"
        lines[1] = json.dumps(e)
        return lines
    rewrite(tamper)
    ok, msg, bad = audit_chain.verify_chain()
    assert not ok and bad == 1 and "edited" in msg


def test_deleting_an_entry_is_detected():
    add(3)
    rewrite(lambda lines: [lines[0], lines[2]])
    ok, _, bad = audit_chain.verify_chain()
    assert not ok and bad == 1


def test_corrupt_json_is_detected():
    add(2)
    rewrite(lambda lines: lines + ["{not json"])
    ok, msg, _ = audit_chain.verify_chain()
    assert not ok and "not valid JSON" in msg


def test_old_entries_without_hash_are_tolerated():
    audit_chain.AUDIT.write_text(json.dumps({"system": "S", "state": "Approved"}) + "\n", encoding="utf-8")
    add(2)
    assert audit_chain.verify_chain()[0]