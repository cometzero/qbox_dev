# QBox SMMUv3 CD-table SSID indexing verification

- Date: 2026-05-10
- Scope: `/build/qbox_dev`
- Component slice: SMMU-COMP-030 follow-up
- Status: functional slice verified; full ARM SMMUv3 compliance is not claimed

## Implemented

- Added `FEATURE_ARCH_CD_TABLE_INDEX` to the Apollo SMMU TBU feature bitmap.
- Added `REG_ARCH_SSID` to select a modeled SubstreamID/PASID for component
  vectors without breaking the existing Apollo Linux compatibility probe.
- Added `REG_ARCH_CD_DETAIL` to expose selected SSID, S1DSS, S1CDMax, S1FMT,
  and 64K-L2 CD-table usage in tests.
- Decoded `STE.S1CDMax`, `STE.S1DSS`, `STE.S1FMT=linear`, and modeled
  `STE.S1FMT=64K_L2` context descriptor table selection.
- Indexed linear CD tables by selected SSID and faults out-of-range SSIDs with
  `ARCH_FAULT_CD_INVALID`.
- Indexed modeled 64K-L2 CD tables through an L1 descriptor and L2 CD entry.
- Preserved legacy no-SSID CD0 compatibility for existing tests/guest probe.

## Verification evidence

| Check | Evidence |
| --- | --- |
| Component build | `build/verification/apollo-smmuv3-cd-table-ssid-build-20260510.log` |
| Component CTest | `build/verification/apollo-smmuv3-cd-table-ssid-ctest-20260510.log` (`100% tests passed`) |
| Component test | `ArchitectedContextDescriptorTableIndexesSelectedSsid` |
| Source markers | `FEATURE_ARCH_CD_TABLE_INDEX`, `REG_ARCH_SSID`, `ARCH_STE_S1CDMAX_SHIFT`, `ARCH_STE_S1DSS_MASK`, `ARCH_STE_S1FMT_64K_L2` |
| Static/lane gate | `build/verification/smmu-cd-table-ssid-static-final-20260510.log` (`SUMMARY {"pass": 128}`; Buildroot ARM64 lane PASS; diff checks PASS) |
| Platform rebuild | `build/verification/qbox-platform-smmu-cd-table-ssid-20260510.log` (`QBox Buildroot platform runtime built`) |
| Guest smoke driver | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-cd-table-ssid.driver.log` (`PASS: QBox guest IREE Hexagon tiny-CNN output matched`) |
| Guest runtime log | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-cd-table-ssid.log` (`features=0x7fff`, output `1x1x2x2xf32=[[[54 63][90 99]]]`) |

## Remaining blockers

- Full S1DSS bypass semantics are not modeled; bypass is still conservative in
  this functional slice.
- PASID/SSID is selected through a component register, not end-to-end PCIe/ATS
  transaction metadata.
- S2/nested CD formats, full Arm reserved-matrix parity, and byte-exact CD fault event
  payloads remain open.
- Linux `arm-smmu-v3`-generated CD invalidation and multi-master runtime
  coverage remain open.
