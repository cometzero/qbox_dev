# QBox SMMUv3 SMMU-COMP-070 Linux DMA IRQ wait verification (2026-05-11)

## Scope

SMMU-COMP-070 Linux DMA async IRQ wait functional slice.

This slice completes the guest Linux consumer side for the Apollo Hexagon DMA
async fence doorbell. The DMA model already drives Linux-visible doorbell SPIs;
this change makes `apollo-hexagon-test.c` bind the named `doorbell` IRQ, wake a
completion from the IRQ handler, and wait on interrupt-driven async fence
completion before falling back to the existing register-polling loop.

## Changed implementation

- `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c`
  - Added `struct completion async_fence` and `doorbell_irq` state.
  - Added `apollo_hexagon_irq()` to cache pending IRQ status, ACK the
    doorbell in the handler to deassert the level interrupt, and complete the
    async fence.
  - Added `apollo_hexagon_prepare_async_fence()` before each CNN/SG-DMA job start
    to reinitialize completion state and clear stale per-queue status.
  - Added `platform_get_irq_byname_optional(..., "doorbell")` and
    `devm_request_irq()` in probe.
  - Added `wait_for_completion_timeout()` before the legacy polling fallback.
- `scripts/check_buildroot_arm64_lane.sh`
  - Added contract checks for IRQ lookup, IRQ request, completion wait, and
    guest-visible log markers.
- `scripts/check_qbox_smmuv3_compliance.py`
  - Added `linux:dma-async-irq-wait` static compliance gate.
- `doc/spec/qbox-smmuv3-compliance-checklist.md`
  - Extended SMMU-COMP-070 source/runtime evidence for the Linux IRQ wait path.
- `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`
  - Added this progress note and updated the prior polling-only caveat.

## Verification evidence

| Evidence | Command | Result |
| --- | --- | --- |
| Python checker syntax | `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | Pass; see `build/verification/smmu-linux-dma-irq-wait-pycompile-20260511.log`. |
| Shell checker syntax | `bash -n scripts/check_buildroot_arm64_lane.sh` | Pass; see `build/verification/smmu-linux-dma-irq-wait-bashn-20260511.log`. |
| Superproject whitespace check | `git diff --check -- scripts/check_qbox_smmuv3_compliance.py scripts/check_buildroot_arm64_lane.sh doc/spec/qbox-smmuv3-compliance-checklist.md doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md` | Pass; see `build/verification/smmu-linux-dma-irq-wait-superproject-diff-check-20260511.log`. |
| Linux submodule whitespace check | `git -C sources/linux diff --check -- drivers/soc/apollo/apollo-hexagon-test.c` | Pass; see `build/verification/smmu-linux-dma-irq-wait-linux-diff-check-20260511.log`. |
| Buildroot lane contract | `./scripts/check_buildroot_arm64_lane.sh` | Pass; includes the new Linux async doorbell IRQ lookup/request/wait/log gates. See `build/verification/smmu-linux-dma-irq-wait-lane-20260511.log`. |
| SMMUv3 static compliance checker | `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/qbox-smmuv3-compliance-linux-dma-irq-wait-final-20260511.json` | Pass, `SUMMARY {"pass": 600}` and `linux:dma-async-irq-wait` passed. Full SMMUv3 compliance remains `not_claimed`. See `build/verification/smmu-linux-dma-irq-wait-static-final-20260511.log`. |
| Standalone Linux Image build | `./scripts/build_qbox_linux_arm64.sh` | Pass; `drivers/soc/apollo/apollo-hexagon-test.o` rebuilt and `build/linux-a710/arch/arm64/boot/Image` generated. See `build/verification/smmu-linux-dma-irq-wait-kernel-build-20260511.log`. |
| Artifact staging | `./scripts/stage_buildroot_artifacts.sh` | Pass; staged rebuilt `Image.bin`, DTB, rootfs, and Hexagon firmware. See `build/verification/smmu-linux-dma-irq-wait-stage-artifacts-20260511.log`. |
| QBox guest Hexagon smoke | `QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260511-linux-dma-irq-wait QBOX_BOOT_TIMEOUT=65 QBOX_IREE_LOGIN_DELAY=24 QBOX_IREE_AFTER_COMMAND_DELAY=24 ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` | Pass; output matched `1x1x2x2xf32=[[[54 63][90 99]]]` and guest log contains `async fence irq wait signaled queue=0/1`. See `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-linux-dma-irq-wait.driver.log` and `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-linux-dma-irq-wait.log`. |

## Current classification

- SMMU-COMP-070 is still a **functional slice**, not a full compliance claim.
- The normal QBox guest path can now be interrupt-driven for Apollo Hexagon DMA
  async fences, with a compatibility fallback to polling if the doorbell IRQ is
  absent or times out.
- Remaining gaps: formal GIC ordering/coalescing assertions, MSI lifecycle
  parity, and upstream `arm-smmu-v3` interrupt recovery parity.
