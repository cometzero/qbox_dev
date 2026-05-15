# QBox SMMUv3 VATOS VMID-scope slice verification (2026-05-11)

Marker: SMMU-COMP-020/030/080 VATOS VMID-scope slice.

## Scope

Attempt 97 narrows the VATOS/S_VATOS gap without advertising the optional
VATOS page to guest software:

- Decodes `STE.S2VMID` from STE word 2 bits `[63:48]` for modeled stage-2 and
  nested stream configurations.
- Propagates the decoded VMID into the existing walker/TLB tag state used by
  nested descriptor fetches and ATOS/VATOS translations.
- Adds `SMMU_(S_)VATOS_SEL` VMID-scope validation for the internal VATOS path:
  a VATOS stage-1 request is rejected with `ATOS_PAR.FAULTCODE=INV_REQ` when
  the selected VMID does not match the STE S2VMID or the selected STE is not
  VMID-tagged by a stage-2 configuration.
- Keeps `SMMU_IDR0.VATOS` clear and guest-visible `SMMU_(S_)VATOS_SEL` RAZ/WI;
  tests set the internal selector directly because platform-visible VATOS page
  placement remains a separate collision-free MMIO-layout task.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`:
  `SMMU_VATOS_SEL` carries the VMID for the VM using VATOS, and VATOS requests
  are denied when that VMID does not match the selected STE S2VMID or the STE is
  not VMID-tagged.
- `sources/smmu/wiki/synthesis/smmu-register-map.md`: VATOS/S_VATOS page
  presence is advertised by `SMMU_IDR0.VATOS` and located via BA_VATOS fields.

## Changed files

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
- `scripts/check_qbox_smmuv3_compliance.py`
- `scripts/check_buildroot_arm64_lane.sh`
- `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`
- `doc/spec/qbox-smmuv3-compliance-checklist.md`

## Validation evidence

| Gate | Command | Evidence |
| --- | --- | --- |
| Build | `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)"` | `build/verification/smmu-vatos-vmid-scope-build-20260511.log` |
| Focused gTest | `./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*Smmuv3VatosStage1OnlyRegisterPath*:*Smmuv3Vatos*:*Smmuv3GatosAddrTypeNestedStageSelection*'` | `build/verification/smmu-vatos-vmid-scope-gtest-20260511.log` |
| CTest | `ctest --test-dir sources/qbox/build --output-on-failure -R apollo-smmu-tbu-tests` | `build/verification/smmu-vatos-vmid-scope-ctest-20260511.log` |
| Static compliance | `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/smmu-vatos-vmid-scope-static-20260511.json` | `build/verification/smmu-vatos-vmid-scope-static-20260511.log` |
| Buildroot lane | `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-vatos-vmid-scope-lane-20260511.log` |
| Closure | `bash build/verification/smmu-vatos-vmid-scope-final-closure-check-20260511.sh` | `build/verification/smmu-vatos-vmid-scope-final-closure-check-20260511.log` |

## Result

This is a functional, no-overclaiming VATOS VMID-scope slice. It does not claim
full VATOS/S_VATOS compliance because `SMMU_IDR0.VATOS` remains unadvertised and
the VATOS/S_VATOS pages are not yet exposed through a collision-free platform
MMIO map. Therefore `full_smmuv3_compliance` remains `not_claimed`.
