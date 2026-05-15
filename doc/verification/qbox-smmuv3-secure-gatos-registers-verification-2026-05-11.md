# QBox SMMUv3 Secure SMMU_S_GATOS register verification (2026-05-11)

## Scope

SMMU-COMP-020/030/080 Secure `SMMU_S_GATOS` register slice.

Marker: SMMU-COMP-020/030/080 Secure SMMU_S_GATOS register slice.

This extends the previous non-secure `SMMU_GATOS` RUN/PAR path to the Secure
SMMU register page. It closes only Secure GATOS register banking and does not
claim VATOS/S_VATOS, full ATOS_ADDR/type matrix, packet-level PCIe ATS/PRI
attribute parity, Root/Realm RME/GPT/GPC, or upstream driver lifecycle parity.

## Implementation summary

- Added Secure GATOS state: `m_arch_secure_gatos_ctrl`,
  `m_arch_secure_gatos_sid`, `m_arch_secure_gatos_addr`, and
  `m_arch_secure_gatos_par`.
- Added `arch_smmu_enabled_for_security_state()` so Secure GATOS uses Secure
  `SMMU_S_CR0.SMMUEN` rather than Non-secure CR0.
- Routed Secure PAGE_0 GATOS offsets through `read_smmuv3_secure_reg()` and
  `write_smmuv3_secure_reg()`.
- Extended `run_arch_gatos_register_translate(true)` to select Secure
  security-state, use the configured Secure STRTAB bank, write Secure PAR, and
  clear Secure RUN.
- Kept ATOS/GATOS faults as PAR-only outcomes with no normal EVENTQ/PRI side
  effects.

## Source evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `m_arch_secure_gatos_par`
  - `arch_smmu_enabled_for_security_state`
  - `run_arch_gatos_register_translate(true)`
  - `architectural SMMU_S_GATOS register translation`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `SecureSmmuv3GatosRegistersUseSecureBank`
  - `SecureSmmuv3GatosFaultDoesNotRecordEvent`

## Verification evidence

| Command | Log | Result |
| --- | --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j2` | `build/verification/smmu-secure-gatos-registers-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| `sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*SecureSmmuv3GatosRegistersUseSecureBank*:*SecureSmmuv3GatosFaultDoesNotRecordEvent*:*Smmuv3GatosRegistersRunAndClear*'` | `build/verification/smmu-secure-gatos-registers-gtest-20260511.log` | PASS: `3 tests` / `PASSED` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/smmu-secure-gatos-registers-ctest-20260511.log` | PASS: full component CTest |
| `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/smmu-secure-gatos-registers-static-20260511.json` | `build/verification/smmu-secure-gatos-registers-static-20260511.log` | PASS: static checklist/checker, `full_smmuv3_compliance=not_claimed` |
| `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-secure-gatos-registers-lane-20260511.log` | PASS: lane contract |
| final closure script | `build/verification/smmu-secure-gatos-registers-final-closure-check-20260511.log` | PASS: diff checks, syntax, JSON parse, checker, lane |

## Focused runtime assertions

- `SecureSmmuv3GatosRegistersUseSecureBank` verifies that Secure GATOS uses the
  Secure STRTAB bank and Secure CR0 enable, returns the Secure PA in PAR, clears
  RUN, and does not accidentally use the Non-secure STRTAB mapping.
- `SecureSmmuv3GatosFaultDoesNotRecordEvent` verifies Secure fault PAR encoding
  without moving either Non-secure EVENTQ producer or the Secure EVENTQ bank.

## Remaining blockers

- VATOS/S_VATOS register groups.
- Complete ATOS_ADDR field/type matrix and partial translation-result variants.
- Packet-level PCIe ATS/PRI attribute semantics beyond the current TLM slice.
- Complete Root/Realm RME/GPT/GPC policy and upstream `arm-smmu-v3` lifecycle
  parity.
