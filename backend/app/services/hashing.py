

import hashlib


def compute_sha256(content: bytes) -> str:
    """Compute the sha256 hex digest of file content, used for dedup lookups."""
    return hashlib.sha256(content).hexdigest()