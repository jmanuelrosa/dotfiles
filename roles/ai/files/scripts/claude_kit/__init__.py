"""Manage Claude Code skills, agents and plugins stored in this dotfiles repo.

Scope is decided by the `global` group tag, never by the working directory. A
tagged artifact belongs in ~/.claude; everything else belongs in the enclosing
git project. Landing in ~/.claude by direct request always needs --global, so the
call site says so out loud.

Dependencies resolve their own scope rather than inheriting the parent's: a
project skill may depend on a global one and the reverse.
"""

__all__ = ["cli", "errors", "paths"]
