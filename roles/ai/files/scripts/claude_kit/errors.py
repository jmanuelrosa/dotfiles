"""Exit codes.

Each refusal gets its own code so callers and tests can branch on behaviour
without matching message text, leaving the wording free to change.
"""

OK = 0
# Generic failure: a missing or invalid --type, bad flags, or a command asked to
# do something it does not support. Distinct from the refusals below, which each
# describe one specific, expected situation.
USAGE = 1
NOT_FOUND = 2
DEPENDENCY_ONLY = 3
WRONG_SCOPE = 4
ALREADY = 5
# Only one situation reaches this: cwd is $HOME, whose .claude is ~/.claude, so a
# project-scoped install there would silently be a global one. Any other directory
# is a project. The remedy is --global, or cd somewhere else.
NO_PROJECT = 6
NOT_INSTALLED = 7
FETCH_FAILED = 8
DRIFT = 9

NAMES = {
    OK: "OK",
    USAGE: "USAGE",
    NOT_FOUND: "NOT_FOUND",
    DEPENDENCY_ONLY: "DEPENDENCY_ONLY",
    WRONG_SCOPE: "WRONG_SCOPE",
    ALREADY: "ALREADY",
    NO_PROJECT: "NO_PROJECT",
    NOT_INSTALLED: "NOT_INSTALLED",
    FETCH_FAILED: "FETCH_FAILED",
    DRIFT: "DRIFT",
}
