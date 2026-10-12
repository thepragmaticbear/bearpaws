import unittest

from src.authz import can_access


class Accept(unittest.TestCase):
    def test_admin_other_org_denied(self):
        admin = {"id": 1, "role": "admin", "org_id": 1}
        resource = {"owner_id": 2, "org_id": 2}
        self.assertFalse(can_access(admin, resource))

    def test_admin_same_org_allowed(self):
        admin = {"id": 1, "role": "admin", "org_id": 1}
        resource = {"owner_id": 2, "org_id": 1}
        self.assertTrue(can_access(admin, resource))

    def test_owner_same_org_allowed(self):
        user = {"id": 3, "role": "member", "org_id": 1}
        resource = {"owner_id": 3, "org_id": 1}
        self.assertTrue(can_access(user, resource))
