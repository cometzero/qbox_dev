# QBox SMMUv3 PRI PPR ATSCHK/EATS independence verification (2026-05-11)

This report captures the SMMU-COMP-060 PRI PPR ATSCHK/EATS independence slice.

## Scope

The slice documents and verifies the SMMUv3 rule that incoming PRI Page Request
messages are not controlled by `SMMU_CR0.ATSCHK` or `STE.EATS`. Those fields
control ATS Translation Request and ATS Translated transaction handling, while a
normal PPR is queued to PRIQ whenever PRI is enabled and not blocked by Secure
stream, abort, or overflow handling.

Implemented/verified behavior:

- The Apollo TBU PRIQ enqueue path explicitly documents that PPR handling is
  independent of `CR0.ATSCHK` and `STE.EATS`.
- `STE.PPAR` lookup remains limited to the overflow auto-response path.
- Component coverage proves a PPR is queued with `ATSCHK==0` and again with
  `ATSCHK==1` while the selected STE keeps `EATS==0b00`, without creating an
  auto-response or consulting STE.PPAR.

## Ground truth

- `sources/smmu/wiki/concepts/pcie-ats-pri.md`
  - “Incoming PPRs are not affected by `SMMU_CR0.ATSCHK` or `STE.EATS`
    configuration.”
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  - §3.9 covers ATS/PRI configuration and separates PRI queue handling from the
    ATS Translation Request/Translated transaction gates.

## Static evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `Incoming PRI Page Request messages are a PRI-side protocol input`
  - `not gated by CR0.ATSCHK`
  - `only consult STE.PPAR on the architected overflow auto-response path`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `PriProtocolPprIgnoresAtschkAndSteEats`

## Verification commands

```bash
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/smmu-pri-ppr-atschk-eats-independence-build-20260511.log

./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*PriProtocolPprIgnoresAtschkAndSteEats*:*PriProtocolPprFieldsStopMarkerAndNonLastDiscard*:*PriProtocolOverflowUsesStePparForPasidAutoResponse*' \
  2>&1 | tee build/verification/smmu-pri-ppr-atschk-eats-independence-gtest-20260511.log

ctest --test-dir sources/qbox/build --output-on-failure -R apollo-smmu-tbu-tests \
  2>&1 | tee build/verification/smmu-pri-ppr-atschk-eats-independence-ctest-20260511.log

python3 scripts/check_qbox_smmuv3_compliance.py \
  --json build/verification/smmu-pri-ppr-atschk-eats-independence-static-20260511.json \
  2>&1 | tee build/verification/smmu-pri-ppr-atschk-eats-independence-static-20260511.log

./scripts/check_buildroot_arm64_lane.sh \
  2>&1 | tee build/verification/smmu-pri-ppr-atschk-eats-independence-lane-20260511.log
```

## Expected result

The slice remains a modeled PRI protocol increment. It does not claim full
SMMUv3 ATS/PRI compliance while packet-level PCIe ATS/PRI transport, endpoint
ATC completion/recovery ordering, broader Secure/Realm/RME/GPT/GPC policy, and
upstream `arm-smmu-v3` lifecycle parity remain open.
