from typing import Any

def resolve_path(obj: Any, path: str) -> Any:
    """Helper to resolve dot-notation path on an object or dict."""
    parts = path.split(".")
    curr = obj
    for p in parts:
        if hasattr(curr, p):
            curr = getattr(curr, p)
        elif isinstance(curr, dict) and p in curr:
            curr = curr[p]
        else:
            return None
    return curr
