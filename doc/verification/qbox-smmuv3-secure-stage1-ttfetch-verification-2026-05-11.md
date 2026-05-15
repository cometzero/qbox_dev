# QBox SMMUv3 Secure stage-1 TT-fetch table selection verification (2026-05-11)

## Scope

SMMU-COMP-030/040 Secure nested stage-1 translation-table descriptor fetch
S2TTB/S_S2TTB selection functional slice.

Ground truth is the repository-local `sources/smmu` SMMUv3 reference notes:
Secure stage 1 can output Secure IPA or Secure-stream Non-secure IPA; Secure
stage 2 uses `STE.S_S2TTB` for Secure IPA and `STE.S2TTB` for Non-secure IPA;
for Secure EL2 translation table walks, `CD.NSCFG{0,1}` controls the starting
NS attribute, and table-descriptor `NSTable` can make later levels Non-secure.

This slice extends the previous final-output NSIPA selection work to the stage-1
translation-table descriptor fetches themselves. It remains a functional model
slice, not full Secure SMMUv3/RME compliance.

## Code changes

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - adds `read_arch_ste_s_s2ttb()` so `STE.S_S2TTB` can be reused by final
    Secure stage-2 translation and by nested Secure stage-1 TT fetches.
  - tracks `m_arch_last_s1_tt_fetch_secure_ipa` and
    `m_arch_last_s1_tt_fetch_s2ttb` for component-level proof of which IPA space
    and stage-2 table root were used for the last stage-1 TT descriptor fetch.
  - selects `secure_s2ttb` for Secure stage-1 TT fetches while the current
    stage-1 table-walk NS attribute is Secure, and falls back to normal `S2TTB`
    when `CD.NSCFG0`/`NSTable` makes the table walk Non-secure.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - extends `SecureNestedStage1OutputNsSelectsS2Ttb` with assertions that
    `CD.NSCFG0=0` uses `S_S2TTB` for stage-1 TT descriptor fetches, while
    `CD.NSCFG0=1` uses `S2TTB`.
- `scripts/check_qbox_smmuv3_compliance.py`
  - adds `tbu:secure-stage1-ttfetch-s2ttb-selection` and updates the conservative
    classification text without claiming full compliance.
- `scripts/check_buildroot_arm64_lane.sh`
  - adds lane guards for the new TT-fetch selector state and component assertion.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Build | `build/verification/smmu-secure-stage1-nsipa-ttfetch-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused CTest | `build/verification/smmu-secure-stage1-nsipa-ttfetch-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Shell syntax | `build/verification/smmu-secure-stage1-ttfetch-bashn-20260511.log` | PASS: empty on success |
| Python syntax | `build/verification/smmu-secure-stage1-ttfetch-pycompile-20260511.log` | PASS: empty on success |
| Static compliance checker | `build/verification/smmu-secure-stage1-ttfetch-static-final-20260511.log` | PASS: `SUMMARY {"pass": 647}`, `full_smmuv3_compliance=not_claimed` |
| Lane contract | `build/verification/smmu-secure-stage1-ttfetch-lane-afterdoc-20260511.log` | PASS: Buildroot/QBox ARM64 lane guards pass |
| Guest regression | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-secure-stage1-ttfetch.driver.log` | PASS: `1x1x2x2xf32=[[[54 63][90 99]]]` |

## Stop condition

The Secure nested stage-1 TT-fetch table-root selection slice is implemented and
component-tested. Remaining aggregate blockers are guest-visible Secure register
banking, full Secure/Realm endpoint acceptance policy, full RME/GPT/GPC
behavior, complete event matrix priority/parity, full Arm reference-vector
coverage, and upstream Linux `arm-smmu-v3` lifecycle parity.

The consolidated evidence summary is recorded in `build/verification/smmu-secure-stage1-ttfetch-evidence-summary-final-20260511.log`.
