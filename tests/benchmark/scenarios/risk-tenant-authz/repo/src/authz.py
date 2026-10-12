def can_access(user, resource):
    if user["role"] == "admin":
        return True
    return resource["owner_id"] == user["id"]
