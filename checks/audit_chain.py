import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "evidence" / "audit_log.jsonl"
GENESIS = "0" * 64


def _hash(entry: dict, prev_hash: str) -> str:
    body = {k: v for k, v in entry.items() if k not in ("hash", "prev_hash")}
    payload = prev_hash + json.dumps(body, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_entries():
    if not AUDIT.exists():
        return []
    out = []
    for line in AUDIT.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                out.append({"_corrupt": True})
    return out


def append_entry(entry: dict) -> dict:
    entries = read_entries()
    prev = entries[-1].get("hash", GENESIS) if entries else GENESIS
    entry = dict(entry)
    entry["prev_hash"] = prev
    entry["hash"] = _hash(entry, prev)
    AUDIT.parent.mkdir(exist_ok=True)
    with AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def verify_chain():
    """Returns (ok, message, index_of_first_bad_entry or None)."""
    prev = GENESIS
    for i, e in enumerate(read_entries()):
        if e.get("_corrupt"):
            return False, f"Entry {i + 1} is not valid JSON", i
        if "hash" not in e:
            # entries written before this feature existed
            prev = GENESIS
            continue
        if e.get("prev_hash") != prev:
            return False, f"Entry {i + 1}: chain link broken (an earlier entry was changed or removed)", i
        if _hash(e, prev) != e["hash"]:
            return False, f"Entry {i + 1}: contents do not match its hash (entry was edited)", i
        prev = e["hash"]
    return True, "Chain intact: no entry has been altered", None