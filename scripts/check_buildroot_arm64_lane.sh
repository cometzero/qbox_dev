#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

pass() { printf 'PASS: %s\n' "$1"; }
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

require_file() {
  local path=$1 label=$2
  [[ -f "${path}" ]] || fail "missing ${label}: ${path}"
  pass "${label} exists"
}

forbid_file() {
  local path=$1 label=$2
  [[ ! -e "${path}" ]] || fail "${label} unexpectedly present: ${path}"
  pass "${label} absent"
}

require_executable() {
  local path=$1 label=$2
  [[ -x "${path}" ]] || fail "missing executable ${label}: ${path}"
  pass "${label} is executable"
}

require_grep() {
  local pattern=$1 path=$2 label=$3
  grep -Eq -- "${pattern}" "${path}" || fail "${label} not found in ${path}"
  pass "${label} present"
}

forbid_grep() {
  local pattern=$1 path=$2 label=$3
  if grep -Eq -- "${pattern}" "${path}"; then
    fail "${label} unexpectedly present in ${path}"
  fi
  pass "${label} absent"
}

require_submodule() {
  local name=$1 label=$2 submodule_path
  submodule_path=$(git -C "${repo_root}" config -f .gitmodules --get "submodule.${name}.path") \
    || fail "${label} missing from .gitmodules"
  [[ -e "${repo_root}/${submodule_path}/.git" ]] || fail "${label} checkout missing at ${submodule_path}"
  pass "${label} registered at ${submodule_path} and checked out"
}

require_submodule qbox "QBox submodule"
require_submodule sources/buildroot "Buildroot source submodule"
require_submodule sources/linux "Linux source submodule"
require_submodule sources/qemu "libqemu/QEMU source submodule"

require_grep 'branch = 2026\.02\.1' "${repo_root}/.gitmodules" "Buildroot 2026.02.1 pin"
require_grep 'submodule\.sources/linux\.branch feature/qbox_dev' <(git config --file "${repo_root}/.gitmodules" --get-regexp 'submodule\.sources/linux\.branch') "Linux qbox_dev branch pin"
require_grep 'submodule\.sources/qemu\.branch feature/qbox_dev' <(git config --file "${repo_root}/.gitmodules" --get-regexp 'submodule\.sources/qemu\.branch') "QEMU qbox_dev branch pin"
require_grep 'submodule\.sources/buildroot\.shallow false' <(git config --file "${repo_root}/.gitmodules" --get-regexp 'submodule\.sources/buildroot\.shallow') "Buildroot full-history submodule setting"
require_grep 'submodule\.sources/linux\.shallow false' <(git config --file "${repo_root}/.gitmodules" --get-regexp 'submodule\.sources/linux\.shallow') "Linux full-history submodule setting"
require_grep 'submodule\.sources/qemu\.shallow false' <(git config --file "${repo_root}/.gitmodules" --get-regexp 'submodule\.sources/qemu\.shallow') "QEMU full-history submodule setting"

external="${repo_root}/configs/buildroot/external/apollo_qbox"
board="${external}/board/apollo/apollo-qbox"
defconfig="${external}/configs/apollo_qbox_defconfig"
linux_config="${repo_root}/configs/linux/linux.config"
linux_dts="${repo_root}/configs/linux/apollo_soc.dts"
require_file "${external}/external.desc" "BR2_EXTERNAL descriptor"
require_file "${external}/Config.in" "BR2_EXTERNAL Config.in"
require_file "${external}/external.mk" "BR2_EXTERNAL external.mk"
require_file "${defconfig}" "Apollo QBox Buildroot defconfig"
require_file "${linux_config}" "standalone Linux config fragment"
require_file "${board}/device_table.txt" "early device node table"
require_file "${linux_dts}" "Apollo QBox DTS template"
require_file "${board}/genimage.cfg" "future ext4 genimage config"
forbid_file "${board}/linux.config" "Linux config under Buildroot board"
forbid_file "${board}/apollo_soc.dts" "Linux DTS under Buildroot board"
require_executable "${board}/post-build.sh" "post-build hook"
require_executable "${board}/post-image.sh" "post-image hook"
require_executable "${repo_root}/scripts/build_qbox_buildroot_arm64.sh" "Buildroot rootfs build script"
require_executable "${repo_root}/scripts/build_qbox_linux_arm64.sh" "standalone Linux build script"
require_executable "${repo_root}/scripts/stage_buildroot_artifacts.sh" "artifact staging script"
require_executable "${repo_root}/scripts/check_qbox_hexagon_smmu_reference.sh" "QBox Hexagon SMMU reference preflight script"

