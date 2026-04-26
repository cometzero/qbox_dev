#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
qbox_root=${QBOX_ROOT:-"${repo_root}/sources/qbox"}
fw_src="${qbox_root}/tests/qbox/cpu/hexagon/hexagon_smmu_firmware.s"
fw_ld="${qbox_root}/tests/qbox/cpu/hexagon/hexagon_smmu_firmware.ld"
out_dir=${QBOX_HEXAGON_SMMU_CHECK_DIR:-"${repo_root}/build/verification/hexagon-smmu-reference"}
mcpu=${QBOX_HEXAGON_SMMU_MCPU:-hexagonv68}
strict=0
if [[ "${1:-}" == "--strict" ]]; then
  strict=1
fi

mkdir -p "${out_dir}"

print_tool() {
  local tool=$1
  local path
  path=$(command -v "${tool}" || true)
  if [[ -n "${path}" ]]; then
    printf 'TOOL %-18s %s\n' "${tool}" "${path}"
  else
    printf 'TOOL %-18s missing\n' "${tool}"
  fi
}

printf 'Hexagon SMMU reference preflight\n'
printf 'README: %s\n' "${qbox_root}/tests/qbox/cpu/hexagon/HEXAGON_SMMU_README.md"
printf 'Firmware: %s\n' "${fw_src}"
printf 'MCPU: %s\n' "${mcpu}"
printf 'Output: %s\n' "${out_dir}"

for tool in llvm-mc ld.lld llvm-objcopy llvm-objdump hexagon-clang hexagon-as hexagon-objcopy hexagon-objdump; do
  print_tool "${tool}"
done

if [[ ! -f "${fw_src}" || ! -f "${fw_ld}" ]]; then
  printf 'STATUS missing_reference_files\n'
  exit 1
fi

llvm_mc=$(command -v llvm-mc || true)
ld_lld=$(command -v ld.lld || true)
llvm_objcopy=$(command -v llvm-objcopy || true)
llvm_objdump=$(command -v llvm-objdump || true)

if [[ -z "${llvm_mc}" || -z "${ld_lld}" || -z "${llvm_objcopy}" ]]; then
  printf 'STATUS blocked_missing_llvm_tools\n'
  [[ "${strict}" == "1" ]] && exit 2 || exit 0
fi

obj="${out_dir}/hexagon_smmu_firmware.o"
elf="${out_dir}/hexagon_smmu_firmware.elf"
bin="${out_dir}/hexagon_smmu_firmware.bin"
asm_log="${out_dir}/llvm-mc.log"
link_log="${out_dir}/ld-lld.log"
objcopy_log="${out_dir}/llvm-objcopy.log"

set +e
"${llvm_mc}" -arch=hexagon -mcpu="${mcpu}" -filetype=obj "${fw_src}" -o "${obj}" >"${asm_log}" 2>&1
asm_rc=$?
set -e
if [[ "${asm_rc}" != "0" ]]; then
  printf 'STATUS blocked_llvm_hexagon_mcpu_or_syntax\n'
  printf 'DETAIL llvm-mc failed to assemble tlbw/dmwait/dmlink firmware for %s; see %s\n' "${mcpu}" "${asm_log}"
  sed -n '1,80p' "${asm_log}" | sed 's/^/ASM: /'
  [[ "${strict}" == "1" ]] && exit 2 || exit 0
fi

set +e
"${ld_lld}" -T "${fw_ld}" "${obj}" -o "${elf}" \
  --defsym TESTER_ADDR=0x40000 \
  --defsym REG_DEBUG=0x28 \
  --defsym PAGE_SIZE=0x1000 >"${link_log}" 2>&1
link_rc=$?
set -e
if [[ "${link_rc}" != "0" ]]; then
  printf 'STATUS blocked_link\n'
  printf 'DETAIL ld.lld failed; see %s\n' "${link_log}"
  sed -n '1,80p' "${link_log}" | sed 's/^/LD: /'
  [[ "${strict}" == "1" ]] && exit 2 || exit 0
fi

set +e
"${llvm_objcopy}" -O binary "${elf}" "${bin}" >"${objcopy_log}" 2>&1
objcopy_rc=$?
set -e
if [[ "${objcopy_rc}" != "0" || ! -s "${bin}" ]]; then
  printf 'STATUS blocked_objcopy\n'
  printf 'DETAIL llvm-objcopy failed; see %s\n' "${objcopy_log}"
  sed -n '1,80p' "${objcopy_log}" | sed 's/^/OBJCOPY: /'
  [[ "${strict}" == "1" ]] && exit 2 || exit 0
fi

printf 'STATUS buildable_with_llvm\n'
printf 'BINARY %s (%s bytes)\n' "${bin}" "$(stat -c '%s' "${bin}")"
if [[ -n "${llvm_objdump}" ]]; then
  "${llvm_objdump}" -d --triple=hexagon "${elf}" | sed -n '1,80p'
fi
