# QBox SMMUv3 Secure stage-1-derived NSIPA verification (2026-05-11)

## Scope

SMMU-COMP-030/040 Secure stage-1-derived NSIPA selection functional slice.
SMMU-COMP-030/040 Secure nested stage-1-derived NSIPA selection functional evidence is covered by this focused IPA-space selection slice.

This slice uses the repository-local `sources/smmu` SMMUv3 reference notes as
its ground truth. The relevant architectural points are:

- a Secure stream stage-1 output targets either Secure IPA space or Secure-stream
  Non-secure IPA space;
- when Secure stage 2 is enabled, Secure IPA input is translated through
  `STE.S_S2TTB` and Non-secure IPA input is translated through `STE.S2TTB`;
- for Secure stage-1 table walks, `CD.NSCFG{0,1}` provides the starting NS
  attribute, and table-descriptor `NSTable` plus final descriptor `NS` influence
  the effective stage-1 output NS attribute;
- event `NSIPA` is derived from `STE.NSCFG` when stage 1 is bypassed, or from
  the stage-1 target IPA space when stage 1 translation is performed.

The QBox implementation remains a functional compliance slice. It does **not**
claim full Secure SMMUv3/RME compliance, guest-visible Secure register banking,
Secure endpoint acceptance beyond component probes, RME/GPT/GPC behavior, complete
fault/event matrix parity, or upstream Linux `arm-smmu-v3` recovery parity.

## Code changes

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - adds modeled stage-1 descriptor `ARCH_DESC_NS` and `ARCH_DESC_NSTABLE`
    decode constants.
  - adds modeled `ARCH_CD_NSCFG0` decode for the starting NS attribute of a
    Secure stage-1 `CD.TTB0` walk.
  - tracks `m_arch_last_s1_table_walk_nonsecure` and
    `m_arch_last_s1_output_nonsecure_ipa` for focused component assertions.
  - extends the descriptor walker to propagate Secure stage-1 table-walk/output
    NS state from `CD.NSCFG0`, table-descriptor `NSTable`, and leaf `NS`.
  - extends `select_arch_stage2_table_base()` so a Secure nested final stage-2
    translation uses `STE.S_S2TTB` for Secure IPA and `STE.S2TTB` for
    Non-secure IPA.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - adds `SecureNestedStage1OutputNsSelectsS2Ttb`, covering three Secure nested
    cases for the same stream-table probe:
    - leaf `NS=0` and `CD.NSCFG0=0` select Secure IPA and `S_S2TTB`;
    - leaf `ARCH_DESC_NS` selects Non-secure IPA and `S2TTB`;
    - `CD.NSCFG0=1` starts the Secure table walk as Non-secure and selects
      Non-secure IPA / `S2TTB`.
  - updates the reserved-CD-bit vector so modeled `CD.NSCFG0` bit 0 is legal and
    an actually reserved bit remains the negative test input.
- `scripts/check_qbox_smmuv3_compliance.py`
  - adds `tbu:secure-stage1-nsipa-selection` as a conservative static gate and
    narrows the remaining SMMU-COMP-030/040 blocker wording to stage-1 TT-fetch
    Secure IPA-space table selection.
- `scripts/check_buildroot_arm64_lane.sh`
  - adds lane guards for `ARCH_CD_NSCFG0`, `ARCH_DESC_NS`, and the focused
    component test.
- `doc/spec/qbox-smmuv3-compliance-checklist.md`
  - records this as a verified functional slice without claiming full SMMUv3
    compliance.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Build | `build/verification/smmu-secure-stage1-nsipa-build-rerun-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused CTest | `build/verification/smmu-secure-stage1-nsipa-ctest-rerun-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Shell syntax | `build/verification/smmu-secure-stage1-nsipa-bashn-20260511.log` | PASS: empty on success |
| Python syntax | `build/verification/smmu-secure-stage1-nsipa-pycompile-20260511.log` | PASS: empty on success |
| Static compliance checker | `build/verification/smmu-secure-stage1-nsipa-static-afterdoc-20260511.log` | PASS: `SUMMARY {"pass": 642}`, `full_smmuv3_compliance=not_claimed` |
| Lane contract | `build/verification/smmu-secure-stage1-nsipa-lane-20260511.log` | PASS: Buildroot/QBox ARM64 lane guards pass |
| Guest regression | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-secure-stage1-nsipa.driver.log` | PASS: `1x1x2x2xf32=[[[54 63][90 99]]]` |

The guest run also produced:

- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-secure-stage1-nsipa.log`
- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-boot-20260511-secure-stage1-nsipa.log`

The consolidated evidence summary is recorded in
`build/verification/smmu-secure-stage1-nsipa-evidence-summary-final-20260511.log`.

## Stop condition

The configured Secure nested stage-1-derived IPA-space selection component slice
is implemented and verified. The aggregate SMMUv3 compliance goal remains open
because full compliance still requires guest-visible Secure register banking,
Secure/Realm endpoint
acceptance policy beyond component probes, full RME/GPT/GPC behavior, complete
event matrix priority/parity, and upstream Linux `arm-smmu-v3` lifecycle parity.
