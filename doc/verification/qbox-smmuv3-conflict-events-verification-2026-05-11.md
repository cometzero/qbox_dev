# QBox SMMUv3 EVENTQ conflict events verification

- Date: 2026-05-11
- Scope: SMMU-COMP-050 EVENTQ conflict events functional slice
- Repository: `/build/qbox_dev`

## Result

PASS for this functional slice. The final checker report stays conservative:
`full_smmuv3_compliance=not_claimed`.

## Ground truth

- `sources/smmu/cpp/include/smmu/types.h` defines `F_TLB_CONFLICT = 0x20`
  and `F_CFG_CONFLICT = 0x21` as the architected event numbers for §7.3.17
  and §7.3.18.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  §7.3.17 says detected TLB conflicts abort the transaction and attempt to
  record `F_TLB_CONFLICT` with implementation-defined fields.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  §7.3.18 says detected configuration-cache conflicts abort the transaction and
  attempt to record `F_CFG_CONFLICT` with implementation-defined fields.
- `sources/smmu/wiki/concepts/tlb-invalidation.md` summarizes the same detected
  conflict behavior and records that the event entries carry implementation
  defined diagnostics.

## Implemented scope

- `apollo_smmu_tbu` now has modeled fault reasons for TLB and configuration-cache
  conflict reports.
- `arch_event_number_for_fault()` maps those modeled reasons to
  `ARCH_EVENT_F_TLB_CONFLICT = 0x20` and `ARCH_EVENT_F_CFG_CONFLICT = 0x21`.
- `ArchitectedConflictEventsAreMapped` verifies both event numbers, StreamID,
  InputAddr, implementation-defined diagnostic word, and private reason
  detail.

Follow-up note: the conflict diagnostic payload slice now assigns modeled
implementation-defined word3 Reason payloads to those records; see
`doc/verification/qbox-smmuv3-conflict-diagnostic-payload-verification-2026-05-11.md`.

This slice intentionally does **not** detect real multi-hit TLB/config-cache
conflicts. It only wires implementation-defined conflict reasons into the
architected EVENTQ event-number path so later cache-conflict detection can emit
spec-numbered records.

## Validation commands and evidence

```bash
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmu-tbu-conflict-events-build-20260511.log
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure \
  2>&1 | tee build/verification/apollo-smmu-tbu-conflict-events-ctest-20260511.log
{
  bash -n scripts/*.sh
  python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py \
    scripts/check_iree_cnn_pipeline_readiness.py scripts/qbox_pty_runner.py
  scripts/check_qbox_smmuv3_compliance.py --self-test-negative \
    --json build/verification/qbox-smmuv3-compliance-conflict-events-final-20260511.json
  ./scripts/check_buildroot_arm64_lane.sh
  git diff --check
  git -C sources/qbox diff --check
  git -C sources/linux diff --check
} 2>&1 | tee build/verification/smmu-conflict-events-static-final-20260511.log
```

Evidence:

- `build/verification/apollo-smmu-tbu-conflict-events-build-20260511.log`
  - `Built target apollo_smmu_tbu`
  - `Built target apollo-smmu-tbu-tests`
- `build/verification/apollo-smmu-tbu-conflict-events-ctest-20260511.log`
  - `100% tests passed, 0 tests failed out of 1`
- `build/verification/smmu-conflict-events-static-final-20260511.log`
  - `PASS  tbu:event-record-conflict-events`
  - `SUMMARY {"pass": 399}`
  - `Lane conclusion: Buildroot owns rootfs/DTB generation only; Linux Image comes from sources/linux, and libqemu comes from sources/qemu.`
- `build/verification/qbox-smmuv3-compliance-conflict-events-final-20260511.json`
  - `summary = {"pass": 399}`
  - `classification.full_smmuv3_compliance = not_claimed`

## Remaining blockers

This is not full conflict compliance. Actual detection of TLB multi-hit
conditions, configuration-cache conflict detection/recovery, broader
implementation-specific diagnostic matrix coverage, event priority ordering
versus all other fault classes, Secure-state routing, RME/GPT/GPC interactions,
and upstream Linux event-thread recovery parity remain open.
