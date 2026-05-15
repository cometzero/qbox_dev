# QBox SMMUv3 security-state EVENTQ bank mirror verification (2026-05-11)

## Scope

SMMU-COMP-050 security-state EVENTQ bank mirror functional slice.

This slice adds a modeled per-security-state EVENTQ bank mirror for committed
EVENTQ records. The current QBox data path still exposes one guest-visible
EVENTQ because Secure/Realm/Root translation is intentionally rejected, but every
committed event now snapshots its record words, guest queue address, and
producer/consumer state into the logical Non-secure, Secure, Realm, or Root bank
selected by the event security state.

## Implementation summary

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Adds `arch_security_eventq_bank` and
    `m_arch_security_eventq_banks[4]` for per-state bank mirror storage.
  - Adds `arch_security_eventq_bank_state()` for component-test inspection.
  - Adds `arch_queue_next_record_addr()` so committed events can snapshot the
    guest queue address associated with each mirrored record.
  - Extends `record_arch_eventq_security_route()` to capture EVENTQ words,
    guest record address, producer, consumer, and per-bank record counts.
  - Applies the same bank mirror path to directly pushed and redriven stalled
    EVENTQ records.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Extends `UnsupportedSecurityStateIsRejectedBeforeTranslation` so Secure,
    Realm, and Root rejected `F_UUT` events are mirrored into their corresponding
    logical EVENTQ banks with expected words, guest address, and producer state.
  - Extends `FaultReplayFullEventQueueBuffersAndRedrivesStall` so a buffered
    Realm stalled record redriven after a Non-secure current-state change is
    mirrored into the Realm bank.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Add static/lane guards for the per-state EVENTQ bank mirror and component
    assertions.

## Verification evidence

| Evidence | Command | Result |
| --- | --- | --- |
| QBox component build | `cmake --build sources/qbox/build --target apollo_smmu_tbu apollo-smmu-tbu-tests -j2` | Pass; see `build/verification/smmu-security-eventq-bank-build-pre-20260511.log`. |
| QBox component test | `ctest --test-dir sources/qbox/build -R '^apollo-smmu-tbu-tests$' --output-on-failure` | Pass, `1/1 Test #15: apollo-smmu-tbu-tests ............   Passed`; see `build/verification/smmu-security-eventq-bank-ctest-pre-20260511.log`. |
| Shell syntax | `bash -n scripts/check_buildroot_arm64_lane.sh` and `bash -n scripts/*.sh` | Pass; see `build/verification/smmu-security-eventq-bank-bashn-20260511.log` and `build/verification/smmu-security-eventq-bank-bashn-all-20260511.log`. |
| Python syntax | `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | Pass; see `build/verification/smmu-security-eventq-bank-pycompile-20260511.log`. |
| Static checker | `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/qbox-smmuv3-compliance-security-eventq-bank-final-20260511.json` | Pass, expected `SUMMARY {"pass": 626}` with `full_smmuv3_compliance=not_claimed`; see `build/verification/smmu-security-eventq-bank-static-final-20260511.log`. |
| Buildroot lane | `./scripts/check_buildroot_arm64_lane.sh` | Pass; see `build/verification/smmu-security-eventq-bank-lane-20260511.log`. |
| Diff hygiene | `git -C sources/qbox diff --check` and `git diff --check` | Pass; see `build/verification/smmu-security-eventq-bank-qbox-diff-check-20260511.log` and `build/verification/smmu-security-eventq-bank-superproject-diff-check-20260511.log`. |
| QBox guest smoke | `QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260511-security-eventq-bank QBOX_BOOT_TIMEOUT=70 QBOX_IREE_LOGIN_DELAY=24 QBOX_IREE_AFTER_COMMAND_DELAY=24 ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` | Pass; matched `1x1x2x2xf32=[[[54 63][90 99]]]`; see `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-security-eventq-bank.driver.log`, runtime log `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-security-eventq-bank.log`, and boot log `build/verification/qbox-iree-tiny-cnn-hexagon-guest-boot-20260511-security-eventq-bank.log`. |

## Current classification

- SMMU-COMP-050 remains a **functional slice**.
- This narrows the Secure/Realm event-routing blocker by separating committed
  EVENTQ observation into per-security-state logical bank mirrors.
- Remaining blockers still include true separate Secure/Non-secure EVENTQ memory
  banks, secure stream-table banking, `NSCFG`/`S_S2TTB` selection, full RME/GPT
  routing, complete event matrix parity, and upstream Linux `arm-smmu-v3`
  recovery parity.
