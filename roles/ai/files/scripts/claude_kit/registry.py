"""Writing back to skill-registry.json.

The registry is hand-maintained, so a write has to change exactly the field it
means to and nothing else. json.load preserves object order into a dict and
json.dump writes it back in that order, so a load-modify-dump round trip is
order-preserving as long as no key is reinserted.
"""

import json


def _matches(entry, upstream_path):
    return (entry.get("upstream_path") or "") == (upstream_path or "")


def stamp_entry(path, repo, upstream_path, timestamp, collection="skills"):
    """Set updated_at on one tracked entry, leaving the rest byte-identical.

    Matched by (repo, upstream_path) rather than by derived name, because the name
    is a basename and two repos can legitimately supply the same one.

    Returns True if an entry was found and written.
    """
    data = json.loads(path.read_text())
    entries = ((data.get("repos") or {}).get(repo) or {}).get(collection) or []
    found = False
    for entry in entries:
        if _matches(entry, upstream_path):
            entry["updated_at"] = timestamp
            found = True
    if not found:
        return False
    path.write_text(json.dumps(data, indent=2) + "\n")
    return True
