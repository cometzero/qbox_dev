# QBox SMMUv3 VMS PARTID_MAP verification - 2026-05-11

## Scope

SMMU-COMP-050 VMS PARTID_MAP fetch/cache-fill functional slice.

This slice extends the existing modeled STE.VMSPtr path from a one-word probe
to a full 64-byte VMS PARTID_MAP fetch. It stores the eight 64-bit words in a
modeled cache-fill buffer for verification and keeps VMS fetch aborts reported
as `F_VMS_FETCH`.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `ARCH_VMS_PARTID_MAP_WORDS = 8`
  - `m_arch_last_vms_partid_map`
  - `arch_fetch_vms_if_enabled()` reads each VMS PARTID_MAP word.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `VmsFetchCachesFullPartidMap`

## Validation evidence

| Check | Evidence |
| --- | --- |
| Build | `build/verification/apollo-smmu-tbu-vms-partid-map-build-20260511.log` (`Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`) |
| Focused CTest | `build/verification/apollo-smmu-tbu-vms-partid-map-ctest-20260511.log` (`100% tests passed, 0 tests failed out of 1`) |
| Focused gTest | `build/verification/apollo-smmu-tbu-vms-partid-map-gtest-20260511.log` (`[  PASSED  ] 1 test.`) |
| Syntax checks | `build/verification/smmu-vms-partid-map-syntax-20260511.log` |
| Static/lane checker | `build/verification/smmu-vms-partid-map-static-final-20260511.log` (`PASS  tbu:vms-partid-map-fetch`, `SUMMARY {"pass": 472}`) |
| Compliance JSON | `build/verification/qbox-smmuv3-compliance-vms-partid-map-final-20260511.json` (`full_smmuv3_compliance: not_claimed`) |

## Result

`VmsFetchCachesFullPartidMap` stages eight distinct PARTID_MAP words and proves
that a VMS fetch through `STE.VMSPtr` caches word 0 through word 7. The focused
gTest log also shows the modeled fetch log with `partid0=0xa110000000000000`
and `partid7=0xa110000000000007`.

Remaining blockers: real virtual-to-physical MPAM PARTID remapping,
replacement/eviction for multiple VMS cache entries, Secure/Realm VMS state,
PMG behavior, and upstream Linux VMS command-lifecycle parity remain open.