require_grep '^BR2_aarch64=y$' "${defconfig}" "AArch64 target"
require_grep '^BR2_cortex_a710=y$' "${defconfig}" "Cortex-A710 target tuning"
require_grep '^BR2_CCACHE=y$' "${defconfig}" "Buildroot ccache"
require_grep '^BR2_TARGET_ROOTFS_CPIO=y$' "${defconfig}" "CPIO initramfs"
require_grep 'BR2_ROOTFS_DEVICE_TABLE=.*device_table\.txt' "${defconfig}" "early device table configured"
require_grep 'BR2_ROOTFS_POST_IMAGE_SCRIPT_ARGS=.*\.\./\.\./\.\./linux/apollo_soc\.dts' "${defconfig}" "external Linux DTS configured"
require_grep '^BR2_PACKAGE_HOST_DTC=y$' "${defconfig}" "host dtc"
forbid_grep '^BR2_LINUX_KERNEL' "${defconfig}" "Buildroot kernel build options"
forbid_grep 'sources/linux|linux-v7\.0|QBOX_LINUX' "${repo_root}/scripts/build_qbox_buildroot_arm64.sh" "Linux coupling in Buildroot script"
require_grep 'linux_src=\$\{QBOX_LINUX_SRC:-"\$\{repo_root\}/sources/linux"\}' "${repo_root}/scripts/build_qbox_linux_arm64.sh" "Linux source submodule usage"
require_grep 'configs/linux/linux\.config' "${repo_root}/scripts/build_qbox_linux_arm64.sh" "Linux config fragment location"
require_grep 'toolchain_prefix=\$\{QBOX_LINUX_CROSS_COMPILE:-"\$\{buildroot_output\}/host/bin/aarch64-buildroot-linux-gnu-"\}' "${repo_root}/scripts/build_qbox_linux_arm64.sh" "Buildroot toolchain reuse"
require_grep 'linux_cross_compile="\$\{ccache_bin\} \$\{toolchain_prefix\}"' "${repo_root}/scripts/build_qbox_linux_arm64.sh" "Linux ccache launcher"
require_grep 'Image \\' "${repo_root}/scripts/build_qbox_linux_arm64.sh" "standalone Linux Image target"
require_grep 'linux_image=\$\{QBOX_LINUX_IMAGE:-"\$\{linux_output\}/arch/arm64/boot/Image"\}' "${repo_root}/scripts/stage_buildroot_artifacts.sh" "staging uses standalone Linux Image"
require_grep 'linux,initrd-start = <0x0 __INITRD_START__>' "${linux_dts}" "post-image initrd start placeholder"
require_grep 'compatible = "arm,cortex-a710"' "${linux_dts}" "A710 CPU compatible"
require_grep 'reserved-memory' "${linux_dts}" "future SRAM reservations"
require_grep 'compatible = "arm,smmu-v3"' "${linux_dts}" "ARM SMMUv3 node"
require_grep '#iommu-cells = <0x1>' "${linux_dts}" "SMMUv3 iommu cells"
require_grep 'compatible = "apollo,hexagon-ip"' "${linux_dts}" "Apollo Hexagon device node"
require_grep 'iommus = <&smmu 0x1>' "${linux_dts}" "Hexagon device behind SMMUv3"
require_grep 'apollo,dma-path = "direct-tlm"' "${linux_dts}" "Hexagon DMA path contract"
require_grep 'apollo,smmu-stream-id = <0x1>' "${linux_dts}" "Hexagon SMMU StreamID contract"
require_grep 'memory-region-names = "firmware", "dma-test"' "${linux_dts}" "Hexagon firmware and DMA-test SRAM bindings"
require_grep '^CONFIG_ARM_SMMU_V3=y$' "${linux_config}" "Linux SMMUv3 driver"
require_grep '^CONFIG_APOLLO_HEXAGON_TEST=y$' "${linux_config}" "Apollo Hexagon test driver"
require_file "${repo_root}/sources/linux/drivers/soc/apollo/Kconfig" "Apollo Linux SoC Kconfig"
require_file "${repo_root}/sources/linux/drivers/soc/apollo/apollo-hexagon-test.c" "Apollo Hexagon Linux driver"
require_grep 'firmware dma traffic ok' "${repo_root}/sources/linux/drivers/soc/apollo/apollo-hexagon-test.c" "Linux firmware-DMA traffic check"
require_grep 'dma path direct-tlm' "${repo_root}/sources/linux/drivers/soc/apollo/apollo-hexagon-test.c" "Linux DMA path ABI check"
require_grep 'kernel_build": "external:sources/linux"' "${board}/post-image.sh" "post-image records external kernel ownership"
require_grep 'mount -t devtmpfs devtmpfs /dev' "${board}/post-build.sh" "post-build early devtmpfs mount entry"
require_grep '/dev/ttyAMA0[[:space:]]+c[[:space:]]+660' "${board}/device_table.txt" "static ttyAMA0 fallback node"

