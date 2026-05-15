# QBox SMMUv3 STE.Config disabled no-event verification

- Date: 2026-05-11
- Scope: SMMU-COMP-030/050/060 STE.Config disabled no-event functional slice
- Repository: `/build/qbox_dev`

## Result

PASS for this functional slice. The final checker report stays conservative:
`full_smmuv3_compliance=not_claimed`.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  §7.3.7 states that when `STE.V==1` and `STE.Config==0b000`, incoming
  traffic is terminated without recording an event.
- `sources/smmu/wiki/synthesis/smmu-translation-pipeline.md` §15.2 records the
  ATS Translation Request rule: `STE.Config==0b000` returns Unsupported Request
  status and records no Event queue entry.

## Implemented scope

- `apollo_smmu_tbu` now accepts valid `STE.Config==0b000` as a modeled disabled
  stream rather than classifying it as an illegal STE encoding.
- The stream/context walk path sets `ARCH_FAULT_STREAM_DISABLED` for visibility
  but raises `m_arch_fault_record_suppressed`, so probe and negative replay paths
  do not push EVENTQ records for this architected no-event case.
- ATS Translation Requests with valid `STE.Config==0b000` now return modeled UR
  status and no EVENTQ record.
- `ArchitectedConfigDisabledSuppressesEvents` verifies the non-ATS no-event path.
- `AtsConfigDisabledReturnsUrWithoutEvent` verifies the ATS UR/no-event path.

## Validation commands and evidence

```bash
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmu-tbu-config-disabled-no-event-build-20260511.log
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure \
  2>&1 | tee build/verification/apollo-smmu-tbu-config-disabled-no-event-ctest-20260511.log
{
  bash -n scripts/*.sh
  python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py \
    scripts/check_iree_cnn_pipeline_readiness.py scripts/qbox_pty_runner.py
  scripts/check_qbox_smmuv3_compliance.py --self-test-negative \
    --json build/verification/qbox-smmuv3-compliance-config-disabled-no-event-final-20260511.json
  ./scripts/check_buildroot_arm64_lane.sh
  git diff --check
  git -C sources/qbox diff --check
  git -C sources/linux diff --check
} 2>&1 | tee build/verification/smmu-config-disabled-no-event-static-final-20260511.log
```

Evidence:

- `build/verification/apollo-smmu-tbu-config-disabled-no-event-build-20260511.log`
  - `Built target apollo_smmu_tbu`
  - `Built target apollo-smmu-tbu-tests`
- `build/verification/apollo-smmu-tbu-config-disabled-no-event-ctest-20260511.log`
  - `100% tests passed, 0 tests failed out of 1`
- `build/verification/smmu-config-disabled-no-event-static-final-20260511.log`
  - `PASS  tbu:config-disabled-no-event`
  - `SUMMARY {"pass": 407}`
  - `Lane conclusion: Buildroot owns rootfs/DTB generation only; Linux Image comes from sources/linux, and libqemu comes from sources/qemu.`
- `build/verification/qbox-smmuv3-compliance-config-disabled-no-event-final-20260511.json`
  - `summary = {"pass": 407}`
  - `classification.full_smmuv3_compliance = not_claimed`

## Remaining blockers

This is not full disabled-stream/EventQ compliance. Remaining work includes exact
priority ordering against every other detected event, event merging (`MEV`) rules,
full Secure/Realm stream-state routing, packet-level PCIe/CXL attribute coverage,
and upstream Linux event-thread recovery parity.
