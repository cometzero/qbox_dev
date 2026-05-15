# QBox SMMUv3 Secure S2TTB/NSCFG selection verification (2026-05-11)

## Scope

SMMU-COMP-030/040 Secure stage-2 table-base selection functional slice.

This slice uses the repository-local `sources/smmu` reference notes as ground
truth for the modeled behavior: in a Secure stage-2-only translation, `STE.NSCFG`
selects whether the stage-2 input is treated as Secure IPA or Non-secure IPA;
Secure IPA uses `STE.S_S2TTB`, while Non-secure IPA uses `STE.S2TTB`.

The QBox implementation is still a functional model slice. It does not claim
full Secure SMMUv3/RME compliance, guest-visible Secure register banking,
stage-1-derived Secure IPA-space selection, GPT/GPC behavior, or full upstream
Linux `arm-smmu-v3` parity.

## Code changes

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - adds modeled `ARCH_STE_NSCFG_*` decode constants and `ARCH_STE_S_S2TTB_*`
    word/mask constants.
  - adds `select_arch_stage2_table_base()` to choose `S_S2TTB` only for modeled
    Secure stage-2-only/S1DSS-bypass paths where `NSCFG` selects Secure IPA.
  - records `m_arch_last_nscfg`, `m_arch_last_s_s2ttb`, and
    `m_arch_last_s2_secure_ipa` for focused component verification.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - adds `SecureStage2OnlyUsesSS2TtbWhenNscfgSecure` to prove `NSCFG=Secure`
    selects the Secure `S_S2TTB` table and `NSCFG=Non-secure` selects the normal
    `S2TTB` table for the same Secure stream-table probe.
- `scripts/check_qbox_smmuv3_compliance.py`
  - adds the conservative `tbu:secure-s2ttb-nscfg-selection` static gate.
- `scripts/check_buildroot_arm64_lane.sh`
  - adds lane guards for the selector, `S_S2TTB` word decode, and component test.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Build | `build/verification/smmu-secure-s2ttb-nscfg-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused CTest | `build/verification/smmu-secure-s2ttb-nscfg-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |

Additional bash/static/lane/guest regression for this combined state is recorded
in `build/verification/smmu-secure-s2ttb-nscfg-evidence-summary-final-20260511.log`:

- shell syntax: `build/verification/smmu-secure-s2ttb-nscfg-bashn-20260511.log`
  is empty on success.
- Python syntax: `build/verification/smmu-secure-s2ttb-nscfg-pycompile-20260511.log`
  is empty on success.
- static compliance checker: `build/verification/smmu-secure-s2ttb-nscfg-static-20260511.log`
  reports `SUMMARY {"pass": 634}` and
  `full_smmuv3_compliance=not_claimed`.
- lane contract check: `build/verification/smmu-secure-s2ttb-nscfg-lane-20260511.log`
  passes the Buildroot/QBox ARM64 lane guards.
- guest regression: `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-secure-s2ttb-nscfg.driver.log`
  passes with `1x1x2x2xf32=[[[54 63][90 99]]]`.

## Stop condition

The configured Secure stage-2-only `NSCFG` to `S_S2TTB` selection component
slice is implemented and component-tested. The aggregate SMMUv3 compliance goal
remains open because guest-visible Secure banking, stage-1-derived Secure IPA
selection, full RME/GPT/GPC, complete event priority, and upstream recovery
parity remain open.
