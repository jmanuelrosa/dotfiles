"""Shared python for the scripts this repo authors.

Role-neutral on purpose. A tool in `roles/ai/` and a tool in `roles/work/` both need
the same output vocabulary, and neither role can import from the other, so the one
real copy lives here and each tool reaches it through a committed symlink beside its
executable. That is why this is `lib/python/` and not a third copy inside a role.

Stdlib-only, with no exemption. These modules are imported by tools that run from
`~/.local/bin` on a machine that may have nothing but `python3`.
"""
