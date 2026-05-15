# QBox SMMUv3 Multi-Master Topology Verification - 2026-05-10

## Scope

SMMU-COMP-080 platform-visible multi-master functional slice.

This slice adds a second Linux-visible Apollo DMA endpoint with StreamID `0x2`
behind the QBox SMMUv3 node. It closes the previous local blocker where
StreamID isolation was component-tested, but the QBox platform and DTS still
exposed only the primary Hexagon StreamID `0x1` master.

This is not full PCIe/RID/PASID topology compliance. The auxiliary endpoint is a
synthetic Apollo DMA master with its own compatibility DMA/TBU MMIO aperture,
not a PCIe requester with full RID/PASID request semantics.

## Implementation

- `sources/qbox/platforms/buildroot/conf_aarch64.lua` declares
  `APOLLO_HEXAGON_AUX_STREAM_ID = 0x2`, `hexagon_smmu_tbu_1`, and
  `hexagon_dma_1` at the auxiliary Apollo Hexagon control aperture.
- `configs/linux/apollo_soc.dts` exposes `hexagon-aux@1c300000` with
  `iommus = <&smmu 0x2>` and `apollo,smmu-stream-id = <0x2>`.
- `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c` keeps the primary
  endpoint at `/dev/apollo-hexagon` and registers auxiliary endpoints as
  `/dev/apollo-hexagon-%x`, so the second master can probe without clobbering
  the primary userspace ABI.
- `scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` gates runtime on the
  auxiliary StreamID `0x2` probe marker as well as the primary IREE workload.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Linux build | PASS | `build/verification/qbox-linux-smmu-multi-master-20260510.log` records `CC drivers/soc/apollo/apollo-hexagon-test.o` and `Linux Image: /build/qbox_dev/build/linux-a710/arch/arm64/boot/Image`. |
| Buildroot rootfs/DTB build | PASS | `build/verification/qbox-buildroot-smmu-multi-master-20260510.log` records regenerated `apollo_soc.dtb` and `Buildroot rootfs/DTB images: /build/qbox_dev/build/buildroot-a710/images`. |
| Artifact staging | PASS | `build/verification/stage-artifacts-smmu-multi-master-20260510.log` records staged `Image.bin`, DTB, and `rootfs.cpio` into the QBox platform artifact directory. |
| QBox platform runtime build | PASS | `build/verification/qbox-platform-smmu-multi-master-20260510.log` records `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`. |
| Guest smoke | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-multi-master.driver.log` records `PASS: QBox guest IREE Hexagon tiny-CNN output matched` and `Expected: 1x1x2x2xf32=[[[54 63][90 99]]]`. |
| Runtime StreamID 0x2 probe | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-multi-master.log` records `platform 1c300000.hexagon-aux: Adding to iommu group 1`, `dma path smmu-translated caps=0x7d stream-id=0x2`, `SMMUv3 stream/context descriptor probe ok stream-id=0x2`, and `userspace submit ABI ready at /dev/apollo-hexagon-2 stream-id=0x2 primary=0`. |
| Static/checker/lane | PASS | `build/verification/smmu-multi-master-static-final-20260510.log` records shell/Python syntax checks, `scripts/check_qbox_smmuv3_compliance.py --self-test-negative`, `./scripts/check_buildroot_arm64_lane.sh`, and diff checks. |

## Remaining blockers

- Full PCIe RID/PASID requester topology and request semantics.
- Endpoint ATC completion ordering across real multi-master traffic.
- Shared SMMU/CD invalidation lifecycle driven by the upstream Linux
  `arm-smmu-v3` driver.
- Byte-exact event/command/PRI layouts for every Arm SMMUv3 record type.
- Stalled endpoint transaction buffering and re-drive after PRI/fault replay.
- True upstream IREE source integration rather than the current QBox-local guest
  tool registry/runtime shim.
