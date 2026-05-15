# QBox SMMUv3 Raw GERROR Toggle Verification - 2026-05-10

## Scope

SMMU-COMP-070 raw GERROR toggle register functional slice.

This follow-up slice removes the compatibility shortcut where an external
`SMMUV3_GERROR` read returned only active global errors. The Apollo TBU now
returns raw architectural `GERROR` toggle state, keeps `GERRORN` as raw
acknowledgement state, and computes active global errors internally as
`GERROR ^ GERRORN`. Component tests and the Apollo Linux probe now use the same
active-XOR predicate when checking command-queue abort acknowledgement.

This still does not claim full SMMUv3 IRQ/MSI compliance. MSI writes, MSI abort
reporting, GIC/MSI routing, interrupt ordering, and upstream `arm-smmu-v3`
interrupt lifecycle parity remain open.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  describes a global error as active when `SMMU_GERROR[x]` differs from
  `SMMU_GERRORN[x]`.
- The same reference states that hardware toggles `GERROR[x]` when an inactive
  error becomes active, while software acknowledges by toggling `GERRORN[x]`.
- `sources/smmu/TASKS_BUGS.md` records the reference model's XOR-toggle protocol
  for `GERROR/GERRORN`.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `read_arch_gerror_raw()` and returns it for `SMMUV3_GERROR` reads.
- The existing `read_arch_gerror()` helper remains the internal active-error
  predicate (`GERROR ^ GERRORN`) used by `set_arch_gerror()` and
  `ack_arch_gerror()`.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  adds a `reg_read_gerror_active()` helper and renames/extends the component
  vector to `GerrorRegisterExposesRawToggleStateAndGerrornAcknowledgesActiveBits`.
- `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c` adds
  `apollo_smmuv3_gerror_active()` and records raw `gerror`, `gerrorn`, and
  active-XOR values in the DPTI unsupported-command selftest marker.
- `scripts/check_qbox_smmuv3_compliance.py`,
  `scripts/check_buildroot_arm64_lane.sh`, and
  `doc/spec/qbox-smmuv3-compliance-checklist.md` gate the slice.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-gerror-raw-toggle-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-gerror-raw-toggle-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1`. |
| Linux Image build | PASS | `build/verification/qbox-linux-smmu-gerror-raw-toggle-20260510.log`: `Linux Image: /build/qbox_dev/build/linux-a710/arch/arm64/boot/Image`. |
| Artifact staging | PASS | `build/verification/stage-artifacts-smmu-gerror-raw-toggle-20260510.log`: `Staged Linux + Buildroot artifacts into /build/qbox_dev/sources/qbox/platforms/buildroot/fw/Artifacts`. |
| QBox platform build | PASS | `build/verification/qbox-platform-smmu-gerror-raw-toggle-20260510.log`: `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`. |
| Guest smoke | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-gerror-raw-toggle.log`: `PASS: QBox guest IREE Hexagon tiny-CNN output matched`; boot log records `gerror=0x1 gerrorn=0x0 active=0x1`. |
| Static/checker/lane | PASS | `build/verification/smmu-gerror-raw-toggle-static-final-20260510.log`: `PASS  tbu:gerrorn-active-toggle`, `PASS  linux:gerror-active-xor`, `SUMMARY {"pass": 244}`, and `Lane conclusion: Buildroot owns rootfs/DTB generation only; Linux Image comes from sources/linux, and libqemu comes from sources/qemu.` |

## Remaining blockers

- PCIe MSI write generation and MSI abort reporting.
- Full GIC/MSI routing and interrupt ordering with the platform interrupt
  controller.
- Upstream `arm-smmu-v3` IRQ/MSI register lifecycle parity.
- Full interrupt-driven Linux wait paths beyond the current smoke and log-based
  queue/interrupt visibility checks.
