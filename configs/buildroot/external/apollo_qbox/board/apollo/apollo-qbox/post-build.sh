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

interfaces="${target_dir}/etc/network/interfaces"
if [[ -f "${interfaces}" ]] && ! grep -q '^auto eth0$' "${interfaces}"; then
  cat >> "${interfaces}" <<'MARKER'

auto eth0
iface eth0 inet dhcp
MARKER
fi

set_sshd_config() {
  local file=$1 key=$2 value=$3 tmp_file

  tmp_file="${file}.tmp"
  if grep -Eq "^[#[:space:]]*${key}[[:space:]]+" "${file}"; then
    sed -E "s|^[#[:space:]]*${key}[[:space:]].*|${key} ${value}|" \
      "${file}" > "${tmp_file}"
  else
    cp "${file}" "${tmp_file}"
    printf '%s %s\n' "${key}" "${value}" >> "${tmp_file}"
  fi
  mv "${tmp_file}" "${file}"
}

sshd_config="${target_dir}/etc/ssh/sshd_config"
if [[ -f "${sshd_config}" ]]; then
  set_sshd_config "${sshd_config}" PermitRootLogin yes
  set_sshd_config "${sshd_config}" PasswordAuthentication yes
  set_sshd_config "${sshd_config}" PermitEmptyPasswords yes
fi

iree_guest_artifacts_dir=${QBOX_IREE_GUEST_ARTIFACTS_DIR:-}
if [[ -n "${iree_guest_artifacts_dir}" ]]; then
  if [[ ! -d "${iree_guest_artifacts_dir}" ]]; then
    echo "QBOX_IREE_GUEST_ARTIFACTS_DIR is not a directory: ${iree_guest_artifacts_dir}" >&2
    exit 1
  fi

  install -d "${target_dir}/opt/qbox/iree/tiny-cnn"
  cp -a "${iree_guest_artifacts_dir}/." "${target_dir}/opt/qbox/iree/tiny-cnn/"
  cat > "${target_dir}/opt/qbox/iree/README" <<'MARKER'
This image contains optional Apollo QBox IREE tiny-CNN guest artifacts.

The default minimal image does not include IREE artifacts. When this directory
is present, run:

  /opt/qbox/iree/tiny-cnn/run_tiny_cnn_guest.sh
MARKER
fi

iree_vector_add_guest_artifacts_dir=${QBOX_IREE_VECTOR_ADD_GUEST_ARTIFACTS_DIR:-}
if [[ -n "${iree_vector_add_guest_artifacts_dir}" ]]; then
  if [[ ! -d "${iree_vector_add_guest_artifacts_dir}" ]]; then
    echo "QBOX_IREE_VECTOR_ADD_GUEST_ARTIFACTS_DIR is not a directory: ${iree_vector_add_guest_artifacts_dir}" >&2
    exit 1
  fi

  install -d "${target_dir}/opt/qbox/iree/vector-add"
  cp -a "${iree_vector_add_guest_artifacts_dir}/." "${target_dir}/opt/qbox/iree/vector-add/"
  cat > "${target_dir}/opt/qbox/iree/vector-add/README" <<'MARKER'
This image contains optional Apollo QBox IREE vector-add guest artifacts.

Run:

  /opt/qbox/iree/vector-add/run_vector_add_hexagon_guest.sh
MARKER
fi

iree_mnist_guest_artifacts_dir=${QBOX_IREE_MNIST_GUEST_ARTIFACTS_DIR:-}
if [[ -n "${iree_mnist_guest_artifacts_dir}" ]]; then
  if [[ ! -d "${iree_mnist_guest_artifacts_dir}" ]]; then
    echo "QBOX_IREE_MNIST_GUEST_ARTIFACTS_DIR is not a directory: ${iree_mnist_guest_artifacts_dir}" >&2
    exit 1
  fi

  install -d "${target_dir}/opt/qbox/iree/mnist"
  cp -a "${iree_mnist_guest_artifacts_dir}/." "${target_dir}/opt/qbox/iree/mnist/"
  cat > "${target_dir}/opt/qbox/iree/mnist/README" <<'MARKER'
This image contains optional Apollo QBox IREE MNIST-like guest artifacts.

Run:

  /opt/qbox/iree/mnist/run_mnist_apko_hexagon_guest.sh
MARKER
fi
