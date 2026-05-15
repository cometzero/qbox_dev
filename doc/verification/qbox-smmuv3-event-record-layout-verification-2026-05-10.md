# QBox SMMUv3 EVENTQ Common Record Layout Verification - 2026-05-10

## Scope

This report records a SMMU-COMP-050 follow-up functional slice for the Apollo
SMMU TBU fault/event replay model.

The slice implements and verifies architected common EVENTQ record fields for
modeled QBox faults: event number, StreamID, SubstreamID/SSV, InputAddr, a
modeled IPA/payload word, and the existing syndrome/detail word. It also adds
modeled `CMD_STALL_TERM` handling for pending stall accounting.

This is not full Arm SMMUv3 event replay compliance. The full byte-exact layout
for every event type, fetch-address fields, all permission/security/IPA fields,
true STAG matching, stall transaction buffering, and endpoint transaction
re-drive remain open.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - advertises `FEATURE_ARCH_EVENT_RECORD_LAYOUT`;
  - maps modeled fault reasons to architected EVENTQ event numbers such as
    `C_BAD_STREAMID`, `C_BAD_STE`, `C_BAD_CD`, `F_TRANSLATION`, `F_ADDR_SIZE`,
    `F_ACCESS`, and `F_PERMISSION`;
  - writes the common EVENTQ word0 layout with event number, SSV/SubstreamID,
    and StreamID;
  - writes InputAddr in word1 and preserves the modeled syndrome/STAG detail in
    word3;
  - logs `architected EVENTQ record layout` for traceability;
  - decodes `ARCH_CMD_STALL_TERM` and accounts termination of modeled pending
    stalls.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - updates `FaultReplayRecordsSyndromeAndResumeState` for architected event
    numbers;
  - adds `ArchitectedEventRecordLayoutCarriesSubstream`;
  - adds `CmdStallTermTerminatesPendingStalls`.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmuv3-event-layout-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests` |
| Component CTest | PASS | `build/verification/apollo-smmuv3-event-layout-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1` |
| Static/checker/lane | PASS | `build/verification/smmu-event-layout-static-final-20260510.log`: `SUMMARY {"pass": 163}`, Buildroot lane PASS, and superproject/`sources/qbox`/`sources/linux` diff checks PASS. |
| Platform build | PASS | `build/verification/qbox-platform-smmu-event-layout-20260510.log`: `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build` |
| Guest smoke | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-event-layout.driver.log`: `PASS: QBox guest IREE Hexagon tiny-CNN output matched`, `Expected: 1x1x2x2xf32=[[[54 63][90 99]]]`; runtime log records `features=0x1ffff` and `architected EVENTQ record layout`. |

## Remaining blockers

- Full byte-exact event formats for every Arm SMMUv3 event type.
- Fetch-address fields for STE/CD/walk external aborts.
- Complete IPA/security/permission/TTRnW/fault-class field parity.
- True STAG allocation and matching across independent stalled transactions.
- Stall transaction buffering and endpoint transaction re-drive.
- Linux `arm-smmu-v3` driven event consumption and CD invalidation coverage.
- Endpoint-derived PASID/SSID plumbing and full multi-master runtime coverage.
