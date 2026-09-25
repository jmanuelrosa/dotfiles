"""TOML out, for the one file here that a harness also writes: Codex's config.toml.

The stdlib reads TOML and cannot write it. This writes back what `tomllib` read, and the
only promise it makes is `tomllib.loads(dumps(doc)) == doc`. Comments and layout are not
kept, because `tomllib` never saw them; Codex rewrites the file on its own terms anyway.
"""

import math
import re

BARE_KEY = re.compile(r"[A-Za-z0-9_-]+")
ESCAPES = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\t": "\\t", "\n": "\\n", "\f": "\\f", "\r": "\\r"}


def string(text):
    out = []
    for char in text:
        if char in ESCAPES:
            out.append(ESCAPES[char])
        elif ord(char) < 0x20 or ord(char) == 0x7F:
            out.append(f"\\u{ord(char):04x}")
        else:
            out.append(char)
    return '"' + "".join(out) + '"'


def key(name):
    return name if BARE_KEY.fullmatch(name) else string(name)


def dotted(path):
    return ".".join(key(part) for part in path)


def value(item):
    if isinstance(item, bool):
        return "true" if item else "false"
    if isinstance(item, int):
        return str(item)
    if isinstance(item, float):
        if math.isnan(item):
            return "nan"
        if math.isinf(item):
            return "inf" if item > 0 else "-inf"
        return repr(item)
    if isinstance(item, str):
        return string(item)
    if isinstance(item, list):
        return "[" + ", ".join(value(element) for element in item) + "]"
    if isinstance(item, dict):
        return "{ " + ", ".join(f"{key(k)} = {value(v)}" for k, v in item.items()) + " }" if item else "{}"
    raise TypeError(f"no TOML spelling for {type(item).__name__}: {item!r}")


def is_table_array(item):
    return isinstance(item, list) and bool(item) and all(isinstance(element, dict) for element in item)


def table(lines, path, document, header):
    """`document` at `path`: its own keys under `header`, then every table below it.

    A table holding nothing but other tables gets no header of its own, which is how a
    hand-written `[plugins."x"]` arrives without a bare `[plugins]` above it. An empty
    one keeps its header, since that header is the only thing saying it exists.
    """
    scalars = {k: v for k, v in document.items() if not isinstance(v, dict) and not is_table_array(v)}
    children = {k: v for k, v in document.items() if k not in scalars}
    if header and (scalars or not children or header.startswith("[[")):
        if lines:
            lines.append("")
        lines.append(header)
    lines += [f"{key(k)} = {value(v)}" for k, v in scalars.items()]
    for name, child in children.items():
        here = (*path, name)
        if isinstance(child, dict):
            table(lines, here, child, f"[{dotted(here)}]")
        else:
            for element in child:
                table(lines, here, element, f"[[{dotted(here)}]]")


def dumps(document):
    lines = []
    table(lines, (), document, None)
    return "\n".join(lines) + "\n"
