import re


def slugify(text):
    """Lowercase text and replace runs of non-alphanumerics with single hyphens."""
    text = text.lower()
    return re.sub(r"[^a-z0-9]", "-", text)
