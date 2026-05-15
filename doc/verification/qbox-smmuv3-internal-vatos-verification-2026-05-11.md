# QBox SMMUv3 internal VATOS stage-1 slice verification (2026-05-11)

Marker: SMMU-COMP-020/030/080 internal VATOS stage-1 slice.

## Scope

This attempt adds a bounded, no-overclaiming VATOS/S_VATOS model to the
Apollo SMMUv3 TBU component:

- Adds the architected VATOS and S_VATOS page offsets plus
  `SMMU_VATOS_{CTRL,SID,ADDR,PAR}` register offsets.
- Adds independent GATOS and VATOS PAR state so one ATOS register group does
  not overwrite another group's PAR readback.
- Routes VATOS RUN through the existing ATOS walker with
  `m_arch_atos_virtual_interface = true`, so VATOS accepts stage-1-only
  requests and returns `INV_REQ` for stage-2 or stage-1+stage-2 requests.
- Keeps `SMMU_IDR0.VATOS` clear and `SMMU_(S_)VATOS_SEL` RAZ/WI because the
  current QBox platform maps the TBU register window as a contiguous 64 KiB
  block and a guest-visible VATOS page would collide with existing Hexagon
  timer/L2VIC MMIO without a new sparse or relocated platform map.

## Ground truth

- `sources/smmu/wiki/concepts/atos.md`: VATOS is optional, reported through
  `SMMU_IDR0.VATOS`, and supports stage-1-only ATOS lookups.
- `sources/smmu/wiki/synthesis/smmu-register-map.md`: VATOS and S_VATOS pages
  are distinct from PAGE_0/Secure PAGE_0 and are located through the BA_VATOS
  selector fields.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`:
  `SMMU_IDR0.VATOS` is bit 20; VATOS registers are only present when that bit
  is advertised.

## Changed files

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_arch_core.h`
- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
- `scripts/check_qbox_smmuv3_compliance.py`
- `scripts/check_buildroot_arm64_lane.sh`
- `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`
- `doc/spec/qbox-smmuv3-compliance-checklist.md`

## Validation evidence

| Gate | Command | Evidence |
| --- | --- | --- |
| Build | `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)"` | `build/verification/smmu-vatos-internal-build-20260511.log` |
| Focused gTest | `./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*Smmuv3VatosStage1OnlyRegisterPath*:*Smmuv3GatosAddrTypeNestedStageSelection*:*Smmuv3GatosRegistersRunAndClear*'` | `build/verification/smmu-vatos-internal-gtest-20260511.log` |
| CTest | `ctest --test-dir sources/qbox/build --output-on-failure -R apollo-smmu-tbu-tests` | `build/verification/smmu-vatos-internal-ctest-20260511.log` |
| Static compliance | `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/smmu-vatos-internal-static-20260511.json` | `build/verification/smmu-vatos-internal-static-20260511.log` |
| Buildroot lane | `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-vatos-internal-lane-20260511.log` |
| Closure | `bash build/verification/smmu-vatos-internal-final-closure-check-20260511.sh` | `build/verification/smmu-vatos-internal-final-closure-check-20260511.log` |

## Result

This is a functional compliance slice, not a full VATOS/S_VATOS compliance
claim. The model is intentionally not advertised to guest software until a
collision-free guest-visible VATOS/S_VATOS platform mapping is designed and
validated. Therefore `full_smmuv3_compliance` remains `not_claimed`.
