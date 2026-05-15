# QBox SMMUv3 security-state stalled EVENTQ buffer route verification (2026-05-11)

## Scope

SMMU-COMP-050 security-state stalled EVENTQ buffer route functional slice.

This slice fixes a modeled EVENTQ redrive corner case: when a stalled fault
record is buffered because EVENTQ is full, the record now carries the security
state observed when the event was generated.  Later EVENTQ_CONS advancement can
redrive that buffered record after unrelated traffic changes the current
security state, but route accounting still uses the original event security
state.

## Implementation summary

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Replaces raw stalled EVENTQ buffered words with
    `arch_stall_event_buffer_record` containing both EVENTQ words and the
    original security state.
  - Records `m_arch_last_security_state` when a stalled event is buffered.
  - Uses the buffered record security state when redrive commits the EVENTQ
    record and calls `record_arch_eventq_security_route()`.
  - Keeps stale buffered-event discard keyed to the stored EVENTQ words.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Extends `FaultReplayFullEventQueueBuffersAndRedrivesStall` so the event is
    buffered as Realm, the current state is changed back to Non-secure before
    redrive, and the committed route/accounting remains Realm.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Add static/lane guards for the buffered security-state record and redrive
    route assertion.

## Verification evidence

| Evidence | Command | Result |
| --- | --- | --- |
| QBox component build | `cmake --build sources/qbox/build --target apollo_smmu_tbu apollo-smmu-tbu-tests -j2` | Pass; see `build/verification/smmu-security-stall-route-build-pre-20260511.log`. |
| QBox component test | `ctest --test-dir sources/qbox/build -R '^apollo-smmu-tbu-tests$' --output-on-failure` | Pass, `1/1 Test #15: apollo-smmu-tbu-tests ............   Passed`; see `build/verification/smmu-security-stall-route-ctest-pre-20260511.log`. |
| Shell syntax | `bash -n scripts/check_buildroot_arm64_lane.sh` and `bash -n scripts/*.sh` | Pass; see `build/verification/smmu-security-stall-route-bashn-20260511.log` and `build/verification/smmu-security-stall-route-bashn-all-20260511.log`. |
| Python syntax | `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | Pass; see `build/verification/smmu-security-stall-route-pycompile-20260511.log`. |
| Static checker | `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/qbox-smmuv3-compliance-security-stall-route-final-20260511.json` | Pass, expected `SUMMARY {"pass": 625}` with `full_smmuv3_compliance=not_claimed`; see `build/verification/smmu-security-stall-route-static-final-20260511.log`. |
| Buildroot lane | `./scripts/check_buildroot_arm64_lane.sh` | Pass; see `build/verification/smmu-security-stall-route-lane-20260511.log`. |
| Diff hygiene | `git -C sources/qbox diff --check` and `git diff --check` | Pass; see `build/verification/smmu-security-stall-route-qbox-diff-check-20260511.log` and `build/verification/smmu-security-stall-route-superproject-diff-check-20260511.log`. |
| QBox guest smoke | `QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260511-security-stall-route QBOX_BOOT_TIMEOUT=70 QBOX_IREE_LOGIN_DELAY=24 QBOX_IREE_AFTER_COMMAND_DELAY=24 ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` | Pass; matched `1x1x2x2xf32=[[[54 63][90 99]]]`; see `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-security-stall-route.driver.log`, runtime log `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-security-stall-route.log`, and boot log `build/verification/qbox-iree-tiny-cnn-hexagon-guest-boot-20260511-security-stall-route.log`. |

## Current classification

- SMMU-COMP-050 remains a **functional slice**.
- This closes the modeled stale-current-security-state bug in the full EVENTQ
  stall-buffer/redrive path.
- Remaining blockers still include separate Secure/Non-secure EVENTQ memory
  banks, secure stream-table banking, `NSCFG`/`S_S2TTB` selection, full RME/GPT
  routing, complete event matrix parity, and upstream Linux `arm-smmu-v3`
  recovery parity.
