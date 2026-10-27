import json

import pytest

from checks import auth


@pytest.fixture(autouse=True)
def isolated_users(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "USERS", tmp_path / "users.json")


def test_create_and_authenticate():
    auth.create_user("alice_01", "longpassword", "reviewer", "Alice")
    u = auth.authenticate("alice_01", "longpassword")
    assert u == {"username": "alice_01", "role": "reviewer", "name": "Alice"}


def test_username_is_case_insensitive():
    auth.create_user("Bob_01", "longpassword")
    assert auth.authenticate("BOB_01", "longpassword")["username"] == "bob_01"


def test_wrong_password_rejected():
    auth.create_user("carol", "longpassword")
    assert auth.authenticate("carol", "wrongpassword") is None


def test_unknown_user_rejected():
    assert auth.authenticate("nobody", "whatever123") is None


def test_duplicate_username_rejected():
    auth.create_user("dave_1", "longpassword")
    with pytest.raises(ValueError):
        auth.create_user("dave_1", "otherpassword")


@pytest.mark.parametrize("name,pw,role", [
    ("ab", "longpassword", "submitter"),          # username too short
    ("bad name", "longpassword", "submitter"),    # not a valid identifier
    ("eve_1", "short", "submitter"),              # password too short
    ("eve_2", "longpassword", "superuser"),       # unknown role
])
def test_invalid_input_rejected(name, pw, role):
    with pytest.raises(ValueError):
        auth.create_user(name, pw, role)


def test_password_is_never_stored_in_plain_text():
    auth.create_user("frank_1", "my-secret-pass")
    raw = auth.USERS.read_text(encoding="utf-8")
    assert "my-secret-pass" not in raw
    assert ":" in json.loads(raw)["frank_1"]["hash"]    # salt:hash


def test_same_password_gets_different_hashes():
    auth.create_user("gina_1", "samepassword")
    auth.create_user("hank_1", "samepassword")
    users = auth.load_users()
    assert users["gina_1"]["hash"] != users["hank_1"]["hash"]


def test_submitter_cannot_see_reviewer_pages():
    assert "Release Gate" not in auth.ROLE_PAGES["submitter"]
    assert "Release Gate" in auth.ROLE_PAGES["reviewer"]
    assert "Audit a System" in auth.ROLE_PAGES["admin"]