#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
hook_src="${repo_root}/scripts/git-hooks/commit-msg"
repos=(
  "."
  "sources/qbox"
  "sources/qemu"
  "sources/linux"
)

if [[ ! -x "${hook_src}" ]]; then
  echo "commit-msg hook source is missing or not executable: ${hook_src}" >&2
  exit 1
fi

echo "Codex agents should create commits through the commit-atomic skill."

for repo in "${repos[@]}"; do
  repo_path="${repo_root}/${repo}"
  if [[ ! -d "${repo_path}" ]]; then
    echo "SKIP: ${repo} is not checked out" >&2
    continue
  fi
  if ! git -C "${repo_path}" rev-parse --git-dir >/dev/null 2>&1; then
    echo "SKIP: ${repo} is not a git repository" >&2
    continue
  fi

  hook_path=$(git -C "${repo_path}" rev-parse --git-path hooks/commit-msg)
  mkdir -p "$(dirname "${hook_path}")"

  if [[ -e "${hook_path}" && ! -L "${hook_path}" ]]; then
    backup="${hook_path}.bak.$(date +%Y%m%d%H%M%S)"
    mv "${hook_path}" "${backup}"
    echo "BACKUP: ${repo} existing hook -> ${backup}"
  fi

  ln -sfn "${hook_src}" "${hook_path}"
  echo "INSTALLED: ${repo} -> ${hook_path}"
done
