"""The output vocabulary the catalog's own scripts print through.

A copy of `ui` and `colors` from the dotfiles `lib/python/dotkit`, kept here so the
catalog runs on a machine that has no dotfiles checkout. Each script reaches it through
a committed `dotkit` symlink beside its executable.

Stdlib-only, with no exemption. These modules are imported by skill scripts that may
run with nothing but `python3`.
"""
