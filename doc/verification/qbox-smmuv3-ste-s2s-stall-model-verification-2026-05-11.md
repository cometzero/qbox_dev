# QBox SMMUv3 STE.S2S terminate-only STALL_MODEL validation

Date: 2026-05-11

## Scope

SMMU-COMP-030/050 STE.S2S terminate-only STALL_MODEL validation.

This is a focused Arm SMMUv3 compliance slice grounded in
`sources/smmu/bugs/newBugs24Mar2026_7pm.md` BUG-QA-12 and the reference test
coverage in `sources/smmu/cpp/tests/unit/test_bugs_qa_11_12_13_14.cpp`:
`STALL_MODEL==0b01 && STE.S2S==1` must be rejected as `C_BAD_STE`, while the
validation must be guarded by a stage-2-enabled stream so non-stage-2 S2S bits
remain compatible.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Added modeled `ARCH_STALL_MODEL_TERMINATE_ONLY` and
    `ARCH_STALL_MODEL_STALL` constants.
  - Added `m_arch_stall_model`, defaulting to the existing stall-capable model
    so current STE.S2S stall tests keep their behavior.
  - Added `arch_ste_stage2_enabled()` and
    `arch_stall_model_terminates_stage2_stalls()`.
  - Extended `arch_reject_reserved_ste()` to reject stage-2-enabled STEs with
    `STE.S2S=1` when the modeled STALL_MODEL is terminate-only, producing
    `ARCH_FAULT_STE_INVALID` / `C_BAD_STE` before stage-2 walk execution.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Added `SteS2sRejectedWhenStallModelTerminateOnly`.
  - The test verifies the invalid stage-2 S2S path emits a non-stall
    `C_BAD_STE` EVENTQ record, then verifies an S1-only STE carrying the same
    S2S bit still translates successfully under terminate-only STALL_MODEL.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Added static/lane gates for the validation helper, constant, diagnostic,
    and component test.
- `doc/spec/qbox-smmuv3-compliance-checklist.md`
  - Updated SMMU-COMP-030/050 scope and evidence entries without claiming full
    SMMUv3 compliance.

## Verification

| Command | Evidence |
| --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j2` | `build/verification/smmu-ste-s2s-stall-model-build-20260511.log` |
| `sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*SteS2sRejectedWhenStallModelTerminateOnly*:*Stage2SteS2rS2sControlsRecordAndStall*'` | `build/verification/smmu-ste-s2s-stall-model-gtest-20260511.log` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/smmu-ste-s2s-stall-model-ctest-20260511.log` |
| `bash -n scripts/*.sh && python3 -m py_compile ... && python3 scripts/check_qbox_smmuv3_compliance.py --json ...` | `build/verification/smmu-ste-s2s-stall-model-static-20260511.log` |
| `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-ste-s2s-stall-model-lane-20260511.log` |
| final closure replay | `build/verification/smmu-ste-s2s-stall-model-final-closure-check-20260511.log` |

## Results

- Targeted build: PASS, `Built target apollo-smmu-tbu-tests`.
- Focused gTest: PASS, `[  PASSED  ] 2 tests.`
- CTest: PASS, `100% tests passed, 0 tests failed out of 1`.
- Static checker: PASS, `SUMMARY {"pass": 761}`; the checker still classifies
  `full_smmuv3_compliance` as `not_claimed`.
- Lane checker: PASS, `Lane conclusion: Buildroot owns rootfs/DTB generation only;
  Linux Image comes from sources/linux, and libqemu comes from sources/qemu`.

## Remaining blockers

This closes only the modeled STE.S2S terminate-only STALL_MODEL validation
slice. Full SMMUv3 compliance remains open for full event matrix parity, full
Secure/Realm/RME/GPT/GPC behavior, packet-level ATS/PRI protocol parity,
complete PCIe PASID/CD invalidation lifecycle, and upstream arm-smmu-v3 lifecycle
parity.
