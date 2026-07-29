"""One module per subcommand.

Each exposes run(args) -> exit code. Command modules own presentation and
sequencing only; the rules they enforce live in catalog.py, scope.py and
state.py so they can be tested without a filesystem.
"""
