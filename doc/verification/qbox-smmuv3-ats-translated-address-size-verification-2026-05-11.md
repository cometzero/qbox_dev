# QBox SMMUv3 ATS Translated address-size verification - 2026-05-11

SMMU-COMP-050/060 ATS Translated address-size functional slice.

## Scope

This slice verifies QBox's implementation-defined handling for ATS Translated
transactions whose address contains bits above the modeled implemented PA size.
The chosen behavior is a deterministic no-event abort:

- the access terminates with an address error,
- QBox private status reports `ARCH_FAULT_ADDR_SIZE`,
- no EVENTQ record is pushed,
- Stream table/configuration lookup is not performed.

This does not claim full `SMMU_IDR5.OAS` modeling, truncate behavior, GPC/DPT
follow-on checks, Secure/Realm routing, or complete packet-level ATS behavior.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2118`:
  ATS Translation Completions and ATS Translated transactions carry a 64-bit
  address field independent of implemented PA size.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2123`:
  behavior for ATS Translated addresses above implemented PA size is
  implementation-defined; one allowed behavior is abort with no event/fault
  record.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2081`:
  `ATSCHK==0` bypasses further checks other than address-size checking.

## Implemented QBox behavior

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Adds `arch_translated_addr_in_oas()` over the existing 48-bit descriptor
    output mask.
  - Rejects oversized ATS Translated addresses before the `ATSCHK==0`
    configuration-lookup bypass.
  - Suppresses EVENTQ/fault queue recording for this implementation-defined
    no-event abort while retaining private status for deterministic tests.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Adds `AtsTranslatedAddressSizeAbortIsNoEvent`.
- `scripts/check_qbox_smmuv3_compliance.py` and
  `scripts/check_buildroot_arm64_lane.sh`
  - Add durable static/lane guards for this slice.

## Verification commands and evidence

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/apollo-smmu-tbu-ats-translated-address-size-build-20260511.log
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure \
  2>&1 | tee build/verification/apollo-smmu-tbu-ats-translated-address-size-ctest-20260511.log
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
    --json build/verification/qbox-smmuv3-compliance-ats-translated-address-size-final-20260511.json
  ./scripts/check_buildroot_arm64_lane.sh
  git diff --check
  git -C sources/qbox diff --check
  git -C sources/linux diff --check
} 2>&1 | tee build/verification/smmu-ats-translated-address-size-static-final-20260511.log
rm -rf scripts/__pycache__
```

Observed result:

- `build/verification/apollo-smmu-tbu-ats-translated-address-size-build-20260511.log`
  - `Built target apollo_smmu_tbu`
  - `Built target apollo-smmu-tbu-tests`
- `build/verification/apollo-smmu-tbu-ats-translated-address-size-ctest-20260511.log`
  - `100% tests passed, 0 tests failed out of 1`
- `build/verification/smmu-ats-translated-address-size-static-final-20260511.log`
  - `PASS  tbu:ats-translated-address-size-no-event`
  - `PASS: QBox Apollo SMMU TBU ATS Translated address-size component test present`
  - `SUMMARY {"pass": 434}`
- `build/verification/qbox-smmuv3-compliance-ats-translated-address-size-final-20260511.json`
  - `summary.pass = 434`
  - `classification.full_smmuv3_compliance = not_claimed`

## Current limitation

This is a narrow implementation-defined address-size slice. Full ATS Translated
compliance still requires OAS register modeling, optional truncation behavior,
GPC/DPT interactions, Secure/Realm routing, and upstream recovery parity.
