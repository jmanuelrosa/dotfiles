"""Render each harness's native config from the neutral policy in policy/*.toml."""

import sys

if sys.version_info < (3, 11):
    raise SystemExit(f"harnessgen needs Python 3.11 or newer for tomllib, not {sys.version.split()[0]}")
