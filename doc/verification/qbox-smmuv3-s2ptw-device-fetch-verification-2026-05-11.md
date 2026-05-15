# QBox SMMUv3 STE.S2PTW Device fetch verification - 2026-05-11

## Scope

SMMU-COMP-040/050/060 STE.S2PTW Device fetch permission slice.

This slice models the SMMUv3 `STE.S2PTW` control for nested translations.  When
stage 1 and stage 2 are both enabled and `STE.S2PTW` is set, a context
descriptor fetch or stage-1 translation-table descriptor fetch that is translated
through a stage-2 Device-mapped page is terminated as a stage-2 Permission fault.
When `STE.S2PTW` is clear and `IDR3.PTWNNC` is advertised, the existing PTWNNC
normalization behavior remains available for those Device-mapped stage-1 fetches.

## Changed model surfaces

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Adds `ARCH_STE_S2PTW` at architected STE word2 bit `54` and includes it in
    the modeled STE word2 mask.
  - Masks `ARCH_STE_S2PTW` out of the compact helper that derives the modeled
    VMID from STE word2.
  - Tracks `m_arch_current_s2_ptw` and `m_arch_last_s2ptw_fault` for the active
    translation.
  - Adds `arch_s2ptw_reject_device_fetch()` to convert Device-mapped nested CD
    and stage-1 TT fetches into stage-2 Permission faults.
  - Hooks the helper into linear CD fetches, level-1 CD fetches, and stage-1 TT
    descriptor fetches after their stage-2 walk resolves the backing page.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Adds `S2ptwBlocksNestedCdFetchDeviceMemory` for nested CD fetch rejection.
  - Adds `S2ptwBlocksNestedTtFetchDeviceMemory` for nested stage-1 table fetch
    rejection while the CD fetch path remains Normal NC.
  - Keeps `PtwnncNormalizesNestedStage1FetchDeviceMemory` in the focused test
    set to prove the non-S2PTW PTWNNC path is not regressed.
- `scripts/check_qbox_smmuv3_compliance.py`
  - Adds the `tbu:s2ptw-device-fetch-permission` static gate.
- `scripts/check_buildroot_arm64_lane.sh`
  - Adds contract greps for the S2PTW bit, helper, state, and component tests.

## Verification evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/smmu-s2ptw-device-fetch-build-20260511.log` contains `[100%] Built target apollo-smmu-tbu-tests`. |
| Focused gTest | PASS | `build/verification/smmu-s2ptw-device-fetch-gtest-20260511.log` contains `[  PASSED  ] 5 tests.` and `STE.S2PTW blocks Device-mapped`. |
| CTest target | PASS | `build/verification/smmu-s2ptw-device-fetch-ctest-20260511.log` contains `100% tests passed, 0 tests failed out of 1`. |
| Static checker | PASS | `build/verification/smmu-s2ptw-device-fetch-static-20260511.log` contains `SUMMARY {"pass": 1055}` and `full_smmuv3_compliance` remains `not_claimed`. |
| Buildroot lane contract | PASS | `build/verification/smmu-s2ptw-device-fetch-lane-20260511.log` reaches the lane conclusion with the new S2PTW contract greps passing. |
| Syntax / pycompile / diff-check | PASS | `smmu-s2ptw-device-fetch-bash-syntax-20260511.log`, `smmu-s2ptw-device-fetch-pycompile-20260511.log`, and `smmu-s2ptw-device-fetch-diff-check-20260511.log` are empty success logs. |

## Remaining gap classification

This is a bounded compliance slice, not a claim of full ARM SMMUv3 compliance.
Remaining open items include complete DPT behavior, ECMDQ, RME/GPT/GPC security
state parity, full upstream Linux `arm-smmu-v3` lifecycle parity, and broader
architected ordering/coherency interactions across all fetch and translation
classes.
