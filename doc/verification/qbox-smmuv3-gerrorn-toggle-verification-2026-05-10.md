# QBox SMMUv3 GERROR/GERRORN Toggle Verification - 2026-05-10

## Scope

SMMU-COMP-070 GERROR/GERRORN active-bit toggle functional slice.

This component-level slice tightens global error acknowledgement semantics. The
Apollo TBU now keeps raw `GERROR` and `GERRORN` state internally and reports
active errors through `GERROR[x] ^ GERRORN[x]`. New errors toggle raw `GERROR`
only when the error is inactive, software `GERRORN` writes acknowledge only
currently-active bits, inactive-bit writes are ignored by the model, and a later
recurrence can toggle the error active again.

A later follow-up slice in
`doc/verification/qbox-smmuv3-gerror-raw-toggle-verification-2026-05-10.md`
changes the externally-read `SMMUV3_GERROR` value to the architectural raw
toggle state and updates component/Linux probes to compute active errors as
`GERROR ^ GERRORN`.

This is not full architectural IRQ/MSI delivery: PCIe MSI writes, abort
reporting, GIC/MSI routing, and full upstream `arm-smmu-v3` interrupt lifecycle
parity remain open.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  states that a global error is active when `SMMU_GERROR[x]` differs from
  `SMMU_GERRORN[x]`.
- The same section states that hardware toggles `GERROR[x]` when an inactive
  error becomes active, and software acknowledges by toggling the corresponding
  `GERRORN[x]`.
- `sources/smmu/TASKS_BUGS.md` records the reference model's XOR-toggle protocol
  for `GERROR/GERRORN`.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `read_arch_gerror()`, `set_arch_gerror()`, and `ack_arch_gerror()`.
- Command queue errors and queue overflow paths now use `set_arch_gerror()`
  instead of directly OR-ing active bits.
- `SMMUV3_GERRORN` writes call `ack_arch_gerror()` so only currently-active bits
  are acknowledged.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` adds
  `GerrorRegisterExposesRawToggleStateAndGerrornAcknowledgesActiveBits`.
- `scripts/check_qbox_smmuv3_compliance.py`,
  `scripts/check_buildroot_arm64_lane.sh`, and
  `doc/spec/qbox-smmuv3-compliance-checklist.md` gate the slice.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-gerrorn-toggle-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-gerrorn-toggle-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1`. |
| Static/checker/lane | PASS | `build/verification/smmu-gerrorn-toggle-static-final-20260510.log`: `PASS  tbu:gerrorn-active-toggle`, `SUMMARY {"pass": 240}`, and `Lane conclusion: Buildroot owns rootfs/DTB generation only; Linux Image comes from sources/linux, and libqemu comes from sources/qemu.` |

## Remaining blockers

- PCIe MSI write generation and MSI abort reporting.
- Full GIC/MSI delivery and ordering.
- Full raw architectural `GERROR` register exposure if QBox later decides to
  break the current active-bit compatibility ABI.
- Upstream `arm-smmu-v3` interrupt lifecycle parity.
