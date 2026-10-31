"""Shared python for the scripts this repo authors.

Role-neutral on purpose. A tool in `roles/ai/` and a tool in `roles/work/` both need
the same output vocabulary, and neither role can import from the other, so the copy
lives here and each tool reaches it through a committed symlink beside its executable.
That is why this is `lib/python/` and not a copy inside a role.

`ui` and `colors` are vendored from the dotkit repository and pinned in the root
`dotkit.json`: change them there and re-vendor, since test_dotkit_vendored.py rejects an
edit made here. `testing` belongs to this repository and is not vendored.

Stdlib-only, with no exemption. These modules are imported by tools that run from
`~/.local/bin` on a machine that may have nothing but `python3`.
"""
