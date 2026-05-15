# QBox SMMUv3 security-state EVENTQ routing verification (2026-05-11)

## Scope

SMMU-COMP-050 security-state EVENTQ routing functional slice.

This slice adds modeled EVENTQ route accounting by endpoint security state. It
covers the existing QBox policy where Non-secure transactions are supported and
Secure/Realm/Root endpoint transactions are rejected before translation with a
modeled `F_UUT` EVENTQ record.

## Implementation summary

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Adds `ARCH_SECURITY_EVENTQ_STATE_SHIFT`/`MASK` status fields.
  - Adds `m_arch_last_event_security_state` plus per-state EVENTQ counters for
    Non-secure, Secure, Realm, and Root routes.
  - Adds `record_arch_eventq_security_route()` and
    `arch_security_eventq_count()` helpers.
  - Tags committed EVENTQ records and redriven stalled EVENTQ records with the
    current modeled endpoint security state.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Extends `UnsupportedSecurityStateIsRejectedBeforeTranslation` so the
    Secure/Realm/Root rejected `F_UUT` events are checked against the matching
    route tag and per-state accounting.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Add static/lane guards for the security-state EVENTQ routing helpers and
    assertions.

## Verification evidence

| Evidence | Command | Result |
| --- | --- | --- |
| QBox component build | `cmake --build sources/qbox/build --target apollo_smmu_tbu apollo-smmu-tbu-tests -j2` | Pass; see `build/verification/smmu-security-eventq-routing-build-20260511.log`. |
| QBox component test | `ctest --test-dir sources/qbox/build -R '^apollo-smmu-tbu-tests$' --output-on-failure` | Pass, `1/1 Test #15: apollo-smmu-tbu-tests ............   Passed`; see `build/verification/smmu-security-eventq-routing-ctest-20260511.log`. |
| Shell syntax | `bash -n scripts/check_buildroot_arm64_lane.sh` and `bash -n scripts/*.sh` | Pass; see `build/verification/smmu-security-eventq-routing-bashn-20260511.log` and `build/verification/smmu-security-eventq-routing-bashn-all-20260511.log`. |
| Python syntax | `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | Pass; see `build/verification/smmu-security-eventq-routing-pycompile-20260511.log`. |
| Static checker | `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/qbox-smmuv3-compliance-security-eventq-routing-final-20260511.json` | Pass, `SUMMARY {"pass": 623}` with `full_smmuv3_compliance=not_claimed`; see `build/verification/smmu-security-eventq-routing-static-final-20260511.log`. |
| Buildroot lane | `./scripts/check_buildroot_arm64_lane.sh` | Pass; see `build/verification/smmu-security-eventq-routing-lane-20260511.log`. |
| Diff hygiene | `git -C sources/qbox diff --check` and `git diff --check` | Pass; see `build/verification/smmu-security-eventq-routing-qbox-diff-check-final-20260511.log` and `build/verification/smmu-security-eventq-routing-superproject-diff-check-final-20260511.log`. |
| QBox guest smoke | `QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260511-security-eventq-routing QBOX_BOOT_TIMEOUT=70 QBOX_IREE_LOGIN_DELAY=24 QBOX_IREE_AFTER_COMMAND_DELAY=24 ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` | Pass; matched `1x1x2x2xf32=[[[54 63][90 99]]]`; see `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-security-eventq-routing.driver.log`, runtime log `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-security-eventq-routing.log`, and boot log `build/verification/qbox-iree-tiny-cnn-hexagon-guest-boot-20260511-security-eventq-routing.log`. |

## Current classification

- SMMU-COMP-050 remains a **functional slice**.
- This narrows the Secure/Realm event-routing blocker by adding modeled route
  tags and accounting for rejected events.
- Remaining blockers include separate Secure/Non-secure EVENTQ memory banks,
  secure stream-table banking, `NSCFG`/`S_S2TTB` selection, full RME/GPT routing,
  and upstream Linux `arm-smmu-v3` recovery parity.