qbox_root="${repo_root}/sources/qbox"
platform="${qbox_root}/platforms/buildroot/conf_aarch64.lua"
hexagon_smmu_cmake="${qbox_root}/tests/qbox/cpu/hexagon/CMakeLists.txt"
hexagon_smmu_readme="${qbox_root}/tests/qbox/cpu/hexagon/HEXAGON_SMMU_README.md"
require_file "${platform}" "QBox Buildroot AArch64 platform"
require_file "${hexagon_smmu_cmake}" "QBox Hexagon SMMU reference CMake"
require_file "${hexagon_smmu_readme}" "QBox Hexagon SMMU reference README"
require_file "${qbox_root}/platforms/buildroot/fw/arm64_bootloader.lua" "Buildroot ARM64 bootloader stub"
require_file "${qbox_root}/platforms/buildroot/fw/Artifacts/.gitignore" "artifact directory gitignore"
require_grep 'ARM_NUM_CPUS = 4' "${platform}" "4 Cortex-A710 CPUs"
require_grep 'cpu_arm_cortexA710' "${platform}" "Apollo QBox Cortex-A710 module"
require_grep 'apollo_soc\.dtb' "${platform}" "Buildroot DTB artifact"
require_grep 'rootfs\.cpio' "${platform}" "Buildroot initramfs artifact"
require_grep 'math\.floor\(i / 2\) << 8' "${platform}" "2x2 cluster mp_affinity mapping"
require_grep 'moduletype = "keep_alive"' "${platform}" "QBox simulation keep-alive component"
require_grep 'moduletype = "arm_smmuv3"' "${platform}" "QBox SMMUv3 component"
require_grep 'moduletype = "qemu_cpu_hexagon"' "${platform}" "QBox Hexagon CPU component"

