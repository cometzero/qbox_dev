# QBox SMMUv3 conflict diagnostic payload verification (2026-05-11)

## Scope

SMMU-COMP-050 EVENTQ conflict diagnostic payload functional slice.

This slice covers modeled implementation-defined `F_TLB_CONFLICT` and
`F_CFG_CONFLICT` EVENTQ word3 Reason payloads. It extends the prior event-number
plumbing and the TLB/config-cache conflict recovery probes so conflict records no
longer carry a zero diagnostic word in QBox's modeled implementation-defined
payload field.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  describes `F_TLB_CONFLICT` and `F_CFG_CONFLICT` records as carrying
  implementation-defined conflict fields.
- `sources/smmu/cpp/include/smmu/types.h` pins the event numbers
  `F_TLB_CONFLICT = 0x20` and `F_CFG_CONFLICT = 0x21` used by QBox tests.

## Implementation summary

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_arch_core.h`
  - Adds modeled implementation-defined Reason constants:
    `EVENT_CONFLICT_REASON_TLB_TAG_MISMATCH` and
    `EVENT_CONFLICT_REASON_CFG_STE_CONT`.
  - Adds `event_record_has_conflict_reason()` and
    `event_record_conflict_reason()` helpers.
  - Routes `EVENT_F_TLB_CONFLICT` and `EVENT_F_CFG_CONFLICT` through those
    helpers in `event_record_word3()`.
- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Exposes compatibility aliases
    `ARCH_EVENT_CONFLICT_REASON_TLB_TAG_MISMATCH` and
    `ARCH_EVENT_CONFLICT_REASON_CFG_STE_CONT` for component vectors and static
    lane checks.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Extends `ArchitectedConflictEventsAreMapped`,
    `AtsCacheConflictProbeRecordsAndRecovers`, and
    `ConfigCacheConflictProbeRecordsAndRecovers` to verify the modeled word3
    Reason payloads.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Add static/lane guards for the diagnostic constants and test coverage.

## Verification evidence

| Evidence | Command | Result |
| --- | --- | --- |
| QBox component build | `cmake --build sources/qbox/build --target apollo_smmu_tbu apollo-smmu-tbu-tests -j2` | Pass; see `build/verification/smmu-conflict-diagnostic-payload-build-20260511.log`. |
| QBox component test | `ctest --test-dir sources/qbox/build -R '^apollo-smmu-tbu-tests$' --output-on-failure` | Pass, `1/1 Test #15: apollo-smmu-tbu-tests ............   Passed`; see `build/verification/smmu-conflict-diagnostic-payload-ctest-20260511.log`. |
| Shell syntax | `bash -n scripts/check_buildroot_arm64_lane.sh` and `bash -n scripts/*.sh` | Pass; see `build/verification/smmu-conflict-diagnostic-payload-bashn-20260511.log` and `build/verification/smmu-conflict-diagnostic-payload-bashn-all-20260511.log`. |
| Python syntax | `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | Pass; see `build/verification/smmu-conflict-diagnostic-payload-pycompile-20260511.log`. |
| Static checker | `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/qbox-smmuv3-compliance-conflict-diagnostic-payload-final2-20260511.json` | Pass, `SUMMARY {"pass": 619}` with `full_smmuv3_compliance=not_claimed`; see `build/verification/smmu-conflict-diagnostic-payload-static-final2-20260511.log`. |
| Buildroot lane | `./scripts/check_buildroot_arm64_lane.sh` | Pass; see `build/verification/smmu-conflict-diagnostic-payload-lane-20260511.log`. |
| QBox guest smoke | `QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260511-conflict-diagnostic-payload QBOX_BOOT_TIMEOUT=70 QBOX_IREE_LOGIN_DELAY=24 QBOX_IREE_AFTER_COMMAND_DELAY=24 ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` | Pass; matched `1x1x2x2xf32=[[[54 63][90 99]]]`; see `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-conflict-diagnostic-payload.driver.log`, runtime log `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-conflict-diagnostic-payload.log`, and boot log `build/verification/qbox-iree-tiny-cnn-hexagon-guest-boot-20260511-conflict-diagnostic-payload.log`. |
| Diff hygiene | `git -C sources/qbox diff --check` and `git diff --check` | Pass; see `build/verification/smmu-conflict-diagnostic-payload-qbox-diff-check-final-20260511.log` and `build/verification/smmu-conflict-diagnostic-payload-superproject-diff-check-final-20260511.log`. |

## Current classification

- SMMU-COMP-050 remains a **functional slice**.
- This closes the local zero-word diagnostic gap for modeled conflict EVENTQ
  records.
- Remaining blockers include broader implementation-specific diagnostic matrix
  parity, full event-priority/security-state coverage, RME/GPT/GPC interaction,
  real-hardware cache-geometry parity, and upstream Linux `arm-smmu-v3` recovery
  parity.
