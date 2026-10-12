def can_access(user, resource):
    if user["org_id"] is None or resource["org_id"] is None:
        return False
    if user["org_id"] != resource["org_id"]:
        return False
    if user["role"] == "admin":
        return True
    return resource["owner_id"] == user["id"]
