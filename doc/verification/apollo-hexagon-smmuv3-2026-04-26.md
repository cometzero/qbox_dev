# Apollo SMMUv3 + Hexagon Bring-up Verification

Date: 2026-04-26
Workspace: `/build/qbox_dev`
Branch: `feature/qbox_dev`

## Scope

This report records the implementation and verification for adding an
ARM SMMUv3-visible path and a powered-off Hexagon sidecar to the Apollo QBox
platform. The first proof target is Linux/Buildroot boot with the Linux SMMUv3
driver and an Apollo Hexagon platform probe driver binding successfully.

## Implemented Changes

- QBox Apollo platform now instantiates:
  - `arm_smmuv3` wrapper for QEMU `arm-smmuv3`.
  - `qemu_cpu_hexagon` sidecar with Hexagon global register, L2VIC, qtimer,
    and 4 MiB Hexagon SRAM.
  - local libqemu targets `aarch64;hexagon` during QBox build.
- Linux DTS now advertises:
  - `iommu@1c200000` with `compatible = "arm,smmu-v3"`.
  - `hexagon@1c220000` with `iommus = <&smmu 0x1>`.
  - `hexagon_sram@c00000` reserved memory.
- Linux source now contains `drivers/soc/apollo/apollo-hexagon-test.c`, a
  built-in platform probe that checks IOMMU group attachment and coherent DMA.
- Root scripts now build/check/stage the added SMMUv3 and Hexagon modules.

## Commands Run

```bash
bash -n scripts/*.sh
python3 - <<'PY'
import ast, pathlib
for p in pathlib.Path('scripts').glob('*.py'):
    ast.parse(p.read_text())
    print(f'python-ok {p}')
PY
./scripts/check_buildroot_arm64_lane.sh
git diff --check

./scripts/build_qbox_linux_arm64.sh \
  2>&1 | tee build/verification/linux-hexagon-smmuv3-2026-04-26-214018.log
./scripts/build_qbox_buildroot_arm64.sh \
  2>&1 | tee build/verification/buildroot-hexagon-smmuv3-2026-04-26-214018.log
./scripts/build_qbox_buildroot_platform.sh \
  2>&1 | tee build/verification/qbox-platform-hexagon-smmuv3-2026-04-26-214018.log
./scripts/stage_buildroot_artifacts.sh \
  2>&1 | tee build/verification/stage-hexagon-smmuv3-2026-04-26-214018.log

QBOX_BOOT_TIMEOUT=45 \
QBOX_BOOT_LOG=build/verification/qbox-boot-hexagon-smmuv3-retry-2026-04-26-214018.log \
  ./scripts/run_qbox_buildroot_boot.sh

QBOX_BOOT_TIMEOUT=25 \
QBOX_BOOT_LOG=build/verification/qbox-boot-hexagon-smmuv3-final-2026-04-26-215355.log \
  ./scripts/run_qbox_buildroot_boot.sh
```

## Build Evidence

- Linux build completed and produced:
  - `build/linux-a710/arch/arm64/boot/Image` (`41M`)
- Buildroot build completed and produced:
  - `build/buildroot-a710/images/rootfs.cpio` (`3.7M`)
  - `build/buildroot-a710/images/apollo_soc.dtb` (`3.4K`)
- QBox build completed and produced:
  - `sources/qbox/build/platforms-vp`
  - `sources/qbox/build/arm_smmuv3.so`
  - `sources/qbox/build/qemu_cpu_hexagon.so`
  - `sources/qbox/build/hexagon_globalreg.so`
  - `sources/qbox/build/hexagon_l2vic.so`
  - `sources/qbox/build/qemu_hexagon_qtimer.so`

## Boot Evidence

Boot logs:

- `build/verification/qbox-boot-hexagon-smmuv3-retry-2026-04-26-214018.log`
- `build/verification/qbox-boot-hexagon-smmuv3-final-2026-04-26-215355.log`

Relevant markers:

```text
Linux version 7.0.0-13891-g27d128c1cff6-dirty
Machine model: Apollo SoC on apollo-qbox
SMP: Total of 4 processors activated.
OF: reserved mem: ... hexagon_sram@c00000
arm-smmu-v3 1c200000.iommu: oas 44-bit (features 0x01008305)
platform 1c220000.hexagon: Adding to iommu group 0
apollo-hexagon-test 1c220000.hexagon: iommu group attached
apollo-hexagon-test 1c220000.hexagon: dma selftest ok dma=0x0000fffffffff000 size=4096
apollo-hexagon-test 1c220000.hexagon: probe ok
Run /sbin/init as init process
apollo-qbox login:
```

Both bounded runs ended with `BOOT_RC=124` because `QBOX_BOOT_TIMEOUT` intentionally
stopped the otherwise interactive simulation after reaching the login prompt. The
latest final run reached `apollo-qbox login:` and stopped at 24 seconds wall clock.

## Limitations / Next Work

- Hexagon CPU is intentionally `start_powered_off=true`; no Hexagon firmware is
  loaded or executed yet.
- The Linux probe verifies IOMMU binding and coherent DMA allocation from the
  APSS side; it does not yet generate real Hexagon DMA traffic through SMMUv3.
- Production driver ABI, reset/power sequencing, and SystemC/TLM DMA wiring are
  future work.
