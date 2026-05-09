#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
buildroot_output=${QBOX_BUILDROOT_OUTPUT:-"${repo_root}/build/buildroot-a710"}
toolchain_prefix=${QBOX_LINUX_CROSS_COMPILE:-"${buildroot_output}/host/bin/aarch64-buildroot-linux-gnu-"}
out_dir=${QBOX_APOLLO_HEXAGON_TOOLS_OUT:-"${repo_root}/build/apollo-hexagon-guest-tools"}
src="${repo_root}/configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hexagon_runner.c"
runner="${out_dir}/bin/apollo-iree-hexagon-runner"

if [[ ! -x "${toolchain_prefix}gcc" ]]; then
  echo "Buildroot cross compiler missing: ${toolchain_prefix}gcc" >&2
  echo "Run: ./scripts/build_qbox_buildroot_arm64.sh" >&2
  exit 1
fi

mkdir -p "${out_dir}/bin"
"${toolchain_prefix}gcc" \
  -Os \
  -Wall \
  -Wextra \
  -Werror \
  "${src}" \
  -o "${runner}"

if [[ ! -s "${runner}" ]]; then
  echo "failed to build Apollo Hexagon guest runner: ${runner}" >&2
  exit 1
fi

file "${runner}"
echo "Apollo Hexagon guest runner: ${runner}"
