# QBox SMMUv3 PRI STE.PPAR bad StreamID RECINVSID verification (2026-05-11)

This report captures the SMMU-COMP-060 PRI STE.PPAR bad StreamID RECINVSID slice.

## Scope

The bounded slice tightens the PRI overflow auto-response path for
PASID-prefixed PPRs when the model must consult STE.PPAR but the StreamID is
outside the configured stream-table range.

Implemented/verified behavior:

- `read_arch_ste_words()` reports `ARCH_FAULT_BAD_STREAM_ID` through the
  stream-table bounds check.
- `record_pri_ppar_lookup_fault()` reuses the architected ATS Translation
  Request bad-StreamID recording rule.
- A PRI STE.PPAR lookup failure caused by bad StreamID records `C_BAD_STREAMID`
  only when both `SMMU_CR2.REC_CFG_ATS` and `SMMU_CR2.RECINVSID` are set.
- With `REC_CFG_ATS=1` and `RECINVSID=0`, the model suppresses the EVENTQ
  record and still returns PRI Response Failure while clearing the pending PRG.
- With both bits set, the model pushes a `C_BAD_STREAMID` EVENTQ record tagged
  with the failing StreamID and still returns PRI Response Failure.

## Static evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `record_pri_ppar_lookup_fault()`
  - `arch_record_bad_streamid_ats_treq()`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `PriProtocolPparBadStreamIdHonorsRecInvsid`

## Verification commands

```bash
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/smmu-pri-ppar-bad-streamid-recinvsid-build-20260511.log

./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*PriProtocolPparBadStreamIdHonorsRecInvsid*:*PriProtocolPparLookupFaultHonorsRecCfgAts*' \
  2>&1 | tee build/verification/smmu-pri-ppar-bad-streamid-recinvsid-gtest-20260511.log

ctest --test-dir sources/qbox/build --output-on-failure -R apollo-smmu-tbu-tests \
  2>&1 | tee build/verification/smmu-pri-ppar-bad-streamid-recinvsid-ctest-20260511.log

python3 scripts/check_qbox_smmuv3_compliance.py \
  --json build/verification/smmu-pri-ppar-bad-streamid-recinvsid-static-20260511.json \
  2>&1 | tee build/verification/smmu-pri-ppar-bad-streamid-recinvsid-static-20260511.log

./scripts/check_buildroot_arm64_lane.sh \
  2>&1 | tee build/verification/smmu-pri-ppar-bad-streamid-recinvsid-lane-20260511.log
```

## Expected result

The slice is a functional compliance increment only. It must not claim full
SMMUv3 compliance while packet-level PCIe ATS/PRI transport, complete upstream
`arm-smmu-v3` recovery parity, full RME/GPT/GPC policy, broader Secure/Realm
lifecycle parity, and upstream lifecycle convergence remain open.
