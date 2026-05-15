# QBox SMMUv3 GBPA global-bypass verification (2026-05-11)

## Scope

SMMU-COMP-020/030/080 GBPA global-bypass attribute/abort slice.

This slice follows the pinned `sources/smmu` reference for SMMU disabled
behavior: when `SMMU_CR0.SMMUEN==0`, ordinary traffic either bypasses with
`SMMU_GBPA` output attributes or aborts without recording an event when
`SMMU_GBPA.ABORT==1`.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds modeled `SMMU_GBPA` field decode for `ABORT`, `MTCFG`, `MemAttr`,
  `SHCFG`, `ALLOCCFG`, `INSTCFG`, and `PRIVCFG`.
- Disabled-SMMU data-path traffic now records GBPA output attributes alongside
  existing GBPMPAM attributes.
- `GBPA.ABORT` stops the data-path transaction before downstream routing and
  suppresses EVENTQ recording for the disabled-SMMU abort path.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  adds `GlobalBypassUsesGbpaOutputAttributes` and
  `GlobalBypassGbpaAbortSuppressesEvent`.

## Verification evidence

Logs are under `build/verification/` with prefix
`smmu-gbpa-global-bypass-*20260511.*`.

Commands:

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j4
./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*GlobalBypassUsesGbpaOutputAttributes:*GlobalBypassGbpaAbortSuppressesEvent:*GlobalBypassUsesGbpmpamAttributes'
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure
python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/smmu-gbpa-global-bypass-static-20260511.json
./scripts/check_buildroot_arm64_lane.sh
```

## No-overclaim boundary

This is a bounded functional slice. It does not claim identity-address hardware
bus routing for all platform topologies, full Realm/Root GBPA policy, complete
AGBPA behavior, full PCIe attribute parity, or full ARM SMMUv3 compliance. The
static checker must continue to report `full_smmuv3_compliance` as
`not_claimed` until the remaining compliance gaps are implemented and verified.
