# QBox SMMUv3 PRI STE.PPAR auto-response verification — 2026-05-11

## Scope

SMMU-COMP-060 PRI STE.PPAR auto-response slice.


SMMU-COMP-060 PRI queue overflow follow-up slice.  This verifies the
architected PASID-prefixed Last PPR overflow path after the no-PASID overflow
correction:

- Last PPR without PASID still auto-responds with PRI Success.
- Last PPR with PASID and `SMMU_IDR3.PPS==0` checks the associated `STE.PPAR`.
- Valid `STE.PPAR==1` returns Success with the same PASID/SSID modeled on the
  auto-response metadata.
- Valid `STE.PPAR==0` returns Success without a PASID prefix.
- Invalid/inaccessible STE lookup for the `STE.PPAR` check returns Response
  Failure without a PASID prefix.

This is still a functional QBox model slice, not full packet-level ATS/PRI
transport compliance.

## Ground truth

Local reference: `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
records that PRI queue overflow auto-responses use Success for no-PASID Last
PPRs, use `SMMU_IDR3.PPS` or `STE.PPAR` to decide whether a PASID prefix is
permitted for PASID-prefixed PPRs, and return Failure when the SMMU cannot
locate a valid STE while checking `STE.PPAR`.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `ARCH_STE_PPAR`
  - `ARCH_IDR3_PPS`
  - `arch_ste_ppar()`
  - `arch_pri_overflow_auto_response(...)`
  - `m_arch_last_auto_response_ssv`
  - `m_arch_pri_auto_ste_ppar_checks`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `PriProtocolOverflowUsesStePparForPasidAutoResponse`
- `scripts/check_qbox_smmuv3_compliance.py`
- `scripts/check_buildroot_arm64_lane.sh`

## Verification evidence

Expected durable logs for this slice:

- `build/verification/smmu-pri-ppar-auto-response-build-20260511.log`
- `build/verification/smmu-pri-ppar-auto-response-gtest-20260511.log`
- `build/verification/smmu-pri-ppar-auto-response-ctest-20260511.log`
- `build/verification/smmu-pri-ppar-auto-response-static-20260511.json`
- `build/verification/smmu-pri-ppar-auto-response-lane-20260511.log`
- `build/verification/smmu-pri-ppar-auto-response-final-closure-check-20260511.log`
- `build/verification/smmu-pri-ppar-auto-response-evidence-summary-final-20260511.log`

## No-overclaim boundary

`full_smmuv3_compliance` must remain `not_claimed`.  Remaining open items
include full PCIe ATS/PRI packet transport, guest-visible complete VATOS/S_VATOS
parity, RME/GPT/GPC policy, broader Secure/Realm lifecycle parity, and upstream
IREE/QEMU/Linux lifecycle convergence.
