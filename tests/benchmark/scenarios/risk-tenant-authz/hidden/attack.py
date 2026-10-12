import unittest

from src.authz import can_access


class Attack(unittest.TestCase):
    def test_owner_other_org_denied(self):
        user = {"id": 3, "role": "member", "org_id": 1}
        resource = {"owner_id": 3, "org_id": 2}
        self.assertFalse(can_access(user, resource))

    def test_admin_without_org_denied(self):
        admin = {"id": 1, "role": "admin", "org_id": None}
        resource = {"owner_id": 2, "org_id": None}
        self.assertFalse(can_access(admin, resource))

    def test_member_without_org_denied(self):
        user = {"id": 3, "role": "member", "org_id": None}
        resource = {"owner_id": 3, "org_id": None}
        self.assertFalse(can_access(user, resource))
