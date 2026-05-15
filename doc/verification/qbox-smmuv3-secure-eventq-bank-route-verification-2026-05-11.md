# QBox SMMUv3 configured Secure EVENTQ bank route verification (2026-05-11)

## Scope

SMMU-COMP-050 configured Secure EVENTQ bank route.

SMMU-COMP-050 security-state EVENTQ routing follow-up slice.

This slice extends the existing logical per-security-state EVENTQ bank mirror so
that a modeled Secure EVENTQ route can be explicitly configured with its own
queue state. When a Secure-tagged transaction is rejected by the current
Non-secure-only QBox security model, the emitted `F_UUT` record is written to
the configured Secure Event queue bank instead of advancing the Non-secure
`m_eventq` producer.

This is still a functional slice, not full Secure SMMUv3/RME support. Remaining
blockers include guest-visible Secure queue register banking, Secure/Non-secure
stream-table banking, `NSCFG` and `S2TTB` versus `S_S2TTB` selection, full
RME/GPT/GPC behavior, full event matrix parity, and upstream Linux
`arm-smmu-v3` recovery parity.

## Code changes

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `arch_security_eventq_bank` now owns an optional `arch_queue` plus
    `queue_configured` and `routed_to_separate_queue` state.
  - `configure_arch_security_eventq_bank()` configures a modeled per-security
    EVENTQ bank for component and future register-banking paths.
  - `arch_eventq_for_security_state()` selects the configured Secure/Realm/Root
    queue when available, otherwise preserves the existing Non-secure EVENTQ
    behavior.
  - normal and stalled EVENTQ record push/redrive paths now route through that
    selected queue while preserving security-state accounting.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `SecureEventsUseConfiguredEventqBank` verifies a Secure rejected event is
    written to `secure_eventq_base`, leaves `m_eventq.prod` at zero, and records
    `bank.routed_to_separate_queue`.
- `scripts/check_qbox_smmuv3_compliance.py`
  - adds `tbu:security-eventq-separate-bank-route`.
- `scripts/check_buildroot_arm64_lane.sh`
  - adds lane guards for the configured Secure EVENTQ bank route and component
    assertion.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Build | `build/verification/smmu-secure-eventq-bank-route-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused CTest | `build/verification/smmu-secure-eventq-bank-route-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Shell syntax | `build/verification/smmu-secure-eventq-bank-route-bashn-20260511.log` | PASS |
| Python syntax | `build/verification/smmu-secure-eventq-bank-route-pycompile-20260511.log` | PASS |
| Static checker | `build/verification/smmu-secure-eventq-bank-route-static-20260511.log` and `build/verification/qbox-smmuv3-compliance-secure-eventq-bank-route-20260511.json` | PASS: `SUMMARY {"pass": 628}` and `full_smmuv3_compliance=not_claimed` |
| Lane contract | `build/verification/smmu-secure-eventq-bank-route-lane-20260511.log` | PASS |
| Guest regression | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-secure-eventq-bank-route.driver.log` | PASS: tiny-CNN output matched `1x1x2x2xf32=[[[54 63][90 99]]]` |

## Stop condition

The configured Secure EVENTQ bank route is implemented and verified as a narrow
security-state EVENTQ routing improvement. The aggregate SMMUv3 compliance goal
must remain open because the static checker still classifies the repository as
`full_smmuv3_compliance=not_claimed`.
