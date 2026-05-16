# QBox SMMUv3 Linux arm-smmu-v3 integration verification

- Date: 2026-05-16
- Target: `/build/qbox_dev`
- Scope: verify the QBox ARM SMMUv3 path against the Linux
  `drivers/iommu/arm/arm-smmu-v3` driver surface and configure
  `apollo-hexagon-test` to install a Linux DMA-IOMMU mapping for the
  Hexagon SRAM window before mirroring that IOVA into the Apollo TBU.
- Result: PASS for the repo-local Linux/QBox integration slice.

## Compatibility result

The QBox platform is compatible with the Linux `arm-smmu-v3` driver for this
integration slice:

- The DTS exposes `compatible = "arm,smmu-v3"`, four named interrupts, and
  `#iommu-cells = <0x1>`.
- `configs/linux/linux.config` enables `CONFIG_ARM_SMMU_V3=y` and the Apollo
  Hexagon test driver.
- Linux probes `arm-smmu-v3 1c200000.iommu`, allocates CMDQ/EVENTQ storage, and
  attaches the primary and auxiliary Hexagon devices to IOMMU groups.
- `apollo-hexagon-test` now requires a DMA domain from Linux, calls
  `dma_map_resource()` for the shared/Hexagon SRAM window, verifies the mapping
  with `iommu_iova_to_phys()`, and releases it with `dma_unmap_resource()`.
- The driver constrains the DMA-IOMMU allocation to the firmware ABI window so
  Linux installs the mapping at `0x10000000`, matching the QBox Hexagon
  firmware and the Apollo TBU dynamic map window.

## Changed path

- `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c`
  - Adds Linux IOMMU group/domain validation.
  - Installs the DMA-IOMMU resource map through the Linux DMA API.
  - Verifies the IOVA resolves to the expected shared SRAM physical base.
  - Mirrors the same IOVA into the existing Apollo TBU map path.
  - Keeps the Hexagon 32-bit job-register ABI by using a 32-bit DMA mask and
    the `apollo,dma-iova-base`/`apollo,dma-window-size` firmware window.
- `scripts/check_buildroot_arm64_lane.sh`
  - Adds contract checks for the Linux DMA-IOMMU APIs and firmware-window
    constraint.
- `scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh`
  and `scripts/run_iree_vector_add_hexagon_qbox_guest_smoke.sh`
  - Require the new `arm-smmu-v3 dma-iommu map installed` runtime marker.

## Runtime evidence

Primary log:

- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260516-174313.log`
- Boot log:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-boot-20260516-174313.log`

Key markers:

- Linux SMMUv3 probe:
  `arm-smmu-v3 1c200000.iommu: oas 44-bit (features 0x01008305)`
- Linux IOMMU attachment:
  `platform 1c220000.hexagon: Adding to iommu group 0`
  `platform 1c300000.hexagon-aux: Adding to iommu group 1`
- Linux DMA-IOMMU map:
  `arm-smmu-v3 dma-iommu map installed iova=0x0000000010000000 requested=0x10000000 phys=0x0000000000a00000 size=0x600000 domain-type=0x3`
- Apollo TBU mirror:
  `dynamic SMMU map refreshed linux-iommu=yes iova=0x10000000 pa=0x0000000000a00000 size=0x600000 count=17`
- SMMUv3 feature/selftest coverage:
  `SMMUv3 command invalidation selftest ok`
  `SMMUv3 page-table walker/ATS/PRI/fault queue ready`
- DMA/offload coverage:
  `SG DMA stress ok queue=0 fence=1 bytes=131072 segments=8`
  `accelerator tiny cnn ok queue=1 fence=2 status=0x434e4e4f`
- IREE output:
  `1x1x2x2xf32=[[[54 63][90 99]]]`

## Validation commands

| Command | Result |
| --- | --- |
| `git -C sources/linux diff --check` | PASS |
| `git diff --check` | PASS |
| `bash -n scripts/*.sh` | PASS |
| `./scripts/check_buildroot_arm64_lane.sh` | PASS |
| `./scripts/build_qbox_linux_arm64.sh` | PASS: rebuilt `drivers/soc/apollo/apollo-hexagon-test.o` and `arch/arm64/boot/Image` |
| `./scripts/stage_buildroot_artifacts.sh` | PASS |
| `QBOX_BOOT_TIMEOUT=75 ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` | PASS |

## No-overclaim boundary

This verifies the Linux-visible `arm,smmu-v3` control plane, Linux DMA-IOMMU
mapping through `arm-smmu-v3`, and the QBox Apollo TBU mirror used by Hexagon
DMA in the Buildroot guest. It does not claim a complete bit-exact Arm SMMUv3
implementation or that the Apollo TBU data path is directly driven by the QEMU
`arm_smmuv3` device; that bridge remains a separate future integration step.
