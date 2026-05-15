# QBox SMMUv3 CR0 Queue Gates Verification - 2026-05-10

## Scope

SMMU-COMP-020/050/060/070 functional slice for spec-position CR0 queue
enable gates.

This slice teaches the Apollo SMMUv3 TBU model to enforce CR0 SMMUEN plus
CMDQEN, EVENTQEN, and PRIQEN before consuming or producing memory-backed
CMDQ/EVENTQ/PRIQ records. It also exposes CR0.ATSCHK plumbing and updates the
Linux probe to enable the spec-position bits before queue use.

This is not full SMMUv3 command/event/PRI compliance. Full byte-exact event,
command, and PRI layouts, EATS/ATSCHK behavioral matrix coverage, endpoint
transaction re-drive, MSI delivery, upstream `arm-smmu-v3` lifecycle coverage,
and true upstream IREE source integration remain open.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `FEATURE_ARCH_CR0_QUEUE_GATES`, spec-position CR0 bits, and
  `arch_cmdq_enabled`/`arch_eventq_enabled`/`arch_priq_enabled` gates.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  adds `Cr0QueueEnableGatesCmdEventAndPriQueues`.
- `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c` now requires
  `APOLLO_TBU_FEATURE_ARCH_CR0_QUEUE_GATES` and writes
  `APOLLO_SMMUV3_CR0_ENABLE_QUEUES`.
- `scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` now gates runtime on
  `features=0x7ffff`.
- `scripts/check_qbox_smmuv3_compliance.py`,
  `scripts/check_buildroot_arm64_lane.sh`, and
  `doc/spec/qbox-smmuv3-compliance-checklist.md` record the new gate.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-cr0-gates-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-cr0-gates-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1`. |
| Linux build | PASS | `build/verification/qbox-linux-smmu-cr0-gates-20260510.log`: `CC drivers/soc/apollo/apollo-hexagon-test.o`, `Linux Image: /build/qbox_dev/build/linux-a710/arch/arm64/boot/Image`. |
| Artifact staging | PASS | `build/verification/stage-artifacts-smmu-cr0-gates-20260510.log`: staged Linux + Buildroot artifacts into the QBox platform artifact directory. |
| QBox platform runtime build | PASS | `build/verification/qbox-platform-smmu-cr0-gates-20260510.log`: `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`. |
| Guest smoke | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-cr0-gates.driver.log`: `PASS: QBox guest IREE Hexagon tiny-CNN output matched`, `Expected: 1x1x2x2xf32=[[[54 63][90 99]]]`. |
| Runtime CR0 gate marker | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-cr0-gates.log` records `features=0x7ffff`, `SMMUv3 architected queue register selftest ok`, and `SMMUv3 command invalidation selftest ok`. |
| Static/checker/lane | PASS | `build/verification/smmu-cr0-gates-static-final-20260510.log`: final checker/lane/diff evidence; current expected checker summary is `SUMMARY {"pass": 196}`. |

## Remaining blockers

- Full byte-exact command, event, and PRI layouts for every Arm SMMUv3 type.
- EATS/ATSCHK behavioral matrix and secure-stream ATS gating.
- Endpoint ATC completion ordering and transaction re-drive.
- MSI delivery/GIC interrupt wait beyond signal-level IRQ outputs.
- Upstream `arm-smmu-v3` CD invalidation and PASID lifecycle coverage.
- Full PCIe RID/PASID requester semantics.
- True upstream IREE source integration.
