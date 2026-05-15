# QBox SMMUv3 configuration-cache conflict recovery verification (2026-05-11)

## Scope

SMMU-COMP-050 configuration-cache conflict recovery functional slice.

SMMU-COMP-050 functional slice for modeled STE configuration-cache conflict
recovery. This covers implementation-defined `F_CFG_CONFLICT` detection for a
stale same-security overlapping STE span and recovery by invalidating the stale
configuration-cache entry. It does not claim full real-hardware
configuration-cache geometry, Secure/Realm event routing, RME/GPT/GPC behavior,
or upstream Linux `arm-smmu-v3` recovery parity.

## Reference grounding

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  describes `STE.CONT` configuration-cache spans and permits an implementation
  to abort with `F_CFG_CONFLICT` when overlapping non-identical STE cache
  matches are detected.
- The same section states configuration-cache conflicts must not cause an STE to
  be treated as associated with a different Security state. The QBox slice
  models that by making conflict matching security-state scoped.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Added `ARCH_CTRL_CFG_CONFLICT` probe control.
  - Added `arch_config_cache_entry` and a small modeled STE configuration cache.
  - Added `config_cache_conflict_present()` over StreamID span, security state,
    and STE words.
  - Added `record_config_cache_conflict_if_present()` to emit modeled
    `F_CFG_CONFLICT`, clear stale overlapping entries, and count recovery.
  - CFGI paths now clear the modeled configuration cache together with existing
    ATS/VMS modeled invalidation state.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Added `ConfigCacheConflictProbeRecordsAndRecovers` to verify event number,
    StreamID, InputAddr, stale-entry recovery, recovery accounting, and
    security-state isolation.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Added static/lane gates for the modeled configuration-cache conflict
    recovery slice.
- `doc/spec/qbox-smmuv3-compliance-checklist.md` and
  `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`
  - Updated the SMMU-COMP-050 claim boundary and remaining blockers.

## Verification evidence

| Evidence | Command | Result |
| --- | --- | --- |
| QBox component build | `cmake --build sources/qbox/build --target apollo_smmu_tbu apollo-smmu-tbu-tests -j2` | Pass; see `build/verification/smmu-config-cache-conflict-build-20260511.log`. |
| QBox component test | `ctest --test-dir sources/qbox/build -R '^apollo-smmu-tbu-tests$' --output-on-failure` | Pass, `1/1 Test #15: apollo-smmu-tbu-tests ............   Passed`; see `build/verification/smmu-config-cache-conflict-ctest-20260511.log`. |
| Shell syntax | `bash -n scripts/check_buildroot_arm64_lane.sh` and `bash -n scripts/*.sh` | Pass; see `build/verification/smmu-config-cache-conflict-bashn-20260511.log` and `build/verification/smmu-config-cache-conflict-bashn-all-20260511.log`. |
| Python syntax | `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | Pass; see `build/verification/smmu-config-cache-conflict-pycompile-20260511.log`. |
| Static checker | `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/qbox-smmuv3-compliance-config-cache-conflict-20260511.json` | Pass, `SUMMARY {"pass": 615}` with `full_smmuv3_compliance=not_claimed`; see `build/verification/smmu-config-cache-conflict-static-20260511.log`. |
| Buildroot lane | `./scripts/check_buildroot_arm64_lane.sh` | Pass; see `build/verification/smmu-config-cache-conflict-lane-20260511.log`. |
| QBox guest smoke | `QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260511-config-cache-conflict QBOX_BOOT_TIMEOUT=70 QBOX_IREE_LOGIN_DELAY=24 QBOX_IREE_AFTER_COMMAND_DELAY=24 ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` | Pass; matched `1x1x2x2xf32=[[[54 63][90 99]]]`; see `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-config-cache-conflict.driver.log` and runtime log `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-config-cache-conflict.log`. |

## Current classification

- SMMU-COMP-050 remains a **functional slice**.
- Modeled configuration-cache conflict detection and stale-entry recovery are
  now covered for a same-security overlapping STE span.
- Remaining blockers include broader implementation-specific diagnostic matrix
  parity, Secure/Realm event routing, full real-hardware configuration-cache
  geometry, RME/GPT/GPC interactions, and upstream Linux `arm-smmu-v3`
  recovery parity.
