"""Owned keys, replaced inside a file the harness itself also writes."""


def get(tree, dotted):
    for key in dotted.split("."):
        if not isinstance(tree, dict) or key not in tree:
            return None
        tree = tree[key]
    return tree


def ordered_like(old, new):
    """`new`, with the keys `old` already had kept where they were.

    Claude rewrites its own settings file and reorders nothing it does not touch, so a
    render that moved keys around would be a diff on every build with no change in it.
    """
    if not (isinstance(old, dict) and isinstance(new, dict)):
        return new
    kept = {key: ordered_like(old[key], new[key]) for key in old if key in new}
    return {**kept, **{key: value for key, value in new.items() if key not in old}}


def put(tree, dotted, value):
    *parents, leaf = dotted.split(".")
    for key in parents:
        tree = tree.setdefault(key, {})
    tree[leaf] = ordered_like(tree.get(leaf), value)
