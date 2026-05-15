# QBox SMMUv3 ATS cache conflict recovery verification (2026-05-11)

## Scope

SMMU-COMP-050 functional slice for modeled ATS/TLB cache-conflict detection and
recovery. This does not claim full configuration-cache conflict parity or full
Arm SMMUv3 event-matrix compliance.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Added `ARCH_CTRL_TLB_CONFLICT` probe control.
  - Added `ats_cache_conflict_present()` over StreamID, page, ASID, VMID, and
    SSID tags.
  - Added `record_ats_cache_conflict_if_present()` to emit modeled
    `F_TLB_CONFLICT` and invalidate stale page entries.
  - Added `m_arch_tlb_conflict_recoveries` recovery accounting.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Added `AtsCacheConflictProbeRecordsAndRecovers` to verify event number,
    StreamID, SSID tagging, InputAddr, stale-entry invalidation, and recovery
    accounting.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Added static/lane gates for the modeled ATS/TLB conflict recovery slice.
- `doc/spec/qbox-smmuv3-compliance-checklist.md` and
  `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`
  - Updated the SMMU-COMP-050 claim boundary and remaining blockers.

## Verification evidence

| Evidence | Command | Result |
| --- | --- | --- |
| QBox component build | `cmake --build sources/qbox/build --target apollo_smmu_tbu apollo-smmu-tbu-tests -j2` | Pass; see `build/verification/smmu-ats-cache-conflict-recovery-build-20260511.log`. |
| QBox component test | `ctest --test-dir sources/qbox/build -R '^apollo-smmu-tbu-tests$' --output-on-failure` | Pass, `1/1 Test #15: apollo-smmu-tbu-tests ............   Passed`; see `build/verification/smmu-ats-cache-conflict-recovery-ctest-20260511.log`. |
| Shell syntax | `bash -n scripts/check_buildroot_arm64_lane.sh` and `bash -n scripts/*.sh` | Pass; see `build/verification/smmu-ats-cache-conflict-recovery-bashn-20260511.log` and `build/verification/smmu-ats-cache-conflict-recovery-bashn-all-20260511.log`. |
| Python syntax | `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | Pass; see `build/verification/smmu-ats-cache-conflict-recovery-pycompile-20260511.log`. |
| Static checker | `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/qbox-smmuv3-compliance-ats-cache-conflict-recovery-20260511.json` | Pass, `SUMMARY {"pass": 611}` with `full_smmuv3_compliance=not_claimed`; see `build/verification/smmu-ats-cache-conflict-recovery-static-20260511.log`. |
| Buildroot lane | `./scripts/check_buildroot_arm64_lane.sh` | Pass; see `build/verification/smmu-ats-cache-conflict-recovery-lane-20260511.log`. |
| QBox guest smoke | `QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260511-ats-cache-conflict-recovery QBOX_BOOT_TIMEOUT=70 QBOX_IREE_LOGIN_DELAY=24 QBOX_IREE_AFTER_COMMAND_DELAY=24 ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` | Pass; matched `1x1x2x2xf32=[[[54 63][90 99]]]`; see `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-ats-cache-conflict-recovery.driver.log` and runtime log `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-ats-cache-conflict-recovery.log`. |

## Current classification

- SMMU-COMP-050 remains a **functional slice**.
- Modeled ATS/TLB conflict detection and stale-entry recovery are now covered.
- Remaining blockers include broader configuration-cache conflict parity,
  implementation-defined diagnostic payload parity, Secure/Realm event routing,
  RME/GPT/GPC interactions, and upstream Linux `arm-smmu-v3` recovery parity.
