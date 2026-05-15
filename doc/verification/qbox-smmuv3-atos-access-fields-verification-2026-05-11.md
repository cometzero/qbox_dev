# QBox SMMUv3 ATOS_ADDR access-field verification

Date: 2026-05-11

Marker: SMMU-COMP-030/080 ATOS_ADDR access-field attribute slice.

## Scope

This report records Attempt 95 for the reviewed SMMUv3 compliance plan. The
bounded slice aligns the architected `SMMU_GATOS` / `SMMU_S_GATOS` register path
with the local ground-truth notes in `sources/smmu/wiki/concepts/atos.md`:

- `ATOS_ADDR.PnU`, `ATOS_ADDR.InD`, and `ATOS_ADDR.RnW` are explicitly decoded
  from the ATOS register request and logged with the register translation.
- Architected ATOS/PAR success output no longer uses STE output-attribute
  overrides (`MTCFG`, `SHCFG`, `ALLOCCFG`, `INSTCFG`, `PRIVCFG`, `NSCFG`) for
  the PAR `ATTR`/`SH` fields.
- The existing QBox compatibility `REG_ARCH_CTRL=ARCH_CTRL_GATOS_TRANSLATE`
  command still exposes the older modeled `GATOS_PAR` STE-output-attribute
  return path for non-architected tests.

## Changed paths

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
- `scripts/check_qbox_smmuv3_compliance.py`
- `scripts/check_buildroot_arm64_lane.sh`
- `doc/spec/qbox-smmuv3-compliance-checklist.md`
- `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`

## Validation evidence

- Build: `build/verification/smmu-atos-access-fields-build-20260511.log`
- Focused gTest: `build/verification/smmu-atos-access-fields-gtest-20260511.log`
- CTest: `build/verification/smmu-atos-access-fields-ctest-20260511.log`
- Static checker: `build/verification/smmu-atos-access-fields-static-20260511.json`
- Lane: `build/verification/smmu-atos-access-fields-lane-20260511.log`
- Closure: `build/verification/smmu-atos-access-fields-final-closure-check-20260511.log`

## Result

The focused component test `Smmuv3GatosAddrAccessFieldsIgnoreSteOverrides`
checks that a GATOS request carrying `PnU=1`, `InD=1`, and `RnW=1` completes
successfully while keeping PAR success `ATTR=0xff` and `SH=0x3` instead of the
STE override values. It also verifies that the decoded access fields and
`m_arch_last_atos_ste_attrs_ignored` state were recorded.

## Remaining blockers

This is still a bounded ATOS register slice, not full ARM SMMUv3 compliance.
Open work remains for VATOS/S_VATOS optional pages and VMID scoping, complete
ATOS_ADDR field/attribute matrix beyond this PnU/InD/RnW slice, Root/Realm
RME/GPT/GPC behavior, packet-level PCIe ATS/PRI attributes, and upstream
lifecycle parity.
