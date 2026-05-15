# QBox SMMUv3 MPAM PARTID-space verification - 2026-05-11

## Scope

SMMU-COMP-020/050 MPAM PARTID-space functional slice.

Evidence pattern: SMMU-COMP-020/050 MPAM PARTID-space functional slice.

This slice makes QBox's current MPAM PARTID-space model explicit. QBox still
models only the Non-secure SMMUv3 security-state path, but downstream Apollo
SMMU TLM transactions now carry a `mpam_partid_space` attribute alongside
`mpam_partid`, `mpam_pmg`, and `mpam_unknown`. The Apollo TBU also exposes the
last resolved PARTID-space in the MPAM status register so tests and guest-side
probes can distinguish a deliberate Non-secure-only model from an omitted
field.

Ground truth used for this slice:

- `sources/smmu/wiki/concepts/mpam.md`
  - MPAM attributes are not just PARTID/PMG values; they are scoped by the
    SMMU security state/PARTID-space selected by the MPAM_NS/SP path.
  - The current QBox platform has no Secure or Realm execution-state plumbing,
    so this slice deliberately tags all modeled MPAM traffic as Non-secure
    rather than claiming Secure/Realm support.

## Implementation evidence

- `sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h`
  - `mpam_partid_space`
  - `copy_from()` copies `mpam_partid_space` with the rest of the extension.
- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `ARCH_MPAM_SPACE_NONSECURE`
  - `m_arch_last_mpam_partid_space`
  - `populate_arch_mpam_extension()` and
    `populate_arch_mpam_extension_from_state()` attach the explicit modeled
    space to originated and client-derived transactions.
  - `arch_mpam_status()` encodes the last PARTID-space in status bits `[7:6]`.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `MpamAttributesCarryNonSecurePartidSpace`

## Validation evidence

| Check | Evidence |
| --- | --- |
| Build | `build/verification/apollo-smmu-tbu-mpam-partid-space-build-20260511.log` (`Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`) |
| Component CTest | `build/verification/apollo-smmu-tbu-mpam-partid-space-ctest-20260511.log` (`100% tests passed, 0 tests failed out of 1`) |
| Focused gTest | `build/verification/apollo-smmu-tbu-mpam-partid-space-gtest-20260511.log` (`[  PASSED  ] 2 tests.`) |
| Syntax checks | `build/verification/smmu-mpam-partid-space-syntax-20260511.log` |
| Static/lane checker | `build/verification/smmu-mpam-partid-space-static-final-20260511.log` (`PASS  tbu:mpam-partid-space-nonsecure`, `SUMMARY {"pass": 576}`) |
| Compliance JSON | `build/verification/qbox-smmuv3-compliance-mpam-partid-space-final-20260511.json` (`full_smmuv3_compliance: not_claimed`) |

## Result

`MpamAttributesCarryNonSecurePartidSpace` proves a GBPMPAM-attributed client
transaction carries the explicit Non-secure PARTID-space downstream and that the
same PARTID-space is reflected through `REG_ARCH_MPAM_STATUS` bits `[7:6]`.
This closes the previous ambiguity where PARTID/PMG values were propagated
without saying which modeled MPAM PARTID-space they belonged to.

Remaining blockers: Secure and Realm security-state plumbing, MPAM_NS/SP
selection, PMCG PARTID/PMG filtering, PASIDTT-dependent MPAM resolution, and
full ATS/PRI/event/security/RME/GPC/upstream parity remain open.
