# QBox SMMUv3 DMA async IRQ signal verification - 2026-05-11

## Scope

SMMU-COMP-070 DMA async IRQ signal functional slice.

Evidence pattern: SMMU-COMP-070 DMA async IRQ signal functional slice.

This slice upgrades the Apollo Hexagon DMA async fence model from register-only
pending bits to a signal-level interrupt output. `REG_IRQ_STATUS` remains the
software-visible queue bitmap, but the DMA model now asserts `irq_out` whenever
any queue bit is pending and deasserts it only after software acknowledges the
last pending bit through `REG_IRQ_ACK`. The QBox Buildroot platform binds the
primary and auxiliary DMA doorbell outputs to the Linux-visible GIC SPIs that
match the DTS doorbell interrupt entries.

This is still a functional slice. It proves the SystemC signal behavior and
platform wiring, but it does not claim full GIC/MSI ordering, Linux IRQ handler
use, or upstream `arm-smmu-v3` interrupt lifecycle parity.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h`
  - `InitiatorSignalSocket<bool> irq_out`
  - `update_irq_output()`
  - `complete_async_event()` asserts the IRQ signal when queue IRQ bits become
    pending.
  - `REG_IRQ_ACK` clears queue bits and deasserts the IRQ only when no queue is
    still pending.
- `sources/qbox/platforms/buildroot/conf_aarch64.lua`
  - primary `hexagon_dma_0.irq_out -> gic_0.spi_in_564`
  - auxiliary `hexagon_dma_1.irq_out -> gic_0.spi_in_566`
- `sources/qbox/tests/components/apollo_hexagon_dma/apollo-hexagon-dma-tests.cc`
  - `AsyncFenceDrivesIrqSignalUntilAck`
- `sources/qbox/tests/components/CMakeLists.txt`
  - adds `tests/components/apollo_hexagon_dma` to the component test tree.

## Validation evidence

| Check | Evidence |
| --- | --- |
| Build | `build/verification/apollo-hexagon-dma-async-irq-signal-build-20260511.log` (`Built target apollo_hexagon_dma`, `Built target apollo-hexagon-dma-tests`) |
| Component CTest | `build/verification/apollo-hexagon-dma-async-irq-signal-ctest-20260511.log` (`100% tests passed, 0 tests failed out of 1`) |
| Focused gTest | `build/verification/apollo-hexagon-dma-async-irq-signal-gtest-20260511.log` (`[  PASSED  ] 1 test.`) |
| Syntax checks | `build/verification/smmu-dma-async-irq-signal-syntax-20260511.log` |
| Static/lane checker | `build/verification/smmu-dma-async-irq-signal-static-final-20260511.log` (`PASS  dma:async-fence-irq-signal`, `SUMMARY {"pass": 591}`) |
| Compliance JSON | `build/verification/qbox-smmuv3-compliance-dma-async-irq-signal-final-20260511.json` (`full_smmuv3_compliance: not_claimed`) |
| Diff check | `build/verification/smmu-dma-async-irq-signal-diff-check-20260511.log` |

## Result

`AsyncFenceDrivesIrqSignalUntilAck` verifies the signal-level IRQ semantics:

1. the IRQ line starts deasserted with no pending queue bits;
2. queue 0 completion sets `REG_IRQ_STATUS[0]`, increments the fence sequence,
   and asserts the IRQ line;
3. queue 1 completion while queue 0 is still pending keeps the line asserted and
   records both queue bits;
4. acknowledging only queue 0 leaves the IRQ asserted because queue 1 is still
   pending;
5. acknowledging queue 1 clears the final pending bit and deasserts the IRQ.

Remaining blockers: guest Linux currently validates this path by polling
`REG_IRQ_STATUS`/`REG_JOB_FENCE`; a production-complete IRQ path still needs a
Linux IRQ handler/wait path, ordering tests against actual GIC delivery, and
broader SMMUv3/MSI lifecycle parity.
