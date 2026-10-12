import unittest

from src.authz import can_access


class Attack(unittest.TestCase):
    def test_owner_other_org_denied(self):
        user = {"id": 3, "role": "member", "org_id": 1}
        resource = {"owner_id": 3, "org_id": 2}
        self.assertFalse(can_access(user, resource))
