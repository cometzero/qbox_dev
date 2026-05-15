# QBox SMMUv3 GMPAM originated-write verification - 2026-05-11

## Scope

SMMU-COMP-020/050 GMPAM originated-write functional slice.

This slice wires the modeled Non-secure `SMMU_GMPAM` PARTID/PMG values into
Apollo SMMU TLM attributes for SMMU-originated downstream writes. The current
coverage applies to queue record writes through `write_downstream_u64()` and MSI
writes through `write_downstream_u32()`; descriptor-fetch MPAM attribution is
left open so CD/STE/VMS fetch classification can be modeled without incorrectly
marking all reads as originated writes.

Ground truth used for this slice:

- `sources/smmu/wiki/synthesis/smmu-register-map.md`
  - `SMMU_GMPAM` is at offset `0x0138` and provides MPAM attributes for
    SMMU-originated transactions.
- `sources/smmu/wiki/concepts/mpam.md`
  - L1STD, STE, queues, MSIs, and VMS transactions use
    `SMMU_(*_)GMPAM.SO_{PARTID,PMG}`.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  - Queue accesses use `SMMU_(*_)GMPAM` MPAM attributes, and `SMMU_GMPAM` is a
    32-bit MPAM register present when `SMMU_IDR3.MPAM==1`.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `SMMUV3_GMPAM = 0x138`
  - `write_arch_mpam_update_reg()`
  - `populate_arch_mpam_extension()`
  - `write_downstream_u64()` queue record write extension propagation
  - `write_downstream_u32()` MSI write extension propagation
- `sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h`
  - `mpam_valid`, `mpam_unknown`, `mpam_partid`, `mpam_pmg`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `GmpamAttributesPropagateOnEventqWrites`

## Validation evidence

| Check | Evidence |
| --- | --- |
| Build | `build/verification/apollo-smmu-tbu-mpam-gmpam-build-20260511.log` (`Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`) |
| Component CTest | `build/verification/apollo-smmu-tbu-mpam-gmpam-ctest-20260511.log` (`100% tests passed, 0 tests failed out of 1`) |
| Focused gTest | `build/verification/apollo-smmu-tbu-mpam-gmpam-gtest-20260511.log` (`[  PASSED  ] 1 test.`) |
| Syntax checks | `build/verification/smmu-mpam-gmpam-syntax-20260511.log` |
| Static/lane checker | `build/verification/smmu-mpam-gmpam-static-final-20260511.log` (`PASS  tbu:mpam-gmpam-originated-writes`, `SUMMARY {"pass": 516}`) |
| Compliance JSON | `build/verification/qbox-smmuv3-compliance-mpam-gmpam-final-20260511.json` (`full_smmuv3_compliance: not_claimed`) |

## Result

`GmpamAttributesPropagateOnEventqWrites` programs `SMMU_GMPAM.Update=1` with
`PARTID=0x1d` and `PMG=0x4`, pushes an EVENTQ record, and proves the downstream
memory target observes `mpam_valid==true`, `mpam_unknown==false`, and the same
PARTID/PMG on the Apollo SMMU TLM extension.

Remaining blockers: descriptor fetch attribution for STE/CD/VMS reads, complete
Secure/Realm MPAM_NS/SP selection, PMCG PARTID/PMG filtering, and complete ATS
Translated/PASID MPAM rules remain open.
