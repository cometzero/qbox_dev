# QBox SMMUv3 EVENTQ Stall Buffer/Redrive Verification - 2026-05-10

## Scope

SMMU-COMP-050 EVENTQ stalled-fault full-queue functional slice.

This slice changes the Apollo SMMUv3 TBU so a stalled fault record is not
reported as a normal Event queue overflow when the EVENTQ is full. Instead, the
record is buffered in the model and redriven into the memory-backed EVENTQ when
software advances `SMMU_EVENTQ_CONS` and space becomes available. Non-stall
EVENTQ records still use the existing OVFLG/OVACKFLG overflow path.

This remains a functional compliance slice. It does not implement byte-exact
STAG allocation, endpoint transaction replay ordering, all suppression/merge
rules, or real upstream `arm-smmu-v3` event-thread recovery.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  section 3.5.3 states that events from stalled faulting transactions are not
  discarded when the Event queue is full and are recorded after software frees
  queue space.
- The same section distinguishes this from non-stall events, which can be
  discarded/overflowed when the queue is unwritable.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `FEATURE_ARCH_STALL_BUFFER_REDRIVE`.
- `push_event_record()` detects stalled records while the EVENTQ is configured
  but full and calls `buffer_stall_event_record()` instead of the normal
  `set_arch_queue_overflow()` path.
- `write_smmuv3_reg(SMMUV3_EVENTQ_CONS)` now calls
  `drain_stall_event_buffer()` after software advances the Event queue
  consumer pointer.
- Drained stalled records are written through the existing memory-backed EVENTQ
  writer, assert the EVENTQ IRQ, and leave GERROR/OVFLG untouched unless the
  eventual memory write itself aborts.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` adds
  `FaultReplayFullEventQueueBuffersAndRedrivesStall`.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh` gate the slice.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-eventq-stall-buffer-redrive-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-eventq-stall-buffer-redrive-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1`; `FaultReplayFullEventQueueBuffersAndRedrivesStall` verifies stall buffering without OVFLG/GERROR and redrive after `EVENTQ_CONS`. |
| Static/checker/lane | PASS | `build/verification/smmu-eventq-stall-buffer-redrive-static-pre-runtime-20260510.log`: `PASS  tbu:eventq-stall-buffer-redrive`, `SUMMARY {"pass": 270}`, and lane check passed. |
| Platform build | PASS | `build/verification/qbox-platform-smmu-eventq-stall-buffer-redrive-20260510.log`: `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`. |
| Guest smoke | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-eventq-stall-buffer-redrive.driver.log`: `PASS: QBox guest IREE Hexagon tiny-CNN output matched`; runtime log records `features=0x1ffffff` and `1x1x2x2xf32=[[[54 63][90 99]]]`. |

## Remaining blockers

- Byte-exact STAG allocation and matching are still modeled with compact replay
  counters rather than a full hardware transaction table.
- Endpoint transactions are not truly held and reissued on the TLM data path.
- Full event suppression/merge rules, early retry, and ordering against
  `CMD_SYNC`/MSI delivery remain open.
