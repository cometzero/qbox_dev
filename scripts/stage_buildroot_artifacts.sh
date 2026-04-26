#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
buildroot_output=${QBOX_BUILDROOT_OUTPUT:-"${repo_root}/build/buildroot-a710"}
buildroot_images=${QBOX_BUILDROOT_IMAGES:-"${buildroot_output}/images"}
linux_output=${QBOX_LINUX_OUTPUT:-"${repo_root}/build/linux-a710"}
linux_image=${QBOX_LINUX_IMAGE:-"${linux_output}/arch/arm64/boot/Image"}
artifacts_dir=${QBOX_BUILDROOT_ARTIFACTS:-"${repo_root}/sources/qbox/platforms/buildroot/fw/Artifacts"}

require_artifact() {
  local path=$1
  if [[ ! -s "${path}" ]]; then
    echo "missing or empty artifact: ${path}" >&2
    exit 1
  fi
}

require_artifact "${linux_image}"
require_artifact "${buildroot_images}/apollo_soc.dtb"
require_artifact "${buildroot_images}/rootfs.cpio"

rm -f \
  "${artifacts_dir}/qbox_a710_soc.dtb" \
  "${artifacts_dir}/qbox-a710-staged-artifacts.json"

install -D -m 0644 "${linux_image}" "${artifacts_dir}/Image.bin"
install -D -m 0644 "${buildroot_images}/apollo_soc.dtb" "${artifacts_dir}/apollo_soc.dtb"
install -D -m 0644 "${buildroot_images}/rootfs.cpio" "${artifacts_dir}/rootfs.cpio"

manifest="${artifacts_dir}/apollo-qbox-staged-artifacts.json"
cat > "${manifest}" <<JSON
{
  "linux_image_source": "${linux_image}",
  "buildroot_images_dir": "${buildroot_images}",
  "artifacts_dir": "${artifacts_dir}",
  "Image.bin": $(stat -c '%s' "${artifacts_dir}/Image.bin"),
  "apollo_soc.dtb": $(stat -c '%s' "${artifacts_dir}/apollo_soc.dtb"),
  "rootfs.cpio": $(stat -c '%s' "${artifacts_dir}/rootfs.cpio")
}
JSON

echo "Staged Linux + Buildroot artifacts into ${artifacts_dir}"
