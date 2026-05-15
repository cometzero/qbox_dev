# QBox SMMUv3 ATS TR HTTU write-intent verification (2026-05-11)

Marker: SMMU-COMP-040/050/060 ATS Translation Request HTTU write-intent slice.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:2095` states that a valid ATS Translation Request updates Access/Dirty flags when HTTU is enabled; `NW==1` is read-only, while `NW==0` is read-write.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:3253` states that ATS TRs set AF like direct transactions.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md:3254` states that an ATS write request (`NW==0`) to a writable-clean page marks the page writable-dirty before returning a write-granting ATS response; if only Access HTTU is enabled, write access is denied (`W==0`).
- `sources/smmu/TASKS_CPP_OPERATION.md:496` through `sources/smmu/TASKS_CPP_OPERATION.md:498` track the corresponding implementation tasks.

## Implementation slice

- Added `ARCH_CTRL_ATS_TRANSLATION_REQUEST_WRITE` as a test/control path for ATS Translation Requests with write intent (`NW==0`).
- `run_arch_ats_translation_request(bool write)` now feeds the write intent into the existing stream/context/table walker, so the bounded HTTU leaf-update model applies the same Access/Dirty rules to ATS TRs as to direct SMMU transactions.
- The model records `m_arch_last_ats_treq_write` and logs `nw=0/1` plus `httu-dirty=0/1` for auditability.
- `AtsTranslationRequestWriteIntentUpdatesHttuDirty` verifies both:
  - CD.HA+CD.HD write-intent ATS TR clears `AP[RO]` on a DBM writable-clean page and returns success without EVENTQ side effects.
  - CD.HA-only write-intent ATS TR leaves the page read-only and returns the modeled ATS success/no-write (`W==0`) path as a permission translation result without EVENTQ side effects.

## Verification commands

Planned/current evidence is captured under `build/verification/smmu-ats-treq-httu-write-intent-*20260511.log`:

1. `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests`
2. Focused `apollo-smmu-tbu-tests` filter for `AtsTranslationRequestWriteIntentUpdatesHttuDirty` plus adjacent ATS/HTTU tests.
3. `ctest --test-dir sources/qbox/build/tests/components/apollo_smmu_tbu --output-on-failure`
4. `python3 scripts/check_qbox_smmuv3_compliance.py --self-test-negative`
5. `./scripts/check_buildroot_arm64_lane.sh`
6. `bash -n scripts/*.sh`
7. `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py scripts/qbox_pty_runner.py`
8. `git diff --check`

## Scope and remaining gaps

This is a bounded compliance slice. It does not claim complete ATS Completion Data Entry bit encoding, packet-level ATS T/XT/TE/Global-bit parity, full PRI page-request flag update behavior, or full DPT/RME/GPC interactions.
