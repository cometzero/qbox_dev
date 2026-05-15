# QBox SMMUv3 architected SMMU_GATOS register verification (2026-05-11)

## Scope

SMMU-COMP-020/030/080 architected non-secure SMMU_GATOS register slice.

This closes only the non-secure architectural ATOS/GATOS register-group path
needed to drive a translation through `SMMU_GATOS_CTRL.RUN` and read the result
from `SMMU_GATOS_PAR`. It intentionally does not claim full ARM SMMUv3 ATOS
coverage.

## Implementation summary

- Added non-secure PAGE_0 offsets for `SMMUV3_GATOS_CTRL`,
  `SMMUV3_GATOS_SID_LO/HI`, `SMMUV3_GATOS_ADDR_LO/HI`, and
  `SMMUV3_GATOS_PAR_LO/HI` in the Apollo SMMU TBU.
- Added `ARCH_GATOS_CTRL_RUN` and modeled GATOS register state.
- Added `run_arch_gatos_register_translate()` so a RUN write:
  - selects the supplied SID and ADDR,
  - reuses the architectural stream/context/table walker,
  - writes the architected PAR value,
  - clears RUN on completion, and
  - suppresses EVENTQ/PRI side effects for ATOS/GATOS faults.
- Preserved the older compatibility `REG_ARCH_PAR_LO/HI` and
  `ARCH_CTRL_GATOS_TRANSLATE` debug command for existing tests.

## Source evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `SMMUV3_GATOS_CTRL`
  - `SMMUV3_GATOS_PAR_LO`
  - `ARCH_GATOS_CTRL_RUN`
  - `run_arch_gatos_register_translate`
  - `architectural SMMU_GATOS register translation`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `Smmuv3GatosRegistersRunAndClear`
  - `Smmuv3GatosFaultDoesNotRecordEvent`

## Verification evidence

| Command | Log | Result |
| --- | --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j2` | `build/verification/smmu-architected-gatos-registers-rebuild-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| `sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*GatosParReportsSteOutputAttributes*:*Smmuv3GatosRegistersRunAndClear*:*Smmuv3GatosFaultDoesNotRecordEvent*'` | `build/verification/smmu-architected-gatos-registers-regression-gtest-20260511.log` | PASS: `3 tests` / `PASSED` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/smmu-architected-gatos-registers-ctest-20260511.log` | PASS: full component CTest |
| `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/smmu-architected-gatos-registers-static-20260511.json` | `build/verification/smmu-architected-gatos-registers-static-20260511.log` | PASS: static checklist/checker, `full_smmuv3_compliance=not_claimed` |
| `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-architected-gatos-registers-lane-20260511.log` | PASS: lane contract |
| final closure script | `build/verification/smmu-architected-gatos-registers-final-closure-check-20260511.log` | PASS: diff checks, syntax, JSON parse, checker, lane |

## Focused runtime assertions

- `Smmuv3GatosRegistersRunAndClear` verifies SMMU_GATOS SID/ADDR writes, RUN
  clear-on-completion, successful PAR PA bits, and readable SID/ADDR state.
- `Smmuv3GatosFaultDoesNotRecordEvent` verifies a fault PAR with FAULT set and
  `FAULTCODE=0x10` while `m_fault_count` and EVENTQ producer remain unchanged.
- Regression coverage keeps `GatosParReportsSteOutputAttributes` so the newer
  register path stays compatible with the previously added output-attribute PAR
  return slice.

## Remaining blockers

This is still a bounded QBox compliance-model slice. The following items remain
open before any `full_smmuv3_compliance` claim:

- Secure `SMMU_S_GATOS` register-group parity.
- VATOS/S_VATOS register groups.
- Complete ATOS_ADDR field/type matrix and partial translation-result variants.
- Packet-level PCIe ATS/PRI attribute semantics beyond the current TLM slice.
- Complete Root/Realm RME/GPT/GPC policy and upstream `arm-smmu-v3` lifecycle
  parity.
