# QBox SMMUv3 MPAM PARTID_MAP remap verification - 2026-05-11

## Scope

SMMU-COMP-020/050 MPAM PARTID_MAP remap functional slice.

This slice extends the modeled VMS path from discovery/cache fill to client
transaction attribute assignment. For nested `STE.S1MPAM==1` traffic, the TBU
now decodes `CD.PARTID` and `CD.PMG`, maps the virtual `CD.PARTID[4:0]` through
`VMS.PARTID_MAP`, and carries the resolved physical PARTID plus PMG on the
Apollo SMMU TLM extension for the downstream access.

Ground truth used for this slice:

- `sources/smmu/wiki/concepts/virtual-machine-structure.md`
  - `PARTID_MAP` is 32 little-endian 16-bit physical PARTIDs indexed by virtual
    `CD.PARTID`.
- `sources/smmu/wiki/concepts/mpam.md`
  - Nested `STE.S1MPAM==1` uses `VMS.PARTID_MAP[CD.PARTID]` and `CD.PMG`.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `ARCH_CD_MPAM_WORD_OFFSET`
  - `ARCH_CD_VIRTUAL_PARTID_MASK = 0x1f`
  - `arch_vms_partid_map_entry()`
  - `record_arch_mpam_from_cd()`
  - `REG_ARCH_MPAM_STATUS` / `REG_ARCH_MPAM_DETAIL`
- `sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h`
  - `mpam_valid`, `mpam_remapped`, `mpam_unknown`, `mpam_partid`, `mpam_pmg`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `VmsPartidMapRemapsCdPartidToMpamExtension`

## Validation evidence

| Check | Evidence |
| --- | --- |
| Build | `build/verification/apollo-smmu-tbu-mpam-partid-remap-build-20260511.log` (`Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`) |
| Component CTest | `build/verification/apollo-smmu-tbu-mpam-partid-remap-ctest-20260511.log` (`100% tests passed, 0 tests failed out of 1`) |
| Focused gTest | `build/verification/apollo-smmu-tbu-mpam-partid-remap-gtest-20260511.log` (`[  PASSED  ] 1 test.`) |
| Syntax checks | `build/verification/smmu-mpam-partid-remap-syntax-20260511.log` |
| Static/lane checker | `build/verification/smmu-mpam-partid-remap-static-final-20260511.log` (`PASS  tbu:mpam-partid-map-remap`, `SUMMARY {"pass": 487}`) |
| Compliance JSON | `build/verification/qbox-smmuv3-compliance-mpam-partid-remap-final-20260511.json` (`full_smmuv3_compliance: not_claimed`) |

## Result

`VmsPartidMapRemapsCdPartidToMpamExtension` drives a nested stream-table and
context-descriptor walk with `STE.S1MPAM==1`. It stages a VMS map entry where
virtual PARTID `5` resolves to physical PARTID `0x1a`, preserves `CD.PMG==7`,
and proves the downstream memory target observes the resolved MPAM attributes
on the TLM extension. The private MPAM status/detail registers expose the same
resolved state for checker/reporting use.

Remaining blockers: STE-sourced PARTID/PMG assignment when `STE.S1MPAM==0`,
GBPMPAM/GMPAM programming and update handshakes, Secure/Realm MPAM_NS/SP
selection, full PMG range and UNKNOWN behavior, PMCG PARTID/PMG filtering, and
SMMU-originated MPAM attributes for queues, table walks, VMS fetches, MSIs, and
PMCG-originated accesses remain open.
