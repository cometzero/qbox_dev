# QBox SMMUv3 Secure STRTAB bank selection verification (2026-05-11)

## Scope

SMMU-COMP-030 Secure stream-table bank selection functional slice.

This slice adds a modeled per-security-state stream-table bank. A component
probe can configure a Secure STRTAB base/config pair and then select it when the
active modeled security state is Secure, while the Non-secure security state
continues to use the existing SMMUv3 STRTAB registers. This narrows the previous
single Non-secure STRTAB-only model without claiming full Secure SMMUv3 banking.

Remaining blockers include guest-visible Secure register banking, architectural
`NSCFG` and `S2TTB` versus `S_S2TTB` selection, Secure/Realm/Root endpoint
acceptance policy, full RME/GPT/GPC behavior, complete event matrix priority,
and upstream Linux `arm-smmu-v3` lifecycle parity.

## Code changes

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - adds `arch_security_strtab_bank` and `m_arch_security_strtab_banks`.
  - adds `configure_arch_security_strtab_bank()` and
    `arch_security_strtab_bank_state()`.
  - teaches `arch_ste_address()` to select a configured Secure/Realm/Root STRTAB
    bank for modeled descriptor probes while preserving the existing Non-secure
    `STRTAB_BASE/STRTAB_BASE_CFG` path.
  - updates stream-context and STE-read entry checks so a configured security
    STRTAB bank is considered an active stream-table source.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - adds `SecureStreamTableBankSelectsSecureSte` to prove Secure probes read the
    Secure STE/CD while Non-secure probes still read the Non-secure STE/CD.
- `scripts/check_qbox_smmuv3_compliance.py`
  - adds `tbu:security-strtab-bank-selection`.
- `scripts/check_buildroot_arm64_lane.sh`
  - adds lane guards for the configured Secure STRTAB bank route and component
    assertion.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Build | `build/verification/smmu-secure-strtab-bank-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused CTest | `build/verification/smmu-secure-strtab-bank-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |

Additional static/lane/guest regression for this combined state is recorded in
`build/verification/smmu-secure-strtab-bank-evidence-summary-final-20260511.log`:

- static compliance checker: `build/verification/smmu-secure-strtab-bank-static-final-20260511.log`
  reports `SUMMARY {"pass": 632}` and
  `full_smmuv3_compliance=not_claimed`.
- lane contract check: `build/verification/smmu-secure-strtab-bank-lane-final-20260511.log`
  passes the Buildroot/QBox ARM64 lane guards.
- guest regression: `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-secure-strtab-bank.driver.log`
  passes with `1x1x2x2xf32=[[[54 63][90 99]]]`.

## Stop condition

The configured Secure STRTAB bank selection component slice is implemented and
component-tested. The aggregate SMMUv3 compliance goal remains open because this
is not guest-visible Secure register banking and the repository still reports
`full_smmuv3_compliance=not_claimed`.
