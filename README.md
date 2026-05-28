# Android CI/CD Release Skill

A Codex skill for safely preparing Android release bumps in repositories that already have CI/CD release automation.

This is not another versioning plugin or GitHub Action. It is a Codex workflow guardrail: inspect the repository, learn the existing release convention, ask for confirmation when the next `versionName` is not explicit, then commit, push, and create the release tag only when the repository's own CI/CD scripts show that tag pushes are the intended deployment trigger.

## Why this exists

Android release bumps are small edits with expensive failure modes:

- `versionCode` must keep increasing for every release.
- `versionName` is user-facing and often follows a team convention.
- Tag pushes can trigger real deployment pipelines.
- Every repository encodes its release rules slightly differently.

Existing tools usually automate one layer: a GitHub Action that edits Gradle files, a Gradle plugin that derives versions from tags, or a Fastlane lane. This skill is useful when those tools already exist, but the human still needs Codex to follow the repo's current CI/CD and Git history without guessing.

## Differentiators

- Refuses to run on repositories without CI/CD configuration.
- Starts with a dry-run inspection report before edits.
- Requires explicit confirmation for inferred `versionName` bumps.
- Matches existing release commit and tag conventions from Git history.
- Pushes tags only when CI/CD files show a tag-triggered release path.
- Works across GitHub Actions, GitLab CI, Jenkins, CircleCI, Buildkite, Drone, Bitbucket Pipelines, Azure Pipelines, and Codemagic by evidence rather than by forcing a single platform.

## Install

Copy the skill folder into your Codex skills directory:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skill/android-cicd-release "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Then start a new Codex session and invoke:

```text
Use $android-cicd-release to release this Android app.
```

You can also pass a target version:

```text
Use $android-cicd-release to bump this Android app to 2.0.0 and release it.
```

## Safety model

The skill tells Codex to stop before editing unless all of these are true:

- The current directory is a Git repository.
- A CI/CD configuration file is present.
- The worktree is clean.
- `main` can be fetched and fast-forwarded.
- Android version declarations are unambiguous.
- The release trigger in CI/CD is understood.

If the user does not specify a target `versionName`, Codex must ask first, for example:

```text
현재 versionName을 1.0.0에서 1.0.1로 올려도 될까요?
```

## Inspect a repository manually

The bundled script does not mutate files. It summarizes release readiness:

```bash
skill/android-cicd-release/scripts/inspect_android_cicd_release.py --require-ci /path/to/android-repo
```

JSON output:

```bash
skill/android-cicd-release/scripts/inspect_android_cicd_release.py --json /path/to/android-repo
```

## Research notes

See [docs/research.md](docs/research.md) for the market scan and positioning.

Short version:

- Android's official docs require a monotonically increasing `versionCode` and define `versionName` as the user-visible version string.
- GitHub Actions and GitLab CI both support tag-triggered workflows/pipelines.
- Existing Android version bump actions and Gradle plugins are useful, but they generally require project integration and do not act as a conservative, repo-history-aware release operator.

## Test

No third-party Python packages are required.

```bash
python3 -m unittest discover -s tests
```

## Repository layout

```text
.
├── skill/android-cicd-release/   # The installable Codex skill
├── tests/                        # Script regression tests and fixtures
├── docs/research.md              # Similar-tool research and positioning
└── README.md
```

