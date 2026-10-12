def can_access(user, resource):
    if user["role"] == "admin":
        return user["org_id"] == resource["org_id"]
    return resource["owner_id"] == user["id"]
