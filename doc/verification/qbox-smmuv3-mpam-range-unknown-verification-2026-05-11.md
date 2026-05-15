# QBox SMMUv3 MPAM range-to-UNKNOWN verification - 2026-05-11

## Scope

SMMU-COMP-020/050 MPAM range-to-UNKNOWN functional slice.

This slice extends modeled MPAM assignment so resolved PARTID/PMG values are
checked against `SMMU_MPAMIDR` before being carried on downstream client
transactions. Unsupported values are represented as modeled UNKNOWN attributes
on the Apollo SMMU TLM extension.

Ground truth used for this slice:

- `sources/smmu/wiki/concepts/stream-table-entry.md`
  - `STE.PARTID` values greater than `SMMU_(*_)MPAMIDR.PARTID_MAX` are
    interpreted as UNKNOWN.
  - `STE.PMG` values greater than `SMMU_(*_)MPAMIDR.PMG_MAX` are interpreted
    as UNKNOWN.
- `sources/smmu/wiki/concepts/virtual-machine-structure.md`
  - `VMS.PARTID_MAP` entries greater than the supported PARTID size use an
    UNKNOWN PARTID.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `ARCH_MPAMIDR_PMG_MAX = 7`
  - `ARCH_MPAM_UNKNOWN_PARTID`
  - `ARCH_MPAM_UNKNOWN_PMG`
  - `arch_mpam_pmg_supported()`
  - `apply_arch_mpam_range()`
- `sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h`
  - `mpam_unknown`, `mpam_partid`, `mpam_pmg`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `MpamRangeOverflowMarksUnknownAttributes`

## Validation evidence

| Check | Evidence |
| --- | --- |
| Build | `build/verification/apollo-smmu-tbu-mpam-range-unknown-build-20260511.log` (`Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`) |
| Component CTest | `build/verification/apollo-smmu-tbu-mpam-range-unknown-ctest-20260511.log` (`100% tests passed, 0 tests failed out of 1`) |
| Focused gTest | `build/verification/apollo-smmu-tbu-mpam-range-unknown-gtest-20260511.log` (`[  PASSED  ] 1 test.`) |
| Syntax checks | `build/verification/smmu-mpam-range-unknown-syntax-20260511.log` |
| Static/lane checker | `build/verification/smmu-mpam-range-unknown-static-final-20260511.log` (`PASS  tbu:mpam-range-unknown`, `SUMMARY {"pass": 501}`) |
| Compliance JSON | `build/verification/qbox-smmuv3-compliance-mpam-range-unknown-final-20260511.json` (`full_smmuv3_compliance: not_claimed`) |

## Result

`MpamRangeOverflowMarksUnknownAttributes` drives a stage-1 stream/context walk
with `STE.S1MPAM==0`, programs `STE.PARTID` and `STE.PMG` one greater than the
modeled MPAMIDR maxima, and proves the downstream target observes
`mpam_unknown=true`, `mpam_partid=0xffff`, and `mpam_pmg=0xff` on the Apollo
SMMU TLM extension.

Remaining blockers: `GBPMPAM` global-bypass programming, `GMPAM`
SMMU-originated transaction attributes, Secure/Realm MPAM_NS/SP selection,
PMCG PARTID/PMG filtering, and complete ATS Translated/PASID MPAM rules remain
open.
