# Research and Positioning

Last checked: 2026-05-28.

## Similar tools

### GitHub Marketplace Android version actions

- Android Version Bump Automatically: uses semantic commits to bump native Android Gradle versions and create releases on successful merges.
  - https://github.com/marketplace/actions/android-version-bump-automatically
- DoubleSymmetry android-version-actions: increments or overrides `versionCode` and `versionName` directly in `build.gradle` or `build.gradle.kts`.
  - https://github.com/marketplace/actions/increment-the-version-code-name-of-your-android-project

These are CI actions. They are good when the project wants version mutation to happen inside GitHub Actions, but they require adopting that workflow and do not inspect arbitrary existing CI/CD systems before a human-triggered release.

### Gradle tag-based versioning

- ReactiveCircus app-versioning derives Android `versionCode` and `versionName` from Git tags.
  - https://github.com/ReactiveCircus/app-versioning

This is strong for projects that want Gradle to compute versions from Git tags. It is not a release-operator workflow for repositories that already store literal Gradle versions and rely on existing CI/CD scripts.

### Fastlane

- Fastlane is widely used for Android and iOS deployment lanes, and many teams implement custom version bump lanes.
  - https://docs.fastlane.tools/

Fastlane is a deployment automation framework. This skill complements Fastlane by reading whether a repo already invokes Fastlane from CI/CD and then following that repo's existing release trigger.

## Relevant platform facts

- Android versioning docs: `versionCode` is an internal positive integer that should increase for each release; `versionName` is the user-visible string.
  - https://developer.android.com/studio/publish/versioning
- GitHub Actions can run workflows on pushed tags through `on.push.tags`.
  - https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- GitLab CI can create tag pipelines and exposes `CI_COMMIT_TAG` for tag-triggered jobs.
  - https://docs.gitlab.com/user/project/repository/tags/

## Merit of this skill

This skill is deliberately narrower and safer than a generic release tool:

- It only operates when CI/CD release automation exists.
- It prefers repository evidence over hard-coded assumptions.
- It keeps a human confirmation gate before inferred version changes and tag pushes.
- It is useful across GitHub Actions, GitLab CI, Jenkins, and other CI systems because the agent reads the repository scripts instead of requiring one new workflow.
- It helps teams that already have release automation, but still perform version bump and tag steps manually.

## Non-goals

- Do not replace Fastlane, Gradle plugins, GitHub Actions, or GitLab release jobs.
- Do not parse every possible Gradle DSL or custom build logic automatically.
- Do not push tags when CI/CD trigger evidence is absent or ambiguous.
- Do not mutate repository files from the inspection script.

