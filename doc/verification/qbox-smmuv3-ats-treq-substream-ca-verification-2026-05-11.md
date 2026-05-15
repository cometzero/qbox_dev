# QBox SMMUv3 ATS TR substream configuration-fault CA verification (2026-05-11)

Marker: SMMU-COMP-050/060 ATS Translation Request substream CA slice.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2153` defines ATS Translation Request configuration errors as Completer Abort (`CA`) completions.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2158` lists `C_BAD_SUBSTREAMID` and `F_STREAM_DISABLED` among configuration errors that terminate ATS Translation Requests with `CA`, with the event recorded when `SMMU_CR2.REC_CFG_ATS==1`.
- `sources/smmu/TASKS_CPP_OPERATION.md:263` tracks the same CA/event-recording requirement.

## Implementation slice

- Refined `arch_ats_treq_response_code()` so `ARCH_FAULT_STREAM_DISABLED` is only `UR` for the explicit `STE.Config==0` disabled-stream no-event case. `F_STREAM_DISABLED` from S1DSS/CD configuration lookup remains a configuration error and returns `CA`.
- Added `AtsTranslationRequestSubstreamConfigFaultsReturnCa` to cover:
  - out-of-range selected SSID -> `C_BAD_SUBSTREAMID`, `CA`, EVENTQ record;
  - S1DSS `SSID0` with PASID/SSID zero -> `F_STREAM_DISABLED`, `CA`, EVENTQ record.

## Verification commands

Planned/current evidence is captured under `build/verification/smmu-ats-treq-substream-ca-*20260511.log`:

1. `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests`
2. Focused `apollo-smmu-tbu-tests` filter for `AtsTranslationRequestSubstreamConfigFaultsReturnCa` and adjacent ATS config-response tests.
3. `ctest --test-dir sources/qbox/build/tests/components/apollo_smmu_tbu --output-on-failure`
4. `python3 scripts/check_qbox_smmuv3_compliance.py --self-test-negative`
5. `./scripts/check_buildroot_arm64_lane.sh`
6. `bash -n scripts/*.sh`
7. `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py scripts/qbox_pty_runner.py`
8. `git diff --check`

## Scope and remaining gaps

This is a bounded configuration-error matrix slice. It does not claim packet-level ATS Completion Data Entry parity, all REC_CFG_ATS/RECINVSID combinations for every fetch/config error, or full PCIe ATS/PRI protocol compliance.
