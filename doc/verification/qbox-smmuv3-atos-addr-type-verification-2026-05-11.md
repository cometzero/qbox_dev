# QBox SMMUv3 ATOS_ADDR.TYPE Verification (2026-05-11)

Marker: SMMU-COMP-030/080 ATOS_ADDR.TYPE matrix slice.

## Scope

This report records the bounded ATOS register-address follow-up for the Apollo
SMMU TBU model.  The slice keeps the existing non-secure and Secure
`SMMU_(S_)GATOS` RUN/PAR register groups and adds architected decoding for the
`ATOS_ADDR` low fields used by those register groups:

- `TYPE=0b00` is rejected with `INV_REQ` (`GATOS_PAR.FAULTCODE=0xff`).
- `TYPE=0b01` selects a stage-1-only ATOS walk.
- `TYPE=0b10` selects a stage-2-only ATOS walk when stage 2 is present.
- `TYPE=0b11` selects a nested stage-1 + stage-2 ATOS walk.
- A requested stage that is not configured for the selected STE is rejected with
  `INV_STAGE` (`GATOS_PAR.FAULTCODE=0xfe`).
- `RnW` is decoded into the modeled read/write walk permission path.

The implementation intentionally remains a compliance slice, not a full ARM
SMMUv3 ATOS/VATOS claim: VATOS/S_VATOS pages, remaining `ATOS_ADDR` fields,
Secure SSEC non-secure-stream selection, HTTU details, packet-level PCIe
attribute parity, and RME/GPT/GPC policy are still open.

## Ground truth used

- `sources/smmu/wiki/concepts/atos.md`: ATOS overview, no fault event/stall side
  effects, GATOS/S_GATOS/VATOS register groups, and `ATOS_PAR` fault model.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`:
  Chapter 9 ATOS register usage, `ATOS_ADDR.TYPE`, `INV_REQ`, and `INV_STAGE`
  behavior.

## Changed implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Added `ARCH_ATOS_ADDR_*` field constants and `ARCH_FAULT_ATOS_INV_REQ` /
    `ARCH_FAULT_ATOS_INV_STAGE` fault reasons.
  - Added register-path ATOS state so `SMMU_(S_)GATOS_ADDR` is decoded as an
    architected ATOS address register instead of a raw IOVA.
  - Added `arch_atos_validate_ste_config()` to reject reserved `TYPE` and
    absent-stage requests before returning PAR.
  - Added stage-1-only and stage-2-only selection paths for nested streams while
    preserving the existing full nested stage-1+stage-2 path.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Added `atos_addr()` helper for architected register-field encoding.
  - Added `Smmuv3GatosAddrTypeReservedAndInvStage`.
  - Added `Smmuv3GatosAddrTypeNestedStageSelection`.
  - Updated existing GATOS/S_GATOS register tests to encode stage-1 ATOS
    requests explicitly.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Added static/lane evidence for the ATOS_ADDR.TYPE slice.
- `doc/spec/qbox-smmuv3-compliance-checklist.md`
  - Updated SMMU-COMP-020/030/080 claim scopes and evidence without claiming
    full compliance.

## Validation evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Rebuild `apollo-smmu-tbu-tests` | PASS | `build/verification/smmu-atos-addr-type-build-20260511.log` |
| Focused gTest | PASS | `build/verification/smmu-atos-addr-type-gtest-20260511.log` |
| CTest regression | PASS | `build/verification/smmu-atos-addr-type-ctest-20260511.log` |

Focused gTest filter:

```text
*Smmuv3GatosAddrTypeReservedAndInvStage*:*Smmuv3GatosAddrTypeNestedStageSelection*:*Smmuv3GatosRegistersRunAndClear*:*SecureSmmuv3GatosRegistersUseSecureBank*
```

## Remaining blockers

`full_smmuv3_compliance` remains `not_claimed`. Remaining aggregate blockers
include VATOS/S_VATOS pages, complete `ATOS_ADDR` field parity beyond TYPE/RnW,
Secure SSEC non-secure stream selection, packet-level ATS/PRI PCIe attributes,
Root/Realm RME/GPT/GPC behavior, and upstream IREE/arm-smmu-v3 lifecycle parity.
