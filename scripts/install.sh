#!/usr/bin/env bash
set -euo pipefail

skill_name="android-cicd-release"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$repo_root/skill/$skill_name"
dest_root="${CODEX_HOME:-$HOME/.codex}/skills"
dest="$dest_root/$skill_name"

if [[ ! -d "$src" ]]; then
  echo "Skill source not found: $src" >&2
  exit 1
fi

mkdir -p "$dest_root"
tmp="$(mktemp -d "$dest_root/.${skill_name}.tmp.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT

cp -R "$src"/. "$tmp"/
rm -rf "$dest"
mv "$tmp" "$dest"
trap - EXIT

echo "Installed $skill_name to $dest"
echo 'Start a new Codex session and use $android-cicd-release.'
