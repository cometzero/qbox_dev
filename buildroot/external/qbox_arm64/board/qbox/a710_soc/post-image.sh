#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: ${0##*/} <images-dir> <qbox_a710_soc.dts>" >&2
  echo "Buildroot invokes this as: post-image.sh \\"\${BINARIES_DIR}\\" <dts>" >&2
  exit 2
fi

images_dir=$1
dts_template=$2
rootfs_cpio="${images_dir}/rootfs.cpio"
dtb_out="${images_dir}/qbox_a710_soc.dtb"
manifest_out="${images_dir}/qbox-a710-artifacts.json"

if [[ ! -s "${rootfs_cpio}" ]]; then
  echo "missing rootfs cpio: ${rootfs_cpio}" >&2
  exit 1
fi
if [[ ! -s "${dts_template}" ]]; then
  echo "missing DTS template: ${dts_template}" >&2
  exit 1
fi

initrd_start=$((0x8A800000))
rootfs_size=$(stat -c '%s' "${rootfs_cpio}")
initrd_end=$((initrd_start + rootfs_size))
initrd_start_hex=$(printf '0x%08x' "${initrd_start}")
initrd_end_hex=$(printf '0x%08x' "${initrd_end}")

generated_dts="${images_dir}/qbox_a710_soc.generated.dts"
sed \
  -e "s/__INITRD_START__/${initrd_start_hex}/g" \
  -e "s/__INITRD_END__/${initrd_end_hex}/g" \
  "${dts_template}" > "${generated_dts}"

DTC=${DTC:-${HOST_DIR:-}/bin/dtc}
if [[ ! -x "${DTC}" ]]; then
  DTC=$(command -v dtc || true)
fi
if [[ -z "${DTC}" || ! -x "${DTC}" ]]; then
  echo "dtc not found; enable BR2_PACKAGE_HOST_DTC or install dtc" >&2
  exit 1
fi

"${DTC}" -I dts -O dtb -o "${dtb_out}" "${generated_dts}"

cat > "${manifest_out}" <<JSON
{
  "platform": "qbox_a710_soc",
  "dtb": "${dtb_out}",
  "rootfs_cpio": "${rootfs_cpio}",
  "rootfs_cpio_size": ${rootfs_size},
  "initrd_start": "${initrd_start_hex}",
  "initrd_end": "${initrd_end_hex}",
  "dts": "${generated_dts}",
  "kernel_build": "external:sources/linux"
}
JSON

echo "Generated ${dtb_out} with initrd [${initrd_start_hex}, ${initrd_end_hex})"
