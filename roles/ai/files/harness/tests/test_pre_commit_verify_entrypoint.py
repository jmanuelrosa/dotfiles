import importlib.machinery
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


HOOK = Path(__file__).resolve().parents[1] / "hooks" / "pre-commit-verify.sh"
LOADER = importlib.machinery.SourceFileLoader("pre_commit_verify", str(HOOK))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
VERIFY = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(VERIFY)


class VerificationEntrypointTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def package(self, scripts):
        (self.root / "package.json").write_text(json.dumps({"scripts": scripts}))

    def test_verify_precedes_raw_checks_for_each_package_manager(self):
        self.package({"verify": "project bundle", "typecheck": "tsc", "lint": "eslint"})
        for lockfile, manager in (
            ("bun.lock", "bun"),
            ("bun.lockb", "bun"),
            ("pnpm-lock.yaml", "pnpm"),
            ("yarn.lock", "yarn"),
            (None, "npm"),
        ):
            with (
                self.subTest(manager=manager, lockfile=lockfile),
                patch.object(
                    VERIFY.Path,
                    "is_file",
                    lambda path: path.name in {"package.json", lockfile},
                ),
            ):
                self.assertEqual(
                    VERIFY.detect_commands(self.root), [[manager, "run", "verify"]]
                )

    def test_raw_check_fallback_is_unchanged_without_verify(self):
        self.package({"typecheck": "tsc", "type-check": "tsc", "lint": "eslint"})
        (self.root / "bun.lock").touch()
        self.assertEqual(
            VERIFY.detect_commands(self.root),
            [["bun", "run", name] for name in ("typecheck", "type-check", "lint")],
        )

    def test_failed_verify_blocks_without_falling_back(self):
        self.package({"verify": "project bundle", "typecheck": "tsc", "lint": "eslint"})
        payload = {"cwd": str(self.root), "tool_input": {"command": "git commit -m test"}}
        failure = subprocess.CompletedProcess(["npm", "run", "verify"], 17, "failed", "")
        with (
            patch.object(VERIFY.sys, "stdin", io.StringIO(json.dumps(payload))),
            patch.object(VERIFY.sys, "stderr", io.StringIO()),
            patch.object(VERIFY, "repo_root", return_value=str(self.root)),
            patch.object(VERIFY, "has_own_precommit", return_value=False),
            patch.object(VERIFY, "untrusted_reason", return_value=None),
            patch.object(VERIFY.subprocess, "run", return_value=failure) as run,
            self.assertRaises(SystemExit) as result,
        ):
            VERIFY.main()
        self.assertEqual(result.exception.code, 2)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0], ["npm", "run", "verify"])

    def test_untrusted_repositories_do_not_execute_verify(self):
        self.package({"verify": "project bundle"})
        payload = {"cwd": str(self.root), "tool_input": {"command": "git commit -m test"}}
        with (
            patch.object(VERIFY.sys, "stdin", io.StringIO(json.dumps(payload))),
            patch.object(VERIFY.sys, "stderr", io.StringIO()),
            patch.object(VERIFY, "repo_root", return_value=str(self.root)),
            patch.object(VERIFY, "has_own_precommit", return_value=False),
            patch.object(VERIFY, "untrusted_reason", return_value="untrusted origin"),
            patch.object(VERIFY.subprocess, "run") as run,
            self.assertRaises(SystemExit) as result,
        ):
            VERIFY.main()
        self.assertEqual(result.exception.code, 0)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
