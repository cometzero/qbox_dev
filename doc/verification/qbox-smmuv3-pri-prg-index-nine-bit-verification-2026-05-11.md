# QBox SMMUv3 PRI PRGIndex 9-bit verification (2026-05-11)

This report captures the SMMU-COMP-060 PRI PRGIndex 9-bit slice.

## Scope

The slice tightens the modeled PRI Page Request Group index handling to the
architected 9-bit PRGIndex field. The Apollo TBU now masks PRGIndex values when
encoding PRIQ PPR records and when decoding `CMD_PRI_RESP`, and the allocator
wraps within the nonzero 9-bit index space while avoiding an already-pending
PRG.

Implemented/verified behavior:

- `ARCH_PRIQ_PPR_PRG_MASK` defines the 9-bit modeled PRGIndex field.
- `arch_prg_index()` is used by PRIQ PPR word3 encoding and CMD_PRI_RESP decode.
- `allocate_prg()` skips index 0 and avoids duplicate pending PRG indices when
  wrapping the 9-bit space.
- Component coverage proves allocation at `0x1ff` wraps through 0 to 1 and that
  a `CMD_PRI_RESP` with bit 9 set still matches the masked 9-bit PRGIndex.

## Ground truth

- `sources/smmu/wiki/concepts/pcie-ats-pri.md`
  - PRI message format lists `PRGIndex[8:0]` for Page Request Groups.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  - Chapter 8 defines PRI queue entries and PRG Response handling for the
    architected PRGIndex field.

## Static evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `ARCH_PRIQ_PPR_PRG_MASK = 0x1ff`
  - `arch_prg_index`
  - `pri_prg_pending`
  - `complete_prg(arch_prg_index(word1)`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `PriProtocolPrgIndexIsNineBitsAndWraps`

## Verification commands

```bash
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/smmu-pri-prg-index-nine-bit-build-20260511.log

./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*PriProtocolPrgIndexIsNineBitsAndWraps*:*PriProtocolPprIgnoresAtschkAndSteEats*:*CmdPriRespHonorsStreamIdQualifier*' \
  2>&1 | tee build/verification/smmu-pri-prg-index-nine-bit-gtest-20260511.log

ctest --test-dir sources/qbox/build --output-on-failure -R apollo-smmu-tbu-tests \
  2>&1 | tee build/verification/smmu-pri-prg-index-nine-bit-ctest-20260511.log

python3 scripts/check_qbox_smmuv3_compliance.py \
  --json build/verification/smmu-pri-prg-index-nine-bit-static-20260511.json \
  2>&1 | tee build/verification/smmu-pri-prg-index-nine-bit-static-20260511.log

./scripts/check_buildroot_arm64_lane.sh \
  2>&1 | tee build/verification/smmu-pri-prg-index-nine-bit-lane-20260511.log
```

## Expected result

The slice remains a modeled PRI protocol increment. It does not claim full
SMMUv3 ATS/PRI compliance while packet-level PCIe ATS/PRI transport, endpoint
ATC completion/recovery ordering, broader Secure/Realm/RME/GPT/GPC policy, and
upstream `arm-smmu-v3` lifecycle parity remain open.
