#!/usr/bin/env bash
# Fixture: a one-line authorization bug next to untidy, unrelated code and no authz tests.
set -euo pipefail
work="$1"
mkdir -p "$work/src" "$work/tests"
cd "$work"
touch src/__init__.py tests/__init__.py
cat > src/authz.py <<'PY'
def can_access(user, resource):
    if user["role"] == "admin":
        return True
    return user["id"] == resource["owner_id"] or user["org_id"] == resource["org_id"]


def format_user(u):
    # TODO: tidy this up
    s = ""
    s = s + u["name"]
    s = s + " <" + u["email"] + ">"
    return s
PY
cat > tests/test_users.py <<'PY'
import unittest
from src.authz import format_user


class FormatUserTest(unittest.TestCase):
    def test_format(self):
        self.assertEqual(format_user({"name": "Ann", "email": "a@x.io"}), "Ann <a@x.io>")


if __name__ == "__main__":
    unittest.main()
PY
cat > README.md <<'MD'
# authz-service
Run tests: `python3 -m unittest discover -s tests -t .`
MD
git init -q && git config user.email t@example.com && git config user.name T
git add . && git commit -qm fixture
