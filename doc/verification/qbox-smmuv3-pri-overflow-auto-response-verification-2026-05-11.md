# QBox SMMUv3 PRI Overflow Auto-Response Verification (2026-05-11)

## Scope

SMMU-COMP-060 PRI overflow auto-response slice.

This slice tightens the Apollo TBU PRI model for the no-PASID overflow case:
when a Last PPR without SSV/PASID is discarded because PRIQ overflow is active,
the TBU now records an automatic PRI Success response instead of treating all
overflow cases as Response Failure.  Disabled PRIQ and active PRIQ_ABT_ERR still
produce Response Failure.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  states that, on PRI queue overflow, Last PPRs receive automatic PRG responses;
  a PPR without PASID receives no PASID prefix and ResponseCode Success.
- `sources/smmu/wiki/synthesis/smmu-pcie-ats-integration.md` summarizes the
  overflow auto-response behavior and differentiates overflow from PRIQ disabled
  or PRIQ_ABT_ERR failure responses.

## Changed paths

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
- `scripts/check_qbox_smmuv3_compliance.py`
- `scripts/check_buildroot_arm64_lane.sh`
- `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`
- `doc/spec/qbox-smmuv3-compliance-checklist.md`

## Planned evidence

- Build: `build/verification/smmu-pri-overflow-auto-response-build-20260511.log`
- Focused gTest: `build/verification/smmu-pri-overflow-auto-response-gtest-20260511.log`
- CTest: `build/verification/smmu-pri-overflow-auto-response-ctest-20260511.log`
- Static checker: `build/verification/smmu-pri-overflow-auto-response-static-20260511.{log,json}`
- Lane check: `build/verification/smmu-pri-overflow-auto-response-lane-20260511.log`

## No-overclaim note

PASID-prefixed overflow response selection still remains conservative until the
model implements `SMMU_IDR3.PPS` and `STE.PPAR` lookup.  Full PCIe packet
transport, Root Complex signaling, DPT/GPC interactions, and upstream
`arm-smmu-v3` lifecycle parity remain open.
