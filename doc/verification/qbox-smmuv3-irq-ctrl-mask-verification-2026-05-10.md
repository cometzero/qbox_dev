# QBox SMMUv3 IRQ_CTRL Mask Verification - 2026-05-10

## Scope

SMMU-COMP-070 IRQ_CTRL reserved-bit mask functional slice.

This component-level slice tightens the Apollo TBU interrupt-control aperture.
Writes to `SMMUV3_IRQ_CTRL` are masked by the interrupt lines this functional
model exposes (`EVENTQ`, `PRIQ`, `CMDQ_SYNC`, and `GERROR`), and
`SMMUV3_IRQ_CTRLACK` mirrors the masked value instead of preserving unsupported
reserved bits.

This is not full architectural IRQ/MSI delivery. The model still uses
signal-level SystemC outputs and does not implement PCIe MSI writes, GIC-level
routing, upstream `arm-smmu-v3` interrupt lifecycle parity, or architected MSI
configuration registers.

## Ground truth

- `sources/linux/drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.h` defines a bounded
  IRQ_CTRL field set and a separate IRQ_CTRLACK register.
- `sources/smmu/TASKS_BUGS.md` records the reference model's IRQ_CTRL mask fix:
  upper bits are RES0 and IRQ_CTRLACK mirrors the supported bits.
- The QBox Apollo TBU compatibility model intentionally exposes a fourth
  signal-level `CMDQ_SYNC` output; the mask therefore follows the model's
  advertised four signal lines while still rejecting unsupported high bits.

## Implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  adds `ARCH_IRQ_CTRL_WRITABLE_MASK` and applies it when software writes
  `SMMUV3_IRQ_CTRL`.
- `SMMUV3_IRQ_CTRLACK` now mirrors the masked `IRQ_CTRL` value.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` adds
  `IrqCtrlReservedBitsAreMaskedInCtrlAck`.
- `scripts/check_qbox_smmuv3_compliance.py`,
  `scripts/check_buildroot_arm64_lane.sh`, and
  `doc/spec/qbox-smmuv3-compliance-checklist.md` gate the slice.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmu-tbu-irq-ctrl-mask-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`. |
| Component CTest | PASS | `build/verification/apollo-smmu-tbu-irq-ctrl-mask-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1`. |
| Static/checker/lane | PASS | `build/verification/smmu-irq-ctrl-mask-static-final-20260510.log`: `PASS  tbu:irq-ctrl-reserved-mask`, `SUMMARY {"pass": 235}`, and `Lane conclusion: Buildroot owns rootfs/DTB generation only; Linux Image comes from sources/linux, and libqemu comes from sources/qemu.` |

## Remaining blockers

- PCIe MSI write generation and abort reporting.
- Full GIC/MSI routing and interrupt ordering with the platform interrupt
  controller.
- Upstream `arm-smmu-v3` IRQ/MSI register lifecycle parity, including MSI
  configuration registers and Linux driver handling.
