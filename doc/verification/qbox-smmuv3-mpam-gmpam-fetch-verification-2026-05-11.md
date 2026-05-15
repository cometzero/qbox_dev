# QBox SMMUv3 GMPAM originated-fetch verification - 2026-05-11

## Scope

SMMU-COMP-020/050 GMPAM originated-fetch functional slice.

This slice extends the modeled `SMMU_GMPAM` attribution from SMMU-originated
writes to selected SMMU-originated reads. The TBU now attaches Apollo SMMU TLM
MPAM attributes to command-queue fetches, two-level stream-table L1STD fetches,
STE fetches, and VMS PARTID_MAP fetches. L1CD/CD and translation-table
descriptor fetches remain intentionally separate because the local ground truth
assigns those accesses to STE/client-derived MPAM sources rather than GMPAM.

Ground truth used for this slice:

- `sources/smmu/wiki/concepts/mpam.md`
  - L1STD, STE, queues, MSIs, and VMS transactions use
    `SMMU_(*_)GMPAM.SO_{PARTID,PMG}`.
  - L1CD/CD and translation-table descriptor fetches use STE/client-derived
    MPAM sources, so this slice does not blanket-tag all descriptor reads.
- `sources/smmu/wiki/synthesis/smmu-register-map.md`
  - `SMMU_GMPAM` is at offset `0x0138` and provides MPAM attributes for
    SMMU-originated transactions.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `read_downstream_u64(..., bool apply_gmpam = false)`
  - `populate_arch_mpam_extension()`
  - `read_downstream_u64(entry_pa, word0, true)` for CMDQ fetches
  - `read_downstream_u64(l1_pa, l1_desc, true)` for L1STD fetches
  - `read_downstream_u64(ste_pa, ste0, true)` for STE fetches
  - `read_downstream_u64(partid_pa, m_arch_last_vms_partid_map[i], true)` for
    VMS PARTID_MAP fetches
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `GmpamAttributesPropagateOnCmdqFetches`
  - `GmpamAttributesPropagateOnSteAndVmsFetches`

## Validation evidence

| Check | Evidence |
| --- | --- |
| Build | `build/verification/apollo-smmu-tbu-mpam-gmpam-fetch-build-20260511.log` (`Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`) |
| Component CTest | `build/verification/apollo-smmu-tbu-mpam-gmpam-fetch-ctest-20260511.log` (`100% tests passed, 0 tests failed out of 1`) |
| Focused gTest | `build/verification/apollo-smmu-tbu-mpam-gmpam-fetch-gtest-20260511.log` (`[  PASSED  ] 2 tests.`) |
| Syntax checks | `build/verification/smmu-mpam-gmpam-fetch-syntax-20260511.log` |
| Static/lane checker | `build/verification/smmu-mpam-gmpam-fetch-static-final-20260511.log` (`PASS  tbu:mpam-gmpam-originated-fetches`, `SUMMARY {"pass": 525}`) |
| Compliance JSON | `build/verification/qbox-smmuv3-compliance-mpam-gmpam-fetch-final-20260511.json` (`full_smmuv3_compliance: not_claimed`) |

## Result

`GmpamAttributesPropagateOnCmdqFetches` programs `SMMU_GMPAM.Update=1`, fetches
a memory-backed command-queue entry, and proves the downstream read carries the
programmed PARTID/PMG. `GmpamAttributesPropagateOnSteAndVmsFetches` exercises a
nested stream with `STE.S1MPAM` and proves the STE and VMS fetch reads carry the
same GMPAM attributes while the later client transaction still resolves its
CD/VMS PARTID_MAP attributes independently.

Remaining blockers: STE-sourced CD fetch attribution while `STE.S1MPAM==1`, client-derived
MPAM on stage-1/stage-2 translation-table descriptor fetches, complete Secure/Realm
MPAM_NS/SP selection, PMCG PARTID/PMG filtering, and complete ATS
Translated/PASID MPAM rules remain open.
