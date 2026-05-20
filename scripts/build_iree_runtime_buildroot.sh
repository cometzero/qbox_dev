#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
buildroot_src=${QBOX_BUILDROOT_SRC:-"${repo_root}/sources/buildroot"}
iree_src=${QBOX_IREE_SRC:-"${repo_root}/sources/iree"}
output_dir=${QBOX_BUILDROOT_OUTPUT:-"${repo_root}/build/buildroot-a710"}
dl_dir=${QBOX_BUILDROOT_DL_DIR:-"${repo_root}/build/buildroot-dl"}
ccache_dir=${QBOX_BUILDROOT_CCACHE_DIR:-"${repo_root}/build/ccache/buildroot"}
jobs=${QBOX_BUILDROOT_JOBS:-$(nproc)}
build_rootfs=0
package_target=${QBOX_IREE_RUNTIME_PACKAGE_TARGET:-iree-runtime-rebuild}

usage() {
  cat <<'USAGE'
Usage: scripts/build_iree_runtime_buildroot.sh [--rootfs]

Build the repo-local IREE runtime package for the Apollo QBox Buildroot
target. By default this builds the package only. Pass --rootfs to rebuild the
full rootfs after the package has been built.

Environment overrides:
  QBOX_IREE_SRC                  IREE source checkout (default: sources/iree)
  QBOX_IREE_INIT_SUBMODULES     0 skips runtime submodule initialization
  QBOX_IREE_RUNTIME_PACKAGE_TARGET
                                  Buildroot package target
                                  (default: iree-runtime-rebuild)
  QBOX_BUILDROOT_OUTPUT         Buildroot output directory
  QBOX_BUILDROOT_JOBS           Parallel build jobs
USAGE
}

while (($#)); do
  case "$1" in
    --rootfs)
      build_rootfs=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [[ ! -f "${buildroot_src}/Makefile" ]]; then
  echo "Buildroot source missing: ${buildroot_src}" >&2
  echo "Run: git submodule update --init --recursive sources/buildroot" >&2
  exit 1
fi

if [[ ! -f "${iree_src}/CMakeLists.txt" ]]; then
  echo "IREE source missing: ${iree_src}" >&2
  echo "Run: git submodule update --init sources/iree" >&2
  exit 1
fi

if [[ "${QBOX_IREE_INIT_SUBMODULES:-1}" != 0 ]]; then
  mapfile -t runtime_submodules < <(
    sed '/^[[:space:]]*$/d' "${iree_src}/build_tools/scripts/git/runtime_submodules.txt"
  )
  git -C "${iree_src}" submodule update --init --depth 1 "${runtime_submodules[@]}"
fi

"${repo_root}/scripts/build_qbox_buildroot_arm64.sh" --config-only

make -C "${buildroot_src}" \
  O="${output_dir}" \
  BR2_DL_DIR="${dl_dir}" \
  BR2_CCACHE_DIR="${ccache_dir}" \
  "${package_target}" \
  -j"${jobs}"

runner="${output_dir}/target/usr/bin/iree-run-module"
real_runner="${output_dir}/target/usr/libexec/qbox/iree-run-module.real"
apollo_runner="${output_dir}/target/usr/bin/apollo-iree-run-module"
apollo_plugin="${output_dir}/target/usr/lib/qbox/libapollo_iree_hexagon_hal_plugin.so"
if [[ ! -x "${runner}" ]]; then
  echo "IREE runtime package did not install ${runner}" >&2
  exit 1
fi
for path in "${real_runner}" "${apollo_runner}" "${apollo_plugin}"; do
  if [[ ! -x "${path}" ]]; then
    echo "IREE runtime package did not install Apollo frontend artifact: ${path}" >&2
    exit 1
  fi
done

file "${runner}"
file "${real_runner}"
file "${apollo_runner}"
file "${apollo_plugin}"

if ((build_rootfs)); then
  "${repo_root}/scripts/build_qbox_buildroot_arm64.sh"
fi

cat <<EOF
IREE runtime package built: ${runner}
IREE source-built runner: ${real_runner}
Apollo Hexagon registry frontend: ${apollo_runner}
Apollo Hexagon HAL plugin: ${apollo_plugin}
Rootfs inclusion: BR2_PACKAGE_IREE_RUNTIME=y in apollo_qbox_defconfig
Full rootfs build command:
  ./scripts/build_iree_runtime_buildroot.sh --rootfs
EOF
