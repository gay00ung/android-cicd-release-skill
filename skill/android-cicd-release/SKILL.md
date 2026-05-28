---
name: android-cicd-release
description: Safely release Android repositories through existing CI/CD. Use when the user asks to bump Android versionCode/versionName, prepare a release commit, push main, create/push a release tag, or trigger deployment for an Android project that has GitHub Actions, GitLab CI, Jenkins, or similar CI/CD configuration. The skill must first verify CI/CD files exist and abort if they do not.
---

# Android CI/CD Release

## Core Rule

Operate only on Android Git repositories that contain CI/CD configuration. If no CI/CD file is present, stop before editing and say that this skill only applies to repositories with CI/CD release automation.

Default to a dry-run release plan. Do not edit files, commit, push, or tag until the user confirms the exact plan when any version, branch, tag, CI/CD trigger, or dirty-worktree detail is inferred.

Run `scripts/inspect_android_cicd_release.py --require-ci` from this skill first to summarize:

- CI/CD files and release-trigger hints
- Android version declarations
- recent version/release commits
- semver-like tag patterns

Treat the script as an inspection aid, not as proof that release is safe. Read the relevant CI/CD and Gradle files yourself before mutating anything.

## Hard Gates

Verify all gates before editing:

1. Confirm the current directory is a Git repo.
2. Confirm CI/CD files exist, such as `.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/config.yml`, `azure-pipelines.yml`, `bitbucket-pipelines.yml`, `.buildkite/pipeline.yml`, `.drone.yml`, or `codemagic.yaml`.
3. Confirm the worktree is clean. If unrelated changes exist, stop and ask the user how to handle them.
4. Fetch `origin/main` and tags with `git fetch origin main --tags`.
5. Work from `main`: checkout `main`, then fast-forward with `git pull --ff-only origin main`. If the repo has no `main` branch, ask before using another branch.
6. Inspect CI/CD scripts to identify the release trigger. Use tag release only when the scripts indicate tag-triggered deployment, such as `on.push.tags`, `CI_COMMIT_TAG`, `only: tags`, `refs/tags`, or equivalent Jenkins/CI tag checks. If the trigger is manual or unclear, ask the user with the specific evidence found.

## Learn the Repo Convention

Read commit and tag history before deciding names or messages:

- `git log --oneline --decorate --all --grep=version --grep=release --grep=bump --grep=versionCode --grep=versionName --regexp-ignore-case`
- `git tag --sort=-creatordate`
- `git show` on the most relevant previous release bump commits or tags

Match the repository's established conventions for:

- release commit message format
- whether version bumps touch one module or multiple files
- tag prefix/suffix, for example `v1.2.3`, `android-v1.2.3`, or `release/1.2.3`
- annotated versus lightweight tags

If no usable convention exists, use `chore: bump Android version to X.Y.Z` for the commit and ask before choosing the default tag format `vX.Y.Z`.

## Version Bump Rules

Locate the Android application module and edit the `android` block that defines the app release version, usually in `build.gradle` or `build.gradle.kts`.

- Increment `versionCode` by exactly 1.
- Require `versionName` to be semantic version format with exactly three numeric components: `X.Y.Z`.
- Reject or ask about `versionName` values like `1.0`, `1`, `1.0.0-beta`, or non-literal property indirection unless the repo history clearly shows how to update them.
- If the user supplied a target `versionName`, validate it as `X.Y.Z` and use it.
- If the user did not supply a target `versionName`, propose a patch bump from the current version and wait for explicit confirmation before editing. Ask in the user's language, for example: `현재 versionName을 1.0.0에서 1.0.1로 올려도 될까요?`

If multiple Android application modules or multiple plausible `versionName` declarations exist, ask which module/version should be released.

## Release Plan Confirmation

Before mutating files, show a concise plan:

- current branch and target branch
- current and proposed `versionCode`
- current and proposed `versionName`
- files to edit
- validation command to run
- commit message
- tag name and whether it is annotated or lightweight
- CI/CD evidence that pushing that tag triggers release

Proceed only after explicit user confirmation.

## Commit, Push, and Release

After the versionName is confirmed and the CI/CD release trigger is understood:

1. Edit only the required version file(s).
2. Run the narrowest practical validation command, preferring commands used by the repo's CI/CD scripts. At minimum, run a Gradle task that verifies the edited module can be configured or assembled when available.
3. Review `git diff` and stage only the release-version changes.
4. Commit using the learned convention, or `chore: bump Android version to X.Y.Z` if no convention exists.
5. Confirm again before any remote push if the user has not already explicitly approved push/tag operations in the same request.
6. Push `main` with `git push origin main`.
7. Create the release tag on the pushed commit only if CI/CD scripts indicate tag-triggered release.
8. Match the previous compatible tag pattern by replacing only the version portion with the new `versionName`. For prior tag `v1.0.0`, create `vX.Y.Z`.
9. Match annotated/lightweight style. If the previous matching tag is annotated, create `git tag -a TAG -m "Release TAG"`; otherwise create `git tag TAG`.
10. Push exactly that tag with `git push origin TAG`. Do not use `git push --tags`.

Never create a tag that already exists. Never push a guessed tag format when no compatible previous tag exists unless the user has confirmed the chosen format.

## Final Report

Report:

- previous and new `versionCode`
- previous and new `versionName`
- files changed
- commit hash pushed to `main`
- tag pushed, or why no tag was pushed
- CI/CD trigger evidence used
- validation commands run and their results

