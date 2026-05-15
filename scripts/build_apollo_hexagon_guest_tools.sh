#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
buildroot_output=${QBOX_BUILDROOT_OUTPUT:-"${repo_root}/build/buildroot-a710"}
toolchain_prefix=${QBOX_LINUX_CROSS_COMPILE:-"${buildroot_output}/host/bin/aarch64-buildroot-linux-gnu-"}
out_dir=${QBOX_APOLLO_HEXAGON_TOOLS_OUT:-"${repo_root}/build/apollo-hexagon-guest-tools"}
src_dir="${repo_root}/configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools"
runner="${out_dir}/bin/apollo-iree-hexagon-runner"
registry_runner="${out_dir}/bin/apollo-iree-run-module"
plugin="${out_dir}/lib/libapollo_iree_hexagon_hal_plugin.so"
host_registry_runner="${out_dir}/host-bin/apollo-iree-run-module"

if [[ ! -x "${toolchain_prefix}gcc" ]]; then
  echo "Buildroot cross compiler missing: ${toolchain_prefix}gcc" >&2
  echo "Run: ./scripts/build_qbox_buildroot_arm64.sh" >&2
  exit 1
fi

mkdir -p "${out_dir}/bin" "${out_dir}/lib" "${out_dir}/host-bin"
"${toolchain_prefix}gcc" \
  -Os \
  -Wall \
  -Wextra \
  -Werror \
  -I"${src_dir}" \
  "${src_dir}/apollo_iree_hexagon_runner.c" \
  "${src_dir}/apollo_iree_hexagon_hal.c" \
  -ldl \
  -o "${runner}"

"${toolchain_prefix}gcc" \
  -Os \
  -Wall \
  -Wextra \
  -Werror \
  -I"${src_dir}" \
  "${src_dir}/apollo_iree_run_module.c" \
  "${src_dir}/apollo_iree_hal_registry.c" \
  "${src_dir}/apollo_iree_hexagon_hal.c" \
  -ldl \
  -o "${registry_runner}"

"${toolchain_prefix}gcc" \
  -Os \
  -Wall \
  -Wextra \
  -Werror \
  -fPIC \
  -shared \
  -I"${src_dir}" \
  "${src_dir}/apollo_iree_hexagon_plugin.c" \
  "${src_dir}/apollo_iree_hexagon_hal.c" \
  -o "${plugin}"

gcc \
  -Os \
  -Wall \
  -Wextra \
  -Werror \
  -I"${src_dir}" \
  "${src_dir}/apollo_iree_run_module.c" \
  "${src_dir}/apollo_iree_hal_registry.c" \
  "${src_dir}/apollo_iree_hexagon_hal.c" \
  -ldl \
  -o "${host_registry_runner}"

if [[ ! -s "${runner}" ]]; then
  echo "failed to build Apollo Hexagon guest runner: ${runner}" >&2
  exit 1
fi
if [[ ! -s "${registry_runner}" ]]; then
  echo "failed to build Apollo Hexagon HAL registry runner: ${registry_runner}" >&2
  exit 1
fi
if [[ ! -s "${plugin}" ]]; then
  echo "failed to build Apollo Hexagon HAL plugin: ${plugin}" >&2
  exit 1
fi
if [[ ! -s "${host_registry_runner}" ]]; then
  echo "failed to build host Apollo Hexagon HAL registry runner: ${host_registry_runner}" >&2
  exit 1
fi

file "${runner}"
file "${registry_runner}"
file "${plugin}"
file "${host_registry_runner}"
echo "Apollo Hexagon guest runner: ${runner}"
echo "Apollo Hexagon HAL registry runner: ${registry_runner}"
echo "Apollo Hexagon HAL plugin: ${plugin}"
echo "Host Apollo Hexagon HAL registry runner: ${host_registry_runner}"
