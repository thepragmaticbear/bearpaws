import os


def save_upload(base_dir, name, data):
    path = os.path.join(base_dir, name)
    root = os.path.realpath(base_dir)
    real = os.path.realpath(path)
    if os.path.commonpath([root, real]) != root or real == root:
        raise PermissionError(name)
    with open(path, "wb") as f:
        f.write(data)
    return path
