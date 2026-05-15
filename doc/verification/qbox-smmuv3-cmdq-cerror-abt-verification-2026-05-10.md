# QBox SMMUv3 CMDQ CERROR_ABT Verification - 2026-05-10

## Scope

SMMU-COMP-020 CMDQ CERROR_ABT functional slice.

This slice adds explicit component coverage for the architected command queue abort error class. When software enables CMDQ processing but has not configured a valid command queue base/size, the Apollo TBU leaves `CMDQ_CONS.RD` at the failing queue position, exposes `CMDQ_CONS.ERR = CERROR_ABT`, raises the existing command-queue GERROR bit, and allows software to acknowledge GERROR plus rewrite `CMDQ_CONS` to clear and skip the failed position.

This is still not full SMMUv3 CMDQ compliance: it covers the enabled-but-unconfigured abort path only. Queue memory abort ordering, fetch faults from all possible memory attributes, retry/pause behavior, CERROR_ATC_INV_SYNC, and upstream arm-smmu-v3 queue lifecycle parity remain open.

## Ground truth

- `sources/linux/drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.h` defines `CMDQ_CONS_ERR GENMASK(30, 24)` and the command queue CERROR values, including `CERROR_ABT=2`.
- `sources/smmu/cpp/include/smmu/types.h` mirrors `CMDQ_CONS_ERR_SHIFT = 24` and `CERROR_ABT = 2`.
- `sources/smmu/cpp/src/smmu/smmu.cpp` preserves `CMDQ_CONS.ERR` and keeps `CMDQ_CONS.RD` on the failing command after a command queue error.

## Implementation

- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` adds `CmdqUnconfiguredQueueSetsCerrorAbt`.
- The test drives `CMDQ_PROD` while CMDQ processing is enabled but no command queue base has been configured, then validates `CMDQ_CONS.RD=0`, `CMDQ_CONS.ERR=CERROR_ABT`, `GERROR.CMDQ_ABORT`, and the GERROR IRQ line.
- The test then acknowledges `GERRORN.CMDQ_ABORT`, rewrites `CMDQ_CONS=1`, and confirms the guest-visible error state is cleared.
- `scripts/check_qbox_smmuv3_compliance.py`, `scripts/check_buildroot_arm64_lane.sh`, and `doc/spec/qbox-smmuv3-compliance-checklist.md` now gate the ABT slice.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-cmdq-cerror-abt-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-cmdq-cerror-abt-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1`. |
| Static/checker/lane | PASS | `build/verification/smmu-cmdq-cerror-abt-static-final-20260510.log`: `PASS  tbu:cmdq-cerror-abt`, `SUMMARY {"pass": 222}`, and the Buildroot lane conclusion. |

## Remaining blockers

- Complete illegal-command matrix and all command-dependent CERROR_ILL cases.
- Full CERROR_ABT matrix for command queue memory fetch/write faults and ordering.
- CERROR_ATC_INV_SYNC behavior and ATC invalidation completion ordering.
- CMDQ pause/retry, GERRORN/CMDQ_CONS recovery corner cases, MSI delivery, and full upstream `arm-smmu-v3` queue lifecycle parity.
