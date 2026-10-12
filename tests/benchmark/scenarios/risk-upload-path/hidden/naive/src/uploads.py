import os


def save_upload(base_dir, name, data):
    if ".." in name.replace("\\", "/").split("/"):
        raise PermissionError(name)
    path = os.path.join(base_dir, name)
    with open(path, "wb") as f:
        f.write(data)
    return path
