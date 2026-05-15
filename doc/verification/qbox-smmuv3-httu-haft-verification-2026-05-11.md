# QBox SMMUv3 HTTU HAFT table-descriptor verification - 2026-05-11

## Scope

SMMU-COMP-040/050/060 HTTU HAFT table-descriptor slice.

This slice extends the previous HTTU AF/Dirty leaf update model to the
SMMUv3.4 HAFT controls:

- `SMMU_IDR0.HTTU == 0b11` for Access, Dirty, and table-descriptor AF update
  discovery.
- `CD.HAFT` at architected bit `[67]`, modeled as CD word1 bit `3`.
- `STE.S2HAFT` at architected bit `[187]`, modeled as STE word2 bit `59`.
- Stage-1 table descriptor AF update only when `CD.HA && CD.HAFT`.
- Stage-2 table descriptor AF update only when `STE.S2HA && STE.S2HAFT`.
- Illegal `CD.HAFT` without `CD.HA`, and illegal `STE.S2HAFT` without
  `STE.S2HA`, are rejected as bad CD/STE encodings.

## Changed model surfaces

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Adds `ARCH_IDR0_HTTU_ACCESS_DIRTY_TABLE`, `ARCH_CD_HAFT`, and
    `ARCH_STE_S2HAFT`.
  - Adds table descriptor AF update state and `arch_apply_httu_table_update()`.
  - Masks `STE.S2HAFT` out of the compact modeled VMID helper to avoid
    perturbing modeled VMID selection.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Adds stage-1 and stage-2 HAFT component tests.
  - Updates the register surface test to expect `IDR0.HTTU == 0b11`.
- `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c`
  - Updates the Linux selftest IDR0 expectation to `0x098db7cb`.
- `scripts/check_qbox_smmuv3_compliance.py`
  - Adds the `tbu:httu-haft-table-updates` static gate.
- `scripts/check_buildroot_arm64_lane.sh`
  - Adds contract greps for HAFT discovery, state, helper, and tests.

## Verification evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/smmu-httu-haft-build-20260511.log` contains `[100%] Built target apollo-smmu-tbu-tests`. |
| Focused gTest | PASS | `build/verification/smmu-httu-haft-gtest-20260511.log` contains `[  PASSED  ] 5 tests.` |
| CTest target | PASS | `build/verification/smmu-httu-haft-ctest-20260511.log` contains `100% tests passed, 0 tests failed out of 1`. |
| Static checker | PASS | `build/verification/smmu-httu-haft-static-20260511.log` contains `SUMMARY {"pass": 1054}` and `full_smmuv3_compliance` remains `not_claimed`. |
| Buildroot lane contract | PASS | `build/verification/smmu-httu-haft-lane-20260511.log` reaches the lane conclusion with the new HAFT contract greps passing. |
| Syntax / pycompile / diff-check | PASS | `smmu-httu-haft-bash-syntax-20260511.log`, `smmu-httu-haft-pycompile-20260511.log`, and `smmu-httu-haft-diff-check-20260511.log` are empty success logs. |

## Remaining gap classification

This is still a bounded compliance slice, not a claim of full ARM SMMUv3
compliance.  Remaining open items include full atomic/coherency ordering for
HTTU visibility, complete ATS/PRI interaction parity for every HTTU-influenced
transaction class, DPT, ECMDQ, RME/GPT/GPC, and upstream Linux `arm-smmu-v3`
lifecycle parity.
