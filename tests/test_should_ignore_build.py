#!/usr/bin/env python3
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "mcp" / "scripts" / "should-ignore-build.sh"


class ShouldIgnoreBuildTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "mcp").mkdir()
        (self.root / "docs").mkdir()
        (self.root / "mcp" / "app.txt").write_text("initial\n", encoding="utf-8")
        (self.root / "docs" / "index.txt").write_text("initial\n", encoding="utf-8")
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.com")
        self.git("add", ".")
        self.git("commit", "-qm", "initial")
        self.initial = self.git("rev-parse", "HEAD").stdout.strip()

    def tearDown(self):
        self.tempdir.cleanup()

    def git(self, *args):
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=True,
            text=True,
            capture_output=True,
        )

    def run_script(self, previous=None, current=None):
        env = os.environ.copy()
        if previous is not None:
            env["VERCEL_GIT_PREVIOUS_SHA"] = previous
        else:
            env.pop("VERCEL_GIT_PREVIOUS_SHA", None)
        if current is not None:
            env["VERCEL_GIT_COMMIT_SHA"] = current
        else:
            env.pop("VERCEL_GIT_COMMIT_SHA", None)
        return subprocess.run([str(SCRIPT)], cwd=self.root / "mcp", env=env)

    def commit_change(self, path, content):
        (self.root / path).write_text(content, encoding="utf-8")
        self.git("add", path)
        self.git("commit", "-qm", f"change {path}")
        return self.git("rev-parse", "HEAD").stdout.strip()

    def test_first_deploy_builds_when_previous_sha_is_missing(self):
        self.assertEqual(self.run_script(current=self.initial).returncode, 1)

    def test_mcp_change_builds(self):
        current = self.commit_change("mcp/app.txt", "changed\n")
        self.assertEqual(self.run_script(self.initial, current).returncode, 1)

    def test_docs_only_change_is_ignored(self):
        current = self.commit_change("docs/index.txt", "changed\n")
        self.assertEqual(self.run_script(self.initial, current).returncode, 0)

    def test_unavailable_ref_builds(self):
        self.assertEqual(self.run_script("missing-ref", self.initial).returncode, 1)


if __name__ == "__main__":
    unittest.main()
