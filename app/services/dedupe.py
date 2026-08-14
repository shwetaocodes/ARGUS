import hashlib

def make_dedupe_hash(source_id: int, external_id: str) -> str:
    raw = f"{source_id}:{external_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()