import os


def read_user_file(base_dir, name):
    """Return the text of an uploaded file stored under base_dir."""
    path = os.path.join(base_dir, name)
    with open(path) as f:
        return f.read()
