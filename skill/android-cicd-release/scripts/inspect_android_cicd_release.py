#!/usr/bin/env python3
"""Inspect Android CI/CD release readiness for the android-cicd-release skill."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


CI_PATTERNS = [
    (".github/workflows/*.yml", "GitHub Actions"),
    (".github/workflows/*.yaml", "GitHub Actions"),
    (".gitlab-ci.yml", "GitLab CI"),
    (".gitlab-ci.yaml", "GitLab CI"),
    ("Jenkinsfile", "Jenkins"),
    ("jenkinsfile", "Jenkins"),
    (".circleci/config.yml", "CircleCI"),
    (".circleci/config.yaml", "CircleCI"),
    (".travis.yml", "Travis CI"),
    ("azure-pipelines.yml", "Azure Pipelines"),
    ("azure-pipelines.yaml", "Azure Pipelines"),
    ("bitbucket-pipelines.yml", "Bitbucket Pipelines"),
    (".buildkite/pipeline.yml", "Buildkite"),
    (".buildkite/pipeline.yaml", "Buildkite"),
    (".drone.yml", "Drone CI"),
    (".drone.yaml", "Drone CI"),
    ("codemagic.yaml", "Codemagic"),
    ("codemagic.yml", "Codemagic"),
]

EXCLUDED_DIRS = {
    ".git",
    ".gradle",
    ".idea",
    ".m2",
    "build",
    "node_modules",
    "Pods",
    "DerivedData",
}

VERSION_CODE_PATTERNS = [
    re.compile(r"\bversionCode\s*(?:=|\s)\s*(?P<value>\d+)\b"),
    re.compile(r"\bversionCode\.set\(\s*(?P<value>\d+)\s*\)"),
    re.compile(r"^\s*VERSION_CODE\s*=\s*(?P<value>\d+)\s*$"),
]

VERSION_NAME_PATTERNS = [
    re.compile(r"\bversionName\s*(?:=|\s)\s*[\"'](?P<value>[^\"']+)[\"']"),
    re.compile(r"\bversionName\.set\(\s*[\"'](?P<value>[^\"']+)[\"']\s*\)"),
    re.compile(r"^\s*VERSION_NAME\s*=\s*(?P<value>\S+)\s*$"),
]

TRIGGER_HINTS = [
    (re.compile(r"\bon\s*:\s*push\b", re.IGNORECASE), "push trigger"),
    (re.compile(r"\btags\s*:", re.IGNORECASE), "tag filter"),
    (re.compile(r"\bonly\s*:\s*(\[)?\s*tags\b", re.IGNORECASE), "GitLab tag-only job"),
    (re.compile(r"\brules\s*:", re.IGNORECASE), "rules block"),
    (re.compile(r"\bCI_COMMIT_TAG\b"), "GitLab tag variable"),
    (re.compile(r"\brefs/tags\b"), "tag ref check"),
    (re.compile(r"\bGITHUB_REF_TYPE\b.*\btag\b|\btag\b.*\bGITHUB_REF_TYPE\b"), "GitHub tag type check"),
    (re.compile(r"\bgithub\.ref\b.*\brefs/tags\b|\brefs/tags\b.*\bgithub\.ref\b"), "GitHub tag ref check"),
    (re.compile(r"\bworkflow_dispatch\b", re.IGNORECASE), "manual GitHub workflow"),
    (re.compile(r"\bwhen\s*:\s*manual\b", re.IGNORECASE), "manual GitLab job"),
    (re.compile(r"\btag_name\b", re.IGNORECASE), "release tag name"),
    (re.compile(r"\bfastlane\b", re.IGNORECASE), "fastlane release command"),
]

SEMVER_IN_TAG = re.compile(r"(?P<version>\d+\.\d+\.\d+)")
STRICT_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def run_git(root: Path, args: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def find_repo_root(cwd: Path) -> Path | None:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.strip())


def rel(root: Path, path: Path) -> str:
    return str(path.relative_to(root))


def find_ci_files(root: Path) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    seen: set[Path] = set()
    for pattern, kind in CI_PATTERNS:
        for path in sorted(root.glob(pattern)):
            if path.is_file() and path not in seen:
                results.append({"path": rel(root, path), "kind": kind})
                seen.add(path)
    return results


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def find_android_versions(root: Path) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    target_names = {"build.gradle", "build.gradle.kts", "gradle.properties"}

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name not in target_names or should_skip(path.relative_to(root)):
            continue

        text = read_text(path)
        lines = text.splitlines()
        matches: list[dict[str, object]] = []
        has_android_app = (
            "com.android.application" in text
            or 'id("com.android.application")' in text
            or "id 'com.android.application'" in text
        )

        for index, line in enumerate(lines, start=1):
            for pattern in VERSION_CODE_PATTERNS:
                match = pattern.search(line)
                if match:
                    value = match.group("value")
                    matches.append(
                        {
                            "kind": "versionCode",
                            "line": index,
                            "value": value,
                            "next": str(int(value) + 1),
                            "text": line.strip(),
                        }
                    )
            for pattern in VERSION_NAME_PATTERNS:
                match = pattern.search(line)
                if match:
                    value = match.group("value")
                    next_value = None
                    if STRICT_SEMVER.match(value):
                        major, minor, patch = [int(part) for part in value.split(".")]
                        next_value = f"{major}.{minor}.{patch + 1}"
                    matches.append(
                        {
                            "kind": "versionName",
                            "line": index,
                            "value": value,
                            "next_patch": next_value,
                            "strict_semver": bool(STRICT_SEMVER.match(value)),
                            "text": line.strip(),
                        }
                    )

        if matches:
            candidates.append(
                {
                    "path": rel(root, path),
                    "android_application_plugin": has_android_app,
                    "matches": matches,
                }
            )

    return candidates


def scan_trigger_hints(root: Path, ci_files: list[dict[str, str]]) -> list[dict[str, object]]:
    hints: list[dict[str, object]] = []
    for ci_file in ci_files:
        path = root / ci_file["path"]
        lines = read_text(path).splitlines()
        file_matches: list[dict[str, object]] = []
        for index, line in enumerate(lines, start=1):
            for pattern, label in TRIGGER_HINTS:
                if pattern.search(line):
                    file_matches.append(
                        {"line": index, "hint": label, "text": line.strip()[:220]}
                    )
                    break
        if file_matches:
            hints.append({"path": ci_file["path"], "matches": file_matches[:30]})
    return hints


def tag_metadata(root: Path) -> tuple[list[str], dict[str, str]]:
    code, out, _ = run_git(root, ["tag", "--sort=-creatordate"])
    tags = out.splitlines() if code == 0 and out else []

    code, out, _ = run_git(
        root,
        ["for-each-ref", "--format=%(refname:short)\t%(objecttype)", "refs/tags"],
    )
    object_types: dict[str, str] = {}
    if code == 0 and out:
        for line in out.splitlines():
            if "\t" in line:
                tag, object_type = line.split("\t", 1)
                object_types[tag] = object_type

    return tags, object_types


def semver_tag_patterns(tags: list[str], object_types: dict[str, str]) -> list[dict[str, str]]:
    patterns: list[dict[str, str]] = []
    seen: set[str] = set()

    for tag in tags:
        match = SEMVER_IN_TAG.search(tag)
        if not match:
            continue
        prefix = tag[: match.start("version")]
        suffix = tag[match.end("version") :]
        pattern = f"{prefix}{{version}}{suffix}"
        key = f"{pattern}:{object_types.get(tag, 'unknown')}"
        if key in seen:
            continue
        patterns.append(
            {
                "tag": tag,
                "version": match.group("version"),
                "pattern": pattern,
                "object_type": object_types.get(tag, "unknown"),
            }
        )
        seen.add(key)
        if len(patterns) >= 10:
            break

    return patterns


def history_hints(root: Path) -> list[str]:
    code, out, _ = run_git(
        root,
        [
            "log",
            "--oneline",
            "--decorate",
            "--all",
            "--max-count=30",
            "--regexp-ignore-case",
            "--grep=version",
            "--grep=release",
            "--grep=bump",
            "--grep=versionCode",
            "--grep=versionName",
        ],
    )
    if code != 0 or not out:
        return []
    return out.splitlines()


def build_report(cwd: Path) -> tuple[int, dict[str, object]]:
    root = find_repo_root(cwd)
    if root is None:
        return 2, {"git_repo": False, "error": "not a git repository"}

    _, branch, _ = run_git(root, ["branch", "--show-current"])
    _, status, _ = run_git(root, ["status", "--short"])
    ci_files = find_ci_files(root)
    tags, object_types = tag_metadata(root)

    report: dict[str, object] = {
        "git_repo": True,
        "repo_root": str(root),
        "branch": branch,
        "worktree_clean": status == "",
        "status_short": status.splitlines(),
        "ci_files": ci_files,
        "ci_trigger_hints": scan_trigger_hints(root, ci_files),
        "android_versions": find_android_versions(root),
        "recent_tags": tags[:30],
        "semver_tag_patterns": semver_tag_patterns(tags, object_types),
        "history_hints": history_hints(root),
    }
    return 0, report


def print_human(report: dict[str, object]) -> None:
    if not report.get("git_repo"):
        print(f"Git repo: no ({report.get('error')})")
        return

    print(f"Repo: {report['repo_root']}")
    print(f"Branch: {report.get('branch') or '(detached or unknown)'}")
    print(f"Worktree clean: {'yes' if report.get('worktree_clean') else 'no'}")

    status = report.get("status_short") or []
    if status:
        print("Uncommitted changes:")
        for line in status:
            print(f"  {line}")

    print("\nCI/CD files:")
    ci_files = report.get("ci_files") or []
    if ci_files:
        for item in ci_files:
            print(f"  {item['path']} ({item['kind']})")
    else:
        print("  none")

    print("\nCI/CD release-trigger hints:")
    trigger_hints = report.get("ci_trigger_hints") or []
    if trigger_hints:
        for item in trigger_hints:
            print(f"  {item['path']}")
            for match in item["matches"]:
                print(f"    L{match['line']}: {match['hint']}: {match['text']}")
    else:
        print("  none")

    print("\nAndroid version candidates:")
    versions = report.get("android_versions") or []
    if versions:
        for item in versions:
            plugin = "application plugin" if item["android_application_plugin"] else "plugin not detected"
            print(f"  {item['path']} ({plugin})")
            for match in item["matches"]:
                if match["kind"] == "versionCode":
                    print(
                        f"    L{match['line']}: versionCode {match['value']} -> {match['next']}"
                    )
                else:
                    next_patch = match.get("next_patch") or "not strict X.Y.Z"
                    print(
                        f"    L{match['line']}: versionName {match['value']} -> {next_patch}"
                    )
    else:
        print("  none")

    print("\nSemver-like tag patterns:")
    patterns = report.get("semver_tag_patterns") or []
    if patterns:
        for item in patterns:
            tag_style = "annotated" if item["object_type"] == "tag" else "lightweight"
            print(f"  {item['tag']} -> {item['pattern']} ({tag_style})")
    else:
        print("  none")

    print("\nRecent version/release commit hints:")
    history = report.get("history_hints") or []
    if history:
        for line in history[:20]:
            print(f"  {line}")
    else:
        print("  none")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect Android CI/CD release readiness for a Git repository."
    )
    parser.add_argument("path", nargs="?", default=".", help="Repository path to inspect")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text")
    parser.add_argument(
        "--require-ci",
        action="store_true",
        help="Exit non-zero when no CI/CD files are detected",
    )
    args = parser.parse_args()

    code, report = build_report(Path(args.path).resolve())
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_human(report)

    if code != 0:
        return code
    if args.require_ci and not report.get("ci_files"):
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

