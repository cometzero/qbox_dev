# QBox SMMUv3 IDR0 ATS/PRI advertisement verification (2026-05-11)

This report captures the SMMU-COMP-020/060 IDR0 ATS/PRI advertisement slice.

## Scope

The bounded slice aligns the guest-visible `SMMU_IDR0` feature bits with the
modeled ATS/PRI command and queue support already present in the Apollo TBU.
The model now advertises `IDR0.ATS` and `IDR0.PRI`, keeps explicit helper gates
for unsupported `CMD_ATC_INV` and `CMD_PRI_RESP` configurations, and updates the
Apollo Linux selftest expectation to the new architected IDR0 value.

Implemented/verified behavior:

- `ARCH_IDR0_ATS` and `ARCH_IDR0_PRI` are explicit feature-bit constants.
- `ARCH_IDR0` now includes ATS, PRI, ATSRECERR, and MSI feature bits.
- `arch_ats_supported()` and `arch_pri_supported()` gate modeled ATC/PRI command
  legality checks.
- Non-secure and Secure CMDQ paths keep explicit `CERROR_ILL` failure reasons for
  unsupported ATC/PRI command configurations.
- Apollo Linux probe expects `APOLLO_SMMUV3_ARCH_IDR0 == 0x0181a705`.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  - `§4.5.1 CMD_ATC_INV` is tied to `SMMU_IDR0.ATS` support.
  - `§4.5.2 CMD_PRI_RESP` is tied to `SMMU_IDR0.PRI` support.
- `sources/linux/drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.h`
  - `IDR0_ATS` is bit 10 and `IDR0_PRI` is bit 16 in upstream Linux.

## Static evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `ARCH_IDR0_ATS`
  - `ARCH_IDR0_PRI`
  - `arch_ats_supported()`
  - `arch_pri_supported()`
  - `pri-resp-unsupported`
  - `atc-inv-unsupported`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `ArchitectedIdr0AdvertisesAtsPri`
- `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c`
  - `APOLLO_SMMUV3_ARCH_IDR0 0x0181a705`

## Verification commands

```bash
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/smmu-idr0-ats-pri-advertisement-build-20260511.log

./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*ArchitectedIdr0AdvertisesAtsPri*:*ArchitectedRegisterMmioSurface*:*SecureCmdPriRespIgnoresSsecAndTargetsNonSecure*' \
  2>&1 | tee build/verification/smmu-idr0-ats-pri-advertisement-gtest-20260511.log

ctest --test-dir sources/qbox/build --output-on-failure -R apollo-smmu-tbu-tests \
  2>&1 | tee build/verification/smmu-idr0-ats-pri-advertisement-ctest-20260511.log

python3 scripts/check_qbox_smmuv3_compliance.py \
  --json build/verification/smmu-idr0-ats-pri-advertisement-static-20260511.json \
  2>&1 | tee build/verification/smmu-idr0-ats-pri-advertisement-static-20260511.log

./scripts/check_buildroot_arm64_lane.sh \
  2>&1 | tee build/verification/smmu-idr0-ats-pri-advertisement-lane-20260511.log
```

## Expected result

The slice remains a functional compliance increment. It does not claim full
SMMUv3 compliance while packet-level PCIe ATS/PRI transport, complete endpoint
ATC recovery, upstream `arm-smmu-v3` lifecycle parity, full RME/GPT/GPC policy,
and complete Secure/Realm lifecycle parity remain open.
