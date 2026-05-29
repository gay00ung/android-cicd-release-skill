from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill/android-cicd-release/scripts/inspect_android_cicd_release.py"
FIXTURES = ROOT / "tests/fixtures"


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def make_git_repo(fixture: str, tag: str | None = None) -> Path:
    tmp = Path(tempfile.mkdtemp())
    shutil.copytree(FIXTURES / fixture, tmp, dirs_exist_ok=True)

    run(["git", "init", "-b", "main"], tmp)
    run(["git", "config", "user.email", "test@example.com"], tmp)
    run(["git", "config", "user.name", "Test User"], tmp)
    run(["git", "add", "."], tmp)
    commit = run(["git", "commit", "-m", "chore: initial version"], tmp)
    if commit.returncode != 0:
        raise RuntimeError(commit.stderr)
    if tag:
        created = run(["git", "tag", tag], tmp)
        if created.returncode != 0:
            raise RuntimeError(created.stderr)
    return tmp


class InspectAndroidCicdReleaseTests(unittest.TestCase):
    def tearDown(self) -> None:
        tmp = getattr(self, "tmp", None)
        if tmp is not None:
            shutil.rmtree(tmp)

    def test_detects_github_actions_versions_and_tag_pattern(self) -> None:
        self.tmp = make_git_repo("github-actions-tag", tag="v1.2.3")

        result = run([sys.executable, str(SCRIPT), "--json", "--require-ci", str(self.tmp)], ROOT)

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["branch"], "main")
        self.assertTrue(report["worktree_clean"])
        self.assertEqual(report["ci_files"][0]["kind"], "GitHub Actions")
        self.assertEqual(report["android_versions"][0]["path"], "app/build.gradle")
        self.assertEqual(report["android_versions"][0]["matches"][0]["next"], "13")
        self.assertEqual(report["android_versions"][0]["matches"][1]["next_patch"], "1.2.4")
        self.assertEqual(report["semver_tag_patterns"][0]["pattern"], "v{version}")

    def test_detects_gitlab_ci_and_kotlin_dsl_versions(self) -> None:
        self.tmp = make_git_repo("gitlab-tag", tag="android-v2.3.4")

        result = run([sys.executable, str(SCRIPT), "--json", "--require-ci", str(self.tmp)], ROOT)

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["ci_files"][0]["kind"], "GitLab CI")
        hints = json.dumps(report["ci_trigger_hints"])
        self.assertIn("GitLab tag variable", hints)
        self.assertEqual(report["android_versions"][0]["path"], "app/build.gradle.kts")
        self.assertEqual(report["android_versions"][0]["matches"][0]["next"], "8")
        self.assertEqual(report["android_versions"][0]["matches"][1]["next_patch"], "2.3.5")
        self.assertEqual(report["semver_tag_patterns"][0]["pattern"], "android-v{version}")

    def test_detects_jenkins_tag_release_hint(self) -> None:
        self.tmp = make_git_repo("jenkins-tag", tag="release/0.9.9")

        result = run([sys.executable, str(SCRIPT), "--json", "--require-ci", str(self.tmp)], ROOT)

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["ci_files"][0]["kind"], "Jenkins")
        hints = json.dumps(report["ci_trigger_hints"])
        self.assertIn("tag ref check", hints)
        self.assertEqual(report["semver_tag_patterns"][0]["pattern"], "release/{version}")

    def test_detects_gradle_properties_versions(self) -> None:
        self.tmp = make_git_repo("gradle-properties", tag="v3.4.5")

        result = run([sys.executable, str(SCRIPT), "--json", "--require-ci", str(self.tmp)], ROOT)

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["android_versions"][0]["path"], "gradle.properties")
        self.assertEqual(report["android_versions"][0]["matches"][0]["next"], "43")
        self.assertEqual(report["android_versions"][0]["matches"][1]["next_patch"], "3.4.6")

    def test_require_ci_fails_without_ci_files(self) -> None:
        self.tmp = make_git_repo("no-ci")

        result = run([sys.executable, str(SCRIPT), "--require-ci", str(self.tmp)], ROOT)

        self.assertEqual(result.returncode, 3)
        self.assertIn("CI/CD files:\n  none", result.stdout)

    def test_non_git_path_fails(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

        result = run([sys.executable, str(SCRIPT), str(self.tmp)], ROOT)

        self.assertEqual(result.returncode, 2)
        self.assertIn("not a git repository", result.stdout)


if __name__ == "__main__":
    unittest.main()
