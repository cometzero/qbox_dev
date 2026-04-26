#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
buildroot_src=${QBOX_BUILDROOT_SRC:-"${repo_root}/sources/buildroot"}
external_tree=${QBOX_BUILDROOT_EXTERNAL:-"${repo_root}/configs/buildroot/external/apollo_qbox"}
output_dir=${QBOX_BUILDROOT_OUTPUT:-"${repo_root}/build/buildroot-a710"}
dl_dir=${QBOX_BUILDROOT_DL_DIR:-"${repo_root}/build/buildroot-dl"}
ccache_dir=${QBOX_BUILDROOT_CCACHE_DIR:-"${repo_root}/build/ccache/buildroot"}
jobs=${QBOX_BUILDROOT_JOBS:-$(nproc)}

if [[ ! -f "${buildroot_src}/Makefile" ]]; then
  echo "Buildroot source missing: ${buildroot_src}" >&2
  echo "Run: git submodule update --init --recursive sources/buildroot" >&2
  exit 1
fi

mkdir -p "${dl_dir}" "${ccache_dir}"
export BR2_CCACHE_DIR="${ccache_dir}"

make -C "${buildroot_src}" \
  O="${output_dir}" \
  BR2_EXTERNAL="${external_tree}" \
  BR2_DL_DIR="${dl_dir}" \
  apollo_qbox_defconfig

if [[ "${1:-}" == "--config-only" ]]; then
  echo "Configured Buildroot rootfs-only output: ${output_dir}"
  echo "Buildroot ccache dir: ${BR2_CCACHE_DIR}"
  exit 0
fi

make -C "${buildroot_src}" O="${output_dir}" BR2_DL_DIR="${dl_dir}" -j"${jobs}"

echo "Buildroot rootfs/DTB images: ${output_dir}/images"
echo "Buildroot ccache dir: ${BR2_CCACHE_DIR}"
