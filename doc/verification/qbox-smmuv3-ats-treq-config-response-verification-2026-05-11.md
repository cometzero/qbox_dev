# QBox SMMUv3 ATS Translation Request config-response verification (2026-05-11)

## Scope

SMMU-COMP-050/060 ATS Translation Request config-response slice.

This slice separates ATS Translation Request response coding from the older
compatibility probe response helper.  For ATS Translation Requests, modeled
configuration lookup faults now return Completer Abort (CA), while explicit
`F_BAD_ATS_TREQ` protocol/config-abort cases still return Unsupported Request
(UR).  The `STE.Config==0b100` abort encoding is rejected before normal stream
translation and records `F_BAD_ATS_TREQ`.

Reference grounding:

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  lines 2138, 2153, 2157, and 2158 define UR for `STE.Config==0b100`/
  `F_BAD_ATS_TREQ` and CA for ATS Translation Request configuration errors such
  as `C_BAD_STREAMID`, `F_STE_FETCH`, `C_BAD_STE`, `F_CD_FETCH`, and `C_BAD_CD`.
- `sources/smmu/TASKS_CPP_OPERATION.md` lines 258, 261, 262, and 263 track the
  same response-code requirements.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Adds `arch_ats_treq_response_code()` and `log_arch_ats_treq_response()`.
  - Routes ATS Translation Request configuration/fetch failures through the
    ATS-specific CA/UR response selection.
  - Rejects `STE.Config==0b100` through `ats-config-abort` before treating the
    descriptor as a bypass stream.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Adds `AtsTranslationRequestConfigFaultsUseArchitectedResponses`, covering
    `C_BAD_STREAMID -> CA` and `STE.Config==0b100 -> UR/F_BAD_ATS_TREQ`.

## Verification commands

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests
sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*AtsTranslationRequestConfigFaultsUseArchitectedResponses*:*AtsTranslationRequestTranslationFaultReturnsSuccessNoEvent*:*AtsTranslationRequestHonorsCr0AtschkAndSteEats*'
ctest --test-dir sources/qbox/build/tests/components/apollo_smmu_tbu --output-on-failure
python3 scripts/check_qbox_smmuv3_compliance.py --self-test-negative
./scripts/check_buildroot_arm64_lane.sh
```

## No-overclaim boundary

This is a bounded ATS Translation Request response-code slice. It does not
complete the full ATS completion data-entry permission matrix, PCIe T/XT/CXL
metadata, DPT, ECMDQ, RME/GPT/GPC, or upstream Linux `arm-smmu-v3` lifecycle
parity.
