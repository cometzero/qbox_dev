# QBox SMMUv3 ATS Translation Request translation-fault success/no-event verification (2026-05-11)

## Scope

SMMU-COMP-050/060 ATS Translation Request translation-fault success/no-event slice.

This slice aligns QBox with the pinned SMMUv3 reference for ATS Translation
Requests that reach the translation process and hit a page translation fault.
The model now returns a successful ATS completion with no access permissions
(`R==W==0` in the architectural completion data model) and suppresses SMMU
fault/EVENTQ recording. Configuration, fetch, and protocol errors continue to
use the existing UR/CA and `REC_CFG_ATS`-controlled recording paths.

Reference grounding:

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  line 2141: Address Size, Access, or Translation faults on ATS Translation
  Requests complete with Success and `R==W==0` with no SMMU fault recorded.
- `sources/smmu/TASKS_CPP_OPERATION.md` line 260 tracks the same rule as an
  explicit compliance item.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Adds `arch_ats_treq_translation_fault_has_no_smmu_event()`.
  - Converts ATS Translation Request Address Size, Access, Permission, table,
    and page translation faults to a modeled Success response with `R==W==0`.
  - Leaves configuration/fetch/protocol errors on their existing UR/CA paths.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Adds `AtsTranslationRequestTranslationFaultReturnsSuccessNoEvent`, covering
    an AF-clear page Access fault reached through `ARCH_CTRL_ATS_TRANSLATION_REQUEST`.

## Verification commands

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests
sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests \
  --gtest_filter='*AtsTranslationRequestTranslationFaultReturnsSuccessNoEvent*:*AtsTranslationRequestHonorsCr0AtschkAndSteEats*'
ctest --test-dir sources/qbox/build/tests/components/apollo_smmu_tbu --output-on-failure
python3 scripts/check_qbox_smmuv3_compliance.py --self-test-negative
./scripts/check_buildroot_arm64_lane.sh
```

## No-overclaim boundary

This is a bounded ATS Translation Request response-semantics slice. It does not
complete the full ATS completion data-entry permission matrix, ATS NW/write
permission modeling, DPT, ECMDQ, RME/GPT/GPC, or upstream Linux `arm-smmu-v3`
lifecycle parity.
