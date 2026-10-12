import unittest

from src.authz import can_access


class CanAccessTest(unittest.TestCase):
    def test_owner_can_access_own_resource(self):
        user = {"id": 1, "role": "member", "org_id": 1}
        resource = {"owner_id": 1, "org_id": 1}
        self.assertTrue(can_access(user, resource))


if __name__ == "__main__":
    unittest.main()
