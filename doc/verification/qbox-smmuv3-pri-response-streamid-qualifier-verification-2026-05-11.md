# QBox SMMUv3 PRI response StreamID qualifier verification (2026-05-11)

This report captures the SMMU-COMP-060 PRI response StreamID qualifier slice.

## Scope

The bounded slice tightens `CMD_PRI_RESP` matching beyond PRG-only completion.
When the modeled command word carries a non-zero StreamID qualifier, the Apollo
TBU now treats the response as matching only a pending PRI request with both the
named PRG and the same StreamID. This prevents an out-of-order software response
from clearing a different stream's pending PRG that happens to share the command
path.

Implemented/verified behavior:

- Non-zero `cmdq_stream_id(word0)` is passed to `complete_prg()` as a modeled
  StreamID qualifier.
- A PRG match with a different StreamID leaves the pending request intact.
- The mismatch path records `last_pri_response_stream_mismatch` and the command
  StreamID in `last_pri_response_cmd_stream_id`.
- A later response with the correct StreamID clears the pending PRG and records
  normal completion metadata.
- Legacy command words with StreamID zero remain compatibility wildcards for the
  existing tests and guest-facing slices.

## Static evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_arch_core.h`
  - `last_pri_response_stream_mismatch`
  - `last_pri_response_cmd_stream_id`
- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `complete_prg(..., stream_id_valid, response_stream_id)`
  - `cmdq_stream_id(word0) != 0`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `CmdPriRespHonorsStreamIdQualifier`

## Verification commands

```bash
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)" \
  2>&1 | tee build/verification/smmu-pri-response-streamid-qualifier-build-20260511.log

./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*CmdPriRespHonorsStreamIdQualifier*:*CmdPriRespMatchesExactPrgOutOfOrder*:*CmdPriRespUnknownPrgIsAccounted*' \
  2>&1 | tee build/verification/smmu-pri-response-streamid-qualifier-gtest-20260511.log

ctest --test-dir sources/qbox/build --output-on-failure -R apollo-smmu-tbu-tests \
  2>&1 | tee build/verification/smmu-pri-response-streamid-qualifier-ctest-20260511.log

python3 scripts/check_qbox_smmuv3_compliance.py \
  --json build/verification/smmu-pri-response-streamid-qualifier-static-20260511.json \
  2>&1 | tee build/verification/smmu-pri-response-streamid-qualifier-static-20260511.log

./scripts/check_buildroot_arm64_lane.sh \
  2>&1 | tee build/verification/smmu-pri-response-streamid-qualifier-lane-20260511.log
```

## Expected result

The slice remains a functional compliance increment. It does not claim full
SMMUv3 compliance while packet-level PCIe ATS/PRI transport, complete ATC
recovery, upstream `arm-smmu-v3` lifecycle parity, full RME/GPT/GPC policy, and
complete Secure/Realm lifecycle parity remain open.
