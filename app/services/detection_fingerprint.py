"""
Builds a deterministic fingerprint per detection so the same real-world
finding doesn't get re-inserted every time the scheduler re-runs and
re-discovers a condition that's still true.

Each detector defines what makes a detection "the same" in its own domain —
an anomaly is the same if it's the same sector, category, and calendar date;
a sequence match is the same if it's the same template matched against the
same starting event; a cross-source cluster is the same if it's the same
location and the same set of contributing events.
"""
import hashlib


def make_fingerprint(*parts: str) -> str:
    """Joins parts with a separator unlikely to appear in any real value,
    then hashes — order matters, so always pass parts in a consistent order."""
    joined = "|".join(str(p) for p in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()