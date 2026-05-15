# QBox SMMUv3 ATS Translated PASIDTT verification - 2026-05-11

SMMU-COMP-050/060 ATS Translated PASIDTT disabled functional slice.

## Scope

This slice verifies that QBox clears PASID-prefix-derived attributes for ATS
Translated transactions while `SMMU_IDR3.PASIDTT==0`. If an endpoint still
supplies TLM SubstreamID/PnU/InD metadata on a Translated transaction, the event
record path now treats the transaction as:

- `SSV=0`,
- `SSID=0`,
- `PnU=0`,
- `InD=0`.

This does not claim PASIDTT=1 support, packet-level PASID TLP prefix decoding,
MPAM, or complete PCIe PASID lifecycle behavior.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2196`:
  when `SMMU_IDR3.PASIDTT==0` or the ATS Translated transaction lacks a PASID
  TLP prefix, the transaction is treated with `PnU==0`, `InD==0`, and `SSV==0`.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2197`:
  PnU/InD are taken from the Translated transaction only when PASIDTT is
  supported and a PASID prefix is present.

## Implemented QBox behavior

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Adds `arch_pasidtt_supported()` for the current no-PASIDTT model.
  - Sanitizes ATS Translated event-record inputs so supplied SubstreamID,
    privileged, and instruction metadata are ignored while PASIDTT is disabled.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Adds `AtsTranslatedPasidttDisabledClearsPrefixAttrs`.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Add durable static/lane guards for this slice.

## Verification commands and evidence

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmu-tbu-ats-translated-pasidtt-build-20260511.log
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure \
  2>&1 | tee build/verification/apollo-smmu-tbu-ats-translated-pasidtt-ctest-20260511.log
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
    --json build/verification/qbox-smmuv3-compliance-ats-translated-pasidtt-final-20260511.json
  ./scripts/check_buildroot_arm64_lane.sh
  git diff --check
  git -C sources/qbox diff --check
  git -C sources/linux diff --check
} 2>&1 | tee build/verification/smmu-ats-translated-pasidtt-static-final-20260511.log
rm -rf scripts/__pycache__
```

Observed result:

- `build/verification/apollo-smmu-tbu-ats-translated-pasidtt-build-20260511.log`
  - `Built target apollo_smmu_tbu`
  - `Built target apollo-smmu-tbu-tests`
- `build/verification/apollo-smmu-tbu-ats-translated-pasidtt-ctest-20260511.log`
  - `100% tests passed, 0 tests failed out of 1`
- `build/verification/smmu-ats-translated-pasidtt-static-final-20260511.log`
  - `PASS  tbu:ats-translated-pasidtt-disabled-prefix-clear`
  - `PASS: QBox Apollo SMMU TBU ATS Translated PASIDTT disabled component test present`
  - `SUMMARY {"pass": 446}`
- `build/verification/qbox-smmuv3-compliance-ats-translated-pasidtt-final-20260511.json`
  - `summary.pass = 446`
  - `classification.full_smmuv3_compliance = not_claimed`

## Current limitation

This is a narrow PASIDTT-disabled sanitization slice. Full PASIDTT support still
requires advertising PASIDTT=1, packet-level PASID prefix decoding, MPAM, and
complete PCIe PASID lifecycle behavior.
