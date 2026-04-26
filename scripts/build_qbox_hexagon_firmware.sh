#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
qbox_root=${QBOX_ROOT:-"${repo_root}/sources/qbox"}
fw_dir="${qbox_root}/platforms/buildroot/fw"
out_dir="${qbox_root}/platforms/buildroot/fw/Artifacts"
build_dir="${repo_root}/build/hexagon-firmware"
llvm_mc=${LLVM_MC:-$(command -v llvm-mc || true)}
ld_lld=${LD_LLD:-$(command -v ld.lld || true)}
llvm_objcopy=${LLVM_OBJCOPY:-$(command -v llvm-objcopy || true)}

for tool_var in llvm_mc ld_lld llvm_objcopy; do
  tool=${!tool_var}
  if [[ -z "${tool}" ]]; then
    echo "required LLVM Hexagon firmware tool is missing: ${tool_var}" >&2
    exit 1
  fi
done

mkdir -p "${build_dir}" "${out_dir}"

src="${fw_dir}/hexagon_dma_smoke.s"
lds="${fw_dir}/hexagon_dma_smoke.ld"
obj="${build_dir}/apollo_hexagon_dma.o"
elf="${build_dir}/apollo_hexagon_dma.elf"
bin="${out_dir}/apollo_hexagon_dma.bin"

"${llvm_mc}" -arch=hexagon -filetype=obj "${src}" -o "${obj}"
"${ld_lld}" -T "${lds}" "${obj}" -o "${elf}"
"${llvm_objcopy}" -O binary "${elf}" "${bin}"

if [[ ! -s "${bin}" ]]; then
  echo "failed to produce Hexagon firmware: ${bin}" >&2
  exit 1
fi

printf 'Hexagon firmware: %s (%s bytes)\n' "${bin}" "$(stat -c '%s' "${bin}")"
