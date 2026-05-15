# QBox SMMUv3 Secure CMDQ verification

- Date: 2026-05-11
- Scope: `/build/qbox_dev`
- Slice: SMMU-COMP-020 Secure command queue memory-backed lifecycle
- Result: PASS for the implemented functional slice; full ARM SMMUv3 compliance is not claimed.

## What changed

- Added a Secure command-queue consumer for the guest-visible `SMMU_S_CMDQ_*`
  register bank.
- `SMMU_S_CMDQ_PROD` now triggers memory-backed command fetch/consume when
  `SMMU_S_CR0.SMMUEN|CMDQEN` is acknowledged.
- Added independent Secure CMDQ consumer/error state through
  `read_secure_cmdq_cons()`, `write_secure_cmdq_cons()`, and
  `set_secure_cmdq_cerror()`.
- Reused the modeled command handlers for selected Secure commands including
  `CMD_SYNC`, `CMD_ATC_INV`, CFGI, TLBI, PRI_RESP, RESUME, and STALL_TERM while
  keeping the Non-secure CMDQ producer/consumer state isolated.
- Added Secure `CMD_ATC_INV` completion-error ordering parity for the modeled
  slice: a failed Secure ATC invalidation now reports
  `S_CMDQ_CONS.CERROR_ATC_INV_SYNC` on the following `S_CMD_SYNC`, pauses the
  Secure queue, and resumes only after software advances `S_CMDQ_CONS`.
- Added Secure `CMD_SYNC CS=IRQ` MSI ordering parity for the modeled slice:
  zero MSI addresses are ignored, successful writes are recorded only after the
  downstream write succeeds, failed writes raise `S_GERROR.MSI_CMDQ_ABORT`, and
  `S_GERRORN` acknowledgement clears the active Secure GERROR without touching
  the Non-secure GERROR bank.
- Hardened the Hexagon guest smoke verifier so the auxiliary StreamID 0x2 DMA
  path marker tolerates UART interleaving between kernel and QBox log writers.

## Verification evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Focused QBox component build | `build/verification/smmu-secure-cmdq-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Focused SMMU TBU CTest | `build/verification/smmu-secure-cmdq-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Secure CMDQ recovery build | `build/verification/smmu-secure-cmdq-recovery-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Secure CMDQ recovery CTest | `build/verification/smmu-secure-cmdq-recovery-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Secure CMD_SYNC MSI build | `build/verification/smmu-secure-cmdq-sync-msi-build-20260511.log` | PASS: `Built target apollo-smmu-tbu-tests` |
| Secure CMD_SYNC MSI CTest | `build/verification/smmu-secure-cmdq-sync-msi-ctest-20260511.log` | PASS: `100% tests passed, 0 tests failed out of 1` |
| Static/syntax/checker bundle | `build/verification/smmu-secure-cmdq-sync-msi-static-20260511.log` | PASS: `SUMMARY {"pass": 660}` and `full_smmuv3_compliance=not_claimed` |
| Buildroot/QBox lane contract | `build/verification/smmu-secure-cmdq-sync-msi-lane-20260511.log` | PASS: lane conclusion printed |
| Guest Hexagon IREE smoke | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-secure-cmdq-sync-msi.driver.log` | PASS: `1x1x2x2xf32=[[[54 63][90 99]]]` |

## Component coverage

- `SecureCmdqProducerConsumesMemoryBackedCommands` verifies that a programmed
  Secure CMDQ does not advance while Secure CR0 gates are disabled, then consumes
  memory-backed `CMD_SYNC` and `CMD_ATC_INV` entries after Secure CR0 is enabled.
- The same test proves the Secure CMDQ path invalidates a modeled ATS entry and
  leaves the Non-secure CMDQ consumer unchanged.
- `SecureCmdqAtcInvSyncCerrorPausesAndRecovers` verifies modeled Secure
  `ATC_INV` completion failures coalesce at `S_CMD_SYNC`, set
  `CERROR_ATC_INV_SYNC` with `S_CMDQ_CONS.RD` pointing at the failing sync,
  leave Non-secure `CMDQ_CONS` untouched, block further Secure command
  processing while the error is live, and resume after software skips the failed
  sync through `S_CMDQ_CONS`.
- `SecureCmdSyncMsiWriteAndAbortAreReported` verifies Secure `CMD_SYNC CS=IRQ`
  writes the MSI payload on success, reports failed writes through
  `S_GERROR.MSI_CMDQ_ABORT`, acknowledges the active Secure GERROR through
  `S_GERRORN`, raises the shared modeled GERROR/CMDQ_SYNC IRQ status, and
  preserves Non-secure GERROR isolation.

## Remaining blockers

This remains a modeled functional slice. The following are still open before a
full SMMUv3 compliance claim:

- Complete Secure command lifecycle parity, including all Secure command
  encodings, SSec/security-state command parameters, queue-error recovery beyond
  the modeled ATC_INV_SYNC slice, and Secure IRQ/MSI ordering beyond the modeled
  CMD_SYNC MSI slice.
- Full Secure/Realm endpoint acceptance policy.
- RME/GPT/GPC behavior and complete Secure/Realm event matrix.
- Full Arm reference-vector and upstream `arm-smmu-v3` lifecycle parity.