require_grep 'moduletype = "apollo_hexagon_dma"' "${platform}" "QBox Apollo Hexagon DMA component"
require_grep 'stream_id = APOLLO_HEXAGON_STREAM_ID' "${platform}" "QBox Apollo Hexagon DMA StreamID"
require_grep 'smmu_translated = false' "${platform}" "QBox Apollo Hexagon direct-DMA contract"
require_grep 'start_powered_off = false' "${platform}" "QBox Hexagon firmware boot enabled"
require_grep 'APOLLO_HEXAGON_BOOT_ALIAS' "${platform}" "QBox Hexagon boot alias"
require_grep 'aliases=\{\{address=APOLLO_HEXAGON_BOOT_ALIAS' "${platform}" "QBox Hexagon SRAM boot alias mapping"
require_grep 'apollo_hexagon_dma\.bin' "${platform}" "QBox Hexagon firmware loader entry"
require_grep 'apollo_hexagon_dma' "${repo_root}/scripts/build_qbox_buildroot_platform.sh" "QBox Apollo Hexagon DMA build target"
require_grep 'apollo_hexagon_dma\.so' "${repo_root}/scripts/run_qbox_buildroot_boot.sh" "QBox Apollo Hexagon DMA runtime module check"
require_grep 'build_qbox_hexagon_firmware\.sh' "${repo_root}/scripts/stage_buildroot_artifacts.sh" "Hexagon firmware staging hook"
require_grep 'moduletype = "hexagon_globalreg"' "${platform}" "QBox Hexagon global register component"
require_grep 'APOLLO_HEXAGON_SRAM' "${platform}" "QBox Hexagon SRAM mapping"
require_grep 'libqemu_src=\$\{QBOX_LIBQEMU_SRC:-"\$\{repo_root\}/sources/qemu"\}' "${repo_root}/scripts/build_qbox_buildroot_platform.sh" "QBox local libqemu source override"
require_grep 'libqemu_targets=\$\{QBOX_LIBQEMU_TARGETS:-"aarch64;hexagon"\}' "${repo_root}/scripts/build_qbox_buildroot_platform.sh" "QBox AArch64 and Hexagon libqemu targets"
require_grep 'CPM_libqemu_SOURCE="\$\{libqemu_src\}"' "${repo_root}/scripts/build_qbox_buildroot_platform.sh" "QBox CPM libqemu source override"
require_grep 'CMAKE_C_COMPILER_LAUNCHER="\$\{ccache_bin\}"' "${repo_root}/scripts/build_qbox_buildroot_platform.sh" "QBox C ccache launcher"
require_grep 'CMAKE_CXX_COMPILER_LAUNCHER="\$\{ccache_bin\}"' "${repo_root}/scripts/build_qbox_buildroot_platform.sh" "QBox CXX ccache launcher"
require_grep 'keep_alive' "${repo_root}/scripts/build_qbox_buildroot_platform.sh" "QBox keep_alive build target"
require_grep 'keep_alive\.so' "${repo_root}/scripts/run_qbox_buildroot_boot.sh" "QBox keep_alive runtime module check"
require_grep 'arm_smmuv3' "${repo_root}/scripts/build_qbox_buildroot_platform.sh" "QBox SMMUv3 build target"
require_grep 'qemu_cpu_hexagon' "${repo_root}/scripts/build_qbox_buildroot_platform.sh" "QBox Hexagon build target"
require_grep 'arm_smmuv3\.so' "${repo_root}/scripts/run_qbox_buildroot_boot.sh" "QBox SMMUv3 runtime module check"
require_grep 'qemu_cpu_hexagon\.so' "${repo_root}/scripts/run_qbox_buildroot_boot.sh" "QBox Hexagon runtime module check"
require_grep 'QBOX_BOOT_NETDEV_STR' "${platform}" "QBox Apollo netdev runtime override"
require_grep 'QBOX_BOOT_HOSTFWD' "${repo_root}/scripts/run_qbox_buildroot_boot.sh" "QBox boot hostfwd conflict policy"
require_grep 'CAP_DIRECT_TLM' "${qbox_root}/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h" "QBox Apollo Hexagon DMA direct path capability"
require_grep 'CAP_SMMU_TRANSLATED' "${qbox_root}/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h" "QBox Apollo Hexagon DMA future translated capability"
require_grep 'translated_dma' "${qbox_root}/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h" "QBox Apollo Hexagon DMA translated path seam"
require_grep 'HEXAGON_SMMU_MCPU "hexagonv68"' "${hexagon_smmu_cmake}" "QBox Hexagon SMMU v68 firmware target"
require_grep '-mcpu=\$\{HEXAGON_SMMU_MCPU\}' "${hexagon_smmu_cmake}" "QBox Hexagon SMMU CMake mcpu usage"
require_grep '-mcpu="\$\{mcpu\}"' "${repo_root}/scripts/check_qbox_hexagon_smmu_reference.sh" "QBox Hexagon SMMU preflight mcpu usage"
require_grep 'Hexagon v68 or later' "${hexagon_smmu_readme}" "QBox Hexagon SMMU v68 README note"

if git -C "${qbox_root}" ls-files --error-unmatch platforms/buildroot/fw/Artifacts/Image.bin >/dev/null 2>&1; then
  fail "generated Image.bin must not be tracked"
fi
pass "generated boot artifacts are not tracked in qbox"

printf '\nLane conclusion: Buildroot owns rootfs/DTB generation only; Linux Image comes from sources/linux, and libqemu comes from sources/qemu.\n'
