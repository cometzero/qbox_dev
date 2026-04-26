#!/usr/bin/env bash
set -euo pipefail

target_dir=${1:?target directory required}

install -d "${target_dir}/etc"
cat > "${target_dir}/etc/qbox-release" <<'MARKER'
NAME="Apollo QBox Buildroot"
APOLLO_MACHINE="apollo_soc"
APOLLO_BOARD="apollo-qbox"
QBOX_PLATFORM="apollo_soc"
QBOX_BOOT_LANE="initramfs-apollo"
MARKER

# In the initramfs lane, static /dev/null is needed before BusyBox init can
# redirect sysinit actions, then devtmpfs must be mounted before creating
# /dev/pts and /dev/shm. Buildroot's stock inittab creates those directories
# before mount -a, which is too early once /dev is over-mounted by devtmpfs.
inittab="${target_dir}/etc/inittab"
if ! grep -q '^::sysinit:/bin/mount -t devtmpfs devtmpfs /dev$' "${inittab}"; then
  tmp_inittab="${inittab}.tmp"
  awk 'BEGIN { inserted = 0 }
       /^::sysinit:\/bin\/mkdir -p \/dev\/pts \/dev\/shm$/ && !inserted {
         print "::sysinit:/bin/mount -t devtmpfs devtmpfs /dev";
         inserted = 1
       }
       { print }
       END { if (!inserted) print "::sysinit:/bin/mount -t devtmpfs devtmpfs /dev" }' "${inittab}" > "${tmp_inittab}"
  mv "${tmp_inittab}" "${inittab}"
fi

# Avoid a duplicate devtmpfs mount from mount -a; inittab mounts it earlier.
fstab="${target_dir}/etc/fstab"
if grep -q '^devtmpfs[[:space:]]\+/dev[[:space:]]' "${fstab}"; then
  tmp_fstab="${fstab}.tmp"
  grep -v '^devtmpfs[[:space:]]\+/dev[[:space:]]' "${fstab}" > "${tmp_fstab}"
  mv "${tmp_fstab}" "${fstab}"
fi
