# QBox SMMUv3 GBPMPAM global-bypass verification - 2026-05-11

## Scope

SMMU-COMP-020/050 GBPMPAM global-bypass functional slice.

This slice adds the Non-secure MPAM programming registers needed for global
bypass client transactions. `SMMU_GBPMPAM` accepts an architected `Update=1`
write and the TBU applies the accepted `GBP_PARTID`/`GBP_PMG` to downstream
client transactions while `SMMU_CR0.SMMUEN==0`.

Ground truth used for this slice:

- `sources/smmu/wiki/synthesis/smmu-register-map.md`
  - `SMMU_GMPAM` is at offset `0x0138` and `SMMU_GBPMPAM` is at offset
    `0x013C`.
- `sources/smmu/wiki/concepts/mpam.md`
  - Global bypass traffic (`SMMU_(*_)CR0.SMMUEN==0`) uses
    `SMMU_(S_)GBPMPAM.GBP_{PMG,PARTID}`.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  - `SMMU_GBPMPAM.GBP_PMG` is bits `[23:16]` and `GBP_PARTID` is bits
    `[15:0]`; `Update` is bit `[31]`.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `SMMUV3_GMPAM = 0x138`
  - `SMMUV3_GBPMPAM = 0x13c`
  - `ARCH_MPAM_UPDATE`
  - `write_arch_mpam_update_reg()`
  - `record_arch_mpam_from_gbp()`
- `sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h`
  - `mpam_valid`, `mpam_unknown`, `mpam_partid`, `mpam_pmg`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `GlobalBypassUsesGbpmpamAttributes`

## Validation evidence

| Check | Evidence |
| --- | --- |
| Build | `build/verification/apollo-smmu-tbu-mpam-gbpmpam-build-retry-20260511.log` (`Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`) |
| Component CTest | `build/verification/apollo-smmu-tbu-mpam-gbpmpam-ctest-retry-20260511.log` (`100% tests passed, 0 tests failed out of 1`) |
| Focused gTest | `build/verification/apollo-smmu-tbu-mpam-gbpmpam-gtest-retry-20260511.log` (`[  PASSED  ] 1 test.`) |
| Syntax checks | `build/verification/smmu-mpam-gbpmpam-syntax-20260511.log` |
| Static/lane checker | `build/verification/smmu-mpam-gbpmpam-static-final-20260511.log` (`PASS  tbu:mpam-gbpmpam-global-bypass`, `SUMMARY {"pass": 509}`) |
| Compliance JSON | `build/verification/qbox-smmuv3-compliance-mpam-gbpmpam-final-20260511.json` (`full_smmuv3_compliance: not_claimed`) |

## Result

`GlobalBypassUsesGbpmpamAttributes` programs a dynamic stream map, disables
`SMMU_CR0.SMMUEN`, writes `SMMU_GBPMPAM.Update=1` with `PARTID=0x1c` and
`PMG=0x5`, and proves the downstream memory target observes those MPAM
attributes on the Apollo SMMU TLM extension.

Remaining blockers: `GMPAM` propagation to SMMU-originated queue/STE/MSI/VMS
fetches, Secure/Realm MPAM_NS/SP selection, PMCG PARTID/PMG filtering, and
complete ATS Translated/PASID MPAM rules remain open.
