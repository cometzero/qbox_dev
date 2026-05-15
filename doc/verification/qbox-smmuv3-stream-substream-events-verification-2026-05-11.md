# QBox SMMUv3 stream/substream EVENTQ verification

- Date: 2026-05-11
- Scope: SMMU-COMP-030/050 stream/substream EVENTQ functional slice
- Repository: `/build/qbox_dev`

## Result

PASS for this functional slice. The final checker report stays conservative:
`full_smmuv3_compliance=not_claimed`.

## Ground truth

- `sources/smmu/cpp/include/smmu/types.h` names `F_STREAM_DISABLED = 0x06`
  and `C_BAD_SUBSTREAMID = 0x08`.
- `sources/smmu/wiki/concepts/event-queue.md` describes
  `F_STREAM_DISABLED` for S1DSS substream mismatches and
  `C_BAD_SUBSTREAMID` for out-of-range SubstreamID cases.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  sections 7.3.7 and 7.3.9 define the corresponding event causes.

## Implemented scope

- `ARCH_FAULT_STREAM_DISABLED` maps modeled S1DSS stream-disabled descriptor
  faults to `ARCH_EVENT_F_STREAM_DISABLED` (`0x06`).
- `ARCH_FAULT_BAD_SUBSTREAMID` maps modeled SubstreamID range/policy descriptor
  faults to `ARCH_EVENT_C_BAD_SUBSTREAMID` (`0x08`).
- `ArchitectedStreamDisabledAndBadSubstreamEvents` checks emitted EVENTQ event
  numbers plus StreamID and SubstreamID fields for the two modeled cases.

## Validation commands and evidence

```bash
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmu-tbu-stream-substream-build-20260511.log
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure \
  2>&1 | tee build/verification/apollo-smmu-tbu-stream-substream-ctest-20260511.log
{
  bash -n scripts/*.sh
  python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py \
    scripts/check_iree_cnn_pipeline_readiness.py scripts/qbox_pty_runner.py
  scripts/check_qbox_smmuv3_compliance.py --self-test-negative \
    --json build/verification/qbox-smmuv3-compliance-stream-substream-final-20260511.json
  ./scripts/check_buildroot_arm64_lane.sh
  git diff --check
  git -C sources/qbox diff --check
  git -C sources/linux diff --check
} 2>&1 | tee build/verification/smmu-stream-substream-static-final-20260511.log
```

Evidence:

- `build/verification/apollo-smmu-tbu-stream-substream-build-20260511.log`
  - `Built target apollo_smmu_tbu`
  - `Built target apollo-smmu-tbu-tests`
- `build/verification/apollo-smmu-tbu-stream-substream-ctest-20260511.log`
  - `100% tests passed, 0 tests failed out of 1`
- `build/verification/smmu-stream-substream-static-final-20260511.log`
  - `PASS  tbu:event-record-stream-substream`
  - `SUMMARY {"pass": 383}`
  - `Lane conclusion: Buildroot owns rootfs/DTB generation only; Linux Image comes from sources/linux, and libqemu comes from sources/qemu.`
- `build/verification/qbox-smmuv3-compliance-stream-substream-final-20260511.json`
  - `summary = {"pass": 383}`
  - `classification.full_smmuv3_compliance = not_claimed`

## Remaining blockers

This is not full Arm SMMUv3 EVENTQ compliance. The slice does not yet prove
Config==0 no-event behavior, all PASID/ATS Translated variants, Secure event
queue/security-state routing, full RME/GPT/GPC behavior, full event-priority
matrix parity, or upstream Linux arm-smmu-v3 recovery lifecycle parity.
