# QBox SMMUv3 ATS Translated split-stage verification - 2026-05-11

SMMU-COMP-050/060 ATS Translated split-stage unsupported functional slice.

## Scope

This slice verifies QBox's implementation-defined handling for ATS Translated
transactions when `CR0.ATSCHK==1` and `STE.EATS==0b10` split-stage ATS is
selected. QBox does not yet model a transaction protocol that carries Translated
IPA traffic into the TBU for a second-stage-only walk, so the chosen behavior is
an architected rejection:

- the access terminates with an address error,
- private status reports `ARCH_FAULT_TRANSL_FORBIDDEN`,
- an `F_TRANSL_FORBIDDEN` EVENTQ record is pushed,
- `m_arch_last_eats` preserves the decoded `ARCH_STE_EATS_SPLIT` value.

This does not claim true split-stage IPA-to-PA translation, DPT checks,
Secure/Realm routing, GPC ordering, or complete packet-level ATS protocol.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2185`:
  for `STE.EATS==0b10` when inappropriate for the protocol, whether the SMMU
  records `F_TRANSL_FORBIDDEN` and aborts is implementation-defined.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2192`:
  if a split-stage Translated transaction receives a second stage-2 translation
  and faults, the event is recorded like an ordinary transaction. QBox leaves
  this true stage-2 behavior open for a future protocol model.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2233`:
  split-stage address-size and stage-2 translation events appear later in the
  ATS Translated priority list after configuration and EATS/protocol checks.

## Implemented QBox behavior

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Adds `arch_translated_eats_unsupported_by_protocol()` with split-stage
    protocol support disabled for the current QBox TBU model.
  - Rejects `ARCH_STE_EATS_SPLIT` ATS Translated traffic with
    `ARCH_FAULT_TRANSL_FORBIDDEN` and records `F_TRANSL_FORBIDDEN`.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Adds `AtsTranslatedSplitStageUnsupportedRecordsForbidden`.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Add durable static/lane guards for this slice.

## Verification commands and evidence

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmu-tbu-ats-translated-split-stage-build-20260511.log
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure \
  2>&1 | tee build/verification/apollo-smmu-tbu-ats-translated-split-stage-ctest-20260511.log
```

Static/lane verification:

```sh
rm -rf scripts/__pycache__
{
  bash -n scripts/*.sh
  python3 -m py_compile \
    scripts/check_qbox_smmuv3_compliance.py \
    scripts/check_iree_cnn_pipeline_readiness.py \
    scripts/qbox_pty_runner.py
  scripts/check_qbox_smmuv3_compliance.py --self-test-negative \
    --json build/verification/qbox-smmuv3-compliance-ats-translated-split-stage-final-20260511.json
  ./scripts/check_buildroot_arm64_lane.sh
  git diff --check
  git -C sources/qbox diff --check
  git -C sources/linux diff --check
} 2>&1 | tee build/verification/smmu-ats-translated-split-stage-static-final-20260511.log
rm -rf scripts/__pycache__
```

Observed result:

- `build/verification/apollo-smmu-tbu-ats-translated-split-stage-build-20260511.log`
  - `Built target apollo_smmu_tbu`
  - `Built target apollo-smmu-tbu-tests`
- `build/verification/apollo-smmu-tbu-ats-translated-split-stage-ctest-20260511.log`
  - `100% tests passed, 0 tests failed out of 1`
- `build/verification/smmu-ats-translated-split-stage-static-final-20260511.log`
  - `PASS  tbu:ats-translated-split-stage-unsupported`
  - `PASS: QBox Apollo SMMU TBU ATS Translated split-stage unsupported component test present`
  - `SUMMARY {"pass": 437}`
- `build/verification/qbox-smmuv3-compliance-ats-translated-split-stage-final-20260511.json`
  - `summary.pass = 437`
  - `classification.full_smmuv3_compliance = not_claimed`

## Current limitation

This is a narrow implementation-defined protocol-unsuitable slice. Full
split-stage ATS support still requires a Translated IPA protocol model,
stage-2-only translation for EATS_SPLIT traffic, DPT/GPC interactions,
Secure/Realm routing, and upstream recovery parity.
