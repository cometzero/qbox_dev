# QBox SMMUv3 core owner verification (2026-05-11)

## Scope

SMMU-COMP-010 architected core ownership functional slice.

This slice adds a small `apollo_smmu_arch_core` ownership object and wires it
into the existing `apollo_smmu_tbu` compatibility adapter. The purpose is to
make the canonical translation-state owner explicit before deeper behavioral
core extraction. A follow-up within the same scope adds explicit ownership
metadata for the register/queue, STE/CD, walker, and replay subdomains and
routes the SMMUv3 register aperture classifier through the core object. It does
not claim a complete split of those algorithms into a standalone core. A second
follow-up moves the queue geometry helpers behind the core boundary, and a
third follow-up moves actual CMDQ/EVENTQ/PRIQ queue-state storage into the core
while preserving the existing TBU ABI through references. A fourth follow-up
moves stream/context selector storage into the same core object. A fifth
follow-up moves page-table walker state storage into the core. A sixth
follow-up moves scalar fault/replay protocol state into the same core object. A
seventh follow-up moves walker geometry arithmetic helpers behind the core
boundary. An eighth follow-up moves pure Stream-table, STE, CD, and
effective-EATS descriptor decode helpers behind the same core boundary. A ninth
follow-up moves pure EVENTQ fault-record layout and replay/status packing
helpers behind the core boundary while leaving queue writes, logging, and
SystemC replay table mutation in the adapter. A tenth follow-up moves the STAG
stall-record table and side-effect-free lookup helpers into the core while
leaving logging, buffered EVENTQ redrive, and endpoint replay payload records
in the adapter. An eleventh follow-up moves the endpoint replay payload record
table plus pending/any lookup and reset helpers into the core while leaving
SystemC wait/notify, logging, and downstream `b_transport()` redrive side
effects in the adapter. A twelfth follow-up moves replay-record allocation,
duplicate detection, capacity failure accounting, and CMD_RESUME retirement
counter transitions into the core while preserving the adapter-owned
translation retry and downstream redrive side effects. A thirteenth follow-up
moves endpoint replay redrive payload sizing, segment validation, first-segment
PA capture, segment completion, final redrive success, and failure-status
transitions into the core while preserving adapter-owned translation retry and
downstream `b_transport()` I/O. A fourteenth follow-up moves descriptor-walk
validation, descriptor-fetch address planning, descriptor step classification,
and leaf PA/fault state transitions into the core while preserving adapter-owned
downstream descriptor memory fetches, logging, ATS fill, and nested stage-2
walk orchestration. A fifteenth follow-up moves descriptor-fetch lifecycle
bookkeeping into the core, including fetch-address capture, successful
descriptor capture, and `F_WALK_EABT` fault-state transitions for descriptor
memory aborts, while the adapter still performs the physical downstream
`read_downstream_u64()` transaction. A sixteenth follow-up wraps that physical
descriptor memory transaction with a core-owned request/result object so the
adapter passes an explicit transaction PA and reports success/failure back to
the core boundary instead of open-coding descriptor-read completion state. A
seventeenth follow-up wraps endpoint replay downstream TLM transactions with a
core-owned request/result object so the adapter consumes core-supplied
PA/payload/write metadata and reports the returned TLM status back through the
core boundary before committing replay segment state. An eighteenth follow-up
moves the remaining descriptor-read and endpoint-replay physical I/O call sites
out of the walker/redrive loops and into named adapter executor seams while
keeping the actual TLM side effects adapter-executed. A nineteenth follow-up
adds a swappable adapter I/O executor interface plus the default TLM executor,
so descriptor reads and endpoint replay transactions dispatch through a
replaceable seam while the current default implementation still preserves the
adapter-executed downstream TLM behavior.

## Changed implementation

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_arch_core.h`
  - Added `apollo::smmuv3::apollo_smmu_arch_core`.
  - Records `translation_owner::apollo_systemc` as the canonical owner.
  - Keeps `compatibility_adapter_required=true`.
  - Keeps `qemu_translation_bridge_enabled=false` until a verified bridge
    exists.
  - Defines the compatibility aperture (`0x0000`) and SMMUv3 aperture
    (`0x1000`) contract.
  - Records register/queue, stream/context descriptor, page-table walker, and
    fault replay state ownership as canonical SystemC core responsibilities.
  - Provides `classify_register()` for compatibility-vs-SMMUv3 aperture
    routing.
  - Provides `queue_entries()`, `queue_base_addr()`, and `queue_index()` so
    the first register-queue behavior helpers now live on the core boundary.
  - Owns `queue_state` storage for CMDQ, EVENTQ, and PRIQ via
    `cmdq_state()`, `eventq_state()`, and `priq_state()`.
  - Owns `stream_context_descriptor_state` storage for STRTAB
    base/configuration, compatibility STE base, current CD table base, selected
    StreamID, and selected SSID.
  - Owns `page_table_walker_state` storage for TTBR/IOVA/S2TTB, last
    descriptor, PA/IPA/fetch-address, walk-depth, and last-stage fields.
  - Provides walker geometry helpers for granule page-shifts, supported
    granules, walk depth, level indexes, output masks, and leaf offset masks.
  - Provides Stream-table, STE, CD, and effective-EATS descriptor decode
    helpers for side-effect-free architected field extraction.
  - Owns `fault_replay_state` storage for scalar fault attributes, ATS/PRI
    response counters, stall/replay accounting, endpoint replay accounting,
    early-retry accounting, and STAG/PRG/replay sequence tags.
  - Owns `stall_record` table storage and provides STAG/fault lookup helpers
    for stalled EVENTQ records.
  - Owns `endpoint_replay_record` table storage and provides pending/any
    lookup plus reset helpers for stalled endpoint payload replay records.
  - Provides endpoint replay allocation and retirement helpers that update
    core-owned pending/retried/succeeded/failed/terminated/redriven counters.
  - Provides endpoint replay redrive helpers that own payload sizing, segment
    validation, replay PA/length/status updates, downstream replay transaction
    request/result metadata, final redrive success, and failure status
    transitions.
  - Provides descriptor-walk helpers that own walk begin validation, descriptor
    fetch address planning, table/block/page classification, AF/permission
    checks, and leaf PA/fault state transitions.
  - Provides descriptor-fetch lifecycle helpers that capture fetch addresses,
    fetched descriptor values, and descriptor-fetch abort fault state.
  - Provides descriptor memory-read request/result helpers that capture the
    original descriptor PA, actual transaction PA, stage-2-translation marker,
    and success/failure transitions around adapter-owned descriptor memory I/O.
  - Provides endpoint replay transaction request/result helpers that capture
    the replay PA, length, payload pointer, and write/read command metadata
    consumed by the adapter-executed `b_transport()` call.
  - Provides EVENTQ fault-record layout helpers (`event_record_layout`,
    `build_event_record()`), fault syndrome helpers, event-number mapping, and
    replay/status packing helpers for side-effect-free fault/replay reporting.
- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Includes the architected core header.
  - Owns `m_arch_core` in the existing TBU adapter.
  - Routes SMMUv3 register access detection through
    `m_arch_core.classify_register()` instead of duplicating the aperture
    boundary in the adapter.
  - Routes queue entry count, queue base address, and producer/consumer index
    helpers through `apollo_smmu_arch_core`.
  - Keeps compatibility aliases `m_cmdq`, `m_eventq`, and `m_priq` as
    references to core-owned queue state.
  - Keeps compatibility aliases for stream/context selector fields
    (`m_arch_strtab_base`, `m_arch_strtab_cfg`, `m_arch_ste_base`,
    `m_arch_cd_base`, `m_arch_stream_id`, and `m_arch_selected_ssid`) as
    references to core-owned stream/context state.
  - Keeps compatibility aliases for walker fields (`m_arch_ttbr`,
    `m_arch_iova`, `m_arch_s2ttb`, `m_arch_last_desc`, `m_arch_last_pa`,
    `m_arch_last_ipa`, `m_arch_last_fetch_addr`, `m_arch_walk_depth`, and
    `m_arch_last_stage`) as references to core-owned walker state.
  - Routes the existing TBU walker helper wrappers through
    `apollo_smmu_arch_core::walker_*` functions.
  - Routes pure descriptor helper wrappers through
    `apollo_smmu_arch_core` while keeping memory-backed descriptor fetches and
    compatibility logging in the adapter.
  - Routes EVENTQ fault-record layout, fault-detail/event-number helpers, and
    replay/status packing through `apollo_smmu_arch_core` while keeping
    memory-backed queue writes, log emission, buffered-event queues, and
    downstream replay side effects in the adapter.
  - Keeps compatibility aliases for fault/replay scalar fields
    (`m_arch_fault_reason`, `m_arch_stall_pending`,
    `m_arch_endpoint_replay_succeeded`, `m_arch_next_stag`, `m_arch_next_prg`,
    and related counters/tags) as references to core-owned fault/replay state.
  - Keeps `m_arch_stalls` as a compatibility reference to the core-owned STAG
    stall-record table while preserving adapter-owned logging and replay
    redrive side effects.
  - Keeps `m_arch_endpoint_replays` as a compatibility reference to the
    core-owned endpoint replay payload record table while preserving
    adapter-owned SystemC wait/notify, logging, and downstream redrive side
    effects.
  - Routes endpoint replay allocation/duplicate detection and CMD_RESUME
    retirement counter transitions through `apollo_smmu_arch_core` while
    retaining translation retry and `b_transport()` redrive in the adapter.
  - Routes endpoint replay redrive payload/status transitions and downstream
    transaction request/result wrapping through `apollo_smmu_arch_core` while
    retaining translation retry and the actual `b_transport()` I/O execution in
    the adapter.
  - Uses `execute_endpoint_replay_transaction()` as the named adapter executor
    for core-supplied endpoint replay transaction requests.
  - Routes descriptor-walk begin/fetch/step evaluation through
    `apollo_smmu_arch_core` while retaining downstream descriptor memory
    fetches, compatibility logging, ATS fill side effects, and nested stage-2
    orchestration in the adapter.
  - Routes descriptor fetch begin/complete/fail transitions through
    `apollo_smmu_arch_core` while retaining the physical
    `read_downstream_u64()` descriptor memory transaction in the adapter.
  - Routes descriptor memory-read request, completion, and failure transitions
    through `apollo_smmu_arch_core` while the adapter still performs the
    `read_downstream_u64()` call on the transaction PA supplied by the core
    request through the named `execute_descriptor_memory_read()` executor.
  - Preserves the top-level request IOVA across nested descriptor-fetch walks
    before emitting ATS/PRI/fault records, so core walker scratch state cannot
    clobber EVENTQ InputAddr payloads.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Added `ArchitectedCoreOwnsCanonicalTranslationState` to verify the owner,
    compatibility adapter, QEMU bridge state, state ownership metadata, and
    aperture classification.
  - Extended the same test to cover the core queue geometry helpers and the
    CMDQ/EVENTQ/PRIQ, stream/context, walker, and fault/replay state aliasing
    contracts.
  - Extended the same test to cover descriptor-walk config, fetch planning,
    table/leaf classification, and AF fault transitions owned by the core.
  - Extended the same test to cover descriptor-fetch lifecycle success/failure
    state transitions owned by the core.
  - Extended the same test to cover descriptor memory-read request/result
    wrapping, including nested-stage-2 translated fetch transaction PA capture.
  - Extended the same test to cover endpoint replay transaction request/result
    wrapping, including replay PA, length, payload pointer, and write/read
    metadata capture.
  - Extended the same test to inject a fake `arch_io_executor`, proving
    descriptor memory-read and endpoint replay transaction dispatch can be
    swapped without bypassing the core-owned request objects.
- `scripts/check_qbox_smmuv3_compliance.py`
  - Added/extended `tbu:architected-core-owner` and SMMU-COMP-010
    static evidence gates through descriptor memory-read, endpoint replay
    transaction request/result wrapping, and the swappable adapter I/O executor
    interface.
- `scripts/check_buildroot_arm64_lane.sh`
  - Added lane contract checks for the core owner header, swappable I/O
    executor seam, and component test.
- `doc/spec/qbox-smmuv3-compliance-checklist.md`
  - Updated SMMU-COMP-010 evidence and claim boundary.
- `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`
  - Added this progress note and preserved the deeper core-split blocker.

## Verification evidence

| Evidence | Command | Result |
| --- | --- | --- |
| QBox component build | `cmake --build sources/qbox/build --target apollo_smmu_tbu apollo-smmu-tbu-tests -j2` | Pass; see `build/verification/smmu-core-routing-build-20260511.log`. |
| QBox component test | `ctest --test-dir sources/qbox/build -R '^apollo-smmu-tbu-tests$' --output-on-failure` | Pass, `1/1 Test #15: apollo-smmu-tbu-tests ............   Passed`; see `build/verification/smmu-core-routing-ctest-20260511.log`. |
| Shell syntax | `bash -n scripts/check_buildroot_arm64_lane.sh` | Pass; see `build/verification/smmu-core-routing-bashn-20260511.log`. |
| Python syntax | `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | Pass; see `build/verification/smmu-core-routing-pycompile-20260511.log`. |
| Buildroot lane contract | `./scripts/check_buildroot_arm64_lane.sh` | Pass; includes the core owner, subdomain ownership, and register classifier static gates. See `build/verification/smmu-core-routing-lane-20260511.log`. |
| QBox guest smoke | `QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260511-core-routing QBOX_BOOT_TIMEOUT=70 QBOX_IREE_LOGIN_DELAY=24 QBOX_IREE_AFTER_COMMAND_DELAY=24 ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` | Pass; output matched `1x1x2x2xf32=[[[54 63][90 99]]]` See `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-core-routing.driver.log` and `.log`. |
| SMMUv3 static checker | `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/qbox-smmuv3-compliance-core-routing-20260511.json` | Pass; includes `tbu:architected-core-owner` and keeps full SMMUv3 compliance `not_claimed`. See `build/verification/smmu-core-routing-static-20260511.log`. |

The queue-helper follow-up reuses the same verification scope and wrote fresh
evidence:

- Build: `build/verification/smmu-core-queue-helpers-build-20260511.log`
- Component test: `build/verification/smmu-core-queue-helpers-ctest-20260511.log`
- Syntax: `build/verification/smmu-core-queue-helpers-bashn-20260511.log`,
  `build/verification/smmu-core-queue-helpers-pycompile-20260511.log`

The endpoint-replay redrive-state follow-up wrote fresh evidence:

- Build: `build/verification/smmu-core-endpoint-redrive-state-build-20260511.log`
- Component test: `build/verification/smmu-core-endpoint-redrive-state-ctest-20260511.log`
- Syntax: `build/verification/smmu-core-endpoint-redrive-state-bashn-20260511.log`,
  `build/verification/smmu-core-endpoint-redrive-state-bashn-all-20260511.log`,
  `build/verification/smmu-core-endpoint-redrive-state-pycompile-20260511.log`
- Lane/static: `build/verification/smmu-core-endpoint-redrive-state-lane-20260511.log`,
  `build/verification/smmu-core-endpoint-redrive-state-static-20260511.log`
  (`SUMMARY {"pass": 610}`, `full_smmuv3_compliance: not_claimed`)
- Diff checks:
  `build/verification/smmu-core-endpoint-redrive-state-qbox-diff-check-20260511.log`,
  `build/verification/smmu-core-endpoint-redrive-state-superproject-diff-check-20260511.log`
- Guest smoke:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-core-endpoint-redrive-state.driver.log`
  (`1x1x2x2xf32=[[[54 63][90 99]]]`)

The descriptor-walk state follow-up wrote fresh evidence:

- Build: `build/verification/smmu-core-descriptor-walk-state-build-20260511.log`
- Component test:
  `build/verification/smmu-core-descriptor-walk-state-ctest-20260511.log`
- Syntax:
  `build/verification/smmu-core-descriptor-walk-state-bashn-20260511.log`,
  `build/verification/smmu-core-descriptor-walk-state-bashn-all-20260511.log`,
  `build/verification/smmu-core-descriptor-walk-state-pycompile-20260511.log`
- Lane/static:
  `build/verification/smmu-core-descriptor-walk-state-lane-20260511.log`,
  `build/verification/smmu-core-descriptor-walk-state-static-20260511.log`
  (`SUMMARY {"pass": 610}`, `full_smmuv3_compliance: not_claimed`)
- Diff checks:
  `build/verification/smmu-core-descriptor-walk-state-qbox-diff-check-20260511.log`,
  `build/verification/smmu-core-descriptor-walk-state-superproject-diff-check-20260511.log`
- Guest smoke:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-core-descriptor-walk-state.driver.log`
  (`1x1x2x2xf32=[[[54 63][90 99]]]`)

The descriptor-fetch lifecycle follow-up wrote fresh evidence:

- Build:
  `build/verification/smmu-core-descriptor-fetch-lifecycle-build-20260511.log`
- Component test:
  `build/verification/smmu-core-descriptor-fetch-lifecycle-ctest-20260511.log`
- Syntax:
  `build/verification/smmu-core-descriptor-fetch-lifecycle-bashn-20260511.log`,
  `build/verification/smmu-core-descriptor-fetch-lifecycle-bashn-all-20260511.log`,
  `build/verification/smmu-core-descriptor-fetch-lifecycle-pycompile-20260511.log`
- Lane:
  `build/verification/smmu-core-descriptor-fetch-lifecycle-lane-20260511.log`
- Static checker:
  `build/verification/smmu-core-descriptor-fetch-lifecycle-static-20260511.log`,
  `build/verification/qbox-smmuv3-compliance-core-descriptor-fetch-lifecycle-20260511.json`
  (`SUMMARY {"pass": 610}`, `full_smmuv3_compliance: not_claimed`)
- Diff check:
  `build/verification/smmu-core-descriptor-fetch-lifecycle-qbox-diff-check-20260511.log`,
  `build/verification/smmu-core-descriptor-fetch-lifecycle-superproject-diff-check-20260511.log`
- Runtime smoke:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-core-descriptor-fetch-lifecycle.driver.log`,
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-core-descriptor-fetch-lifecycle.log`
  (`1x1x2x2xf32=[[[54 63][90 99]]]`)

The descriptor-memory-read-interface follow-up wrote fresh evidence:

- Build:
  `build/verification/smmu-core-descriptor-memory-read-interface-build-20260511.log`
- Component test:
  `build/verification/smmu-core-descriptor-memory-read-interface-ctest-20260511.log`
- Syntax:
  `build/verification/smmu-core-descriptor-memory-read-interface-bashn-20260511.log`,
  `build/verification/smmu-core-descriptor-memory-read-interface-bashn-all-20260511.log`,
  `build/verification/smmu-core-descriptor-memory-read-interface-pycompile-20260511.log`
- Lane/static:
  `build/verification/smmu-core-descriptor-memory-read-interface-lane-20260511.log`,
  `build/verification/smmu-core-descriptor-memory-read-interface-static-20260511.log`
  (`SUMMARY {"pass": 610}`, `full_smmuv3_compliance: not_claimed`)
- Diff checks:
  `build/verification/smmu-core-descriptor-memory-read-interface-qbox-diff-check-20260511.log`,
  `build/verification/smmu-core-descriptor-memory-read-interface-superproject-diff-check-20260511.log`
- Guest smoke:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-core-descriptor-memory-read-interface.driver.log`,
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-core-descriptor-memory-read-interface.log`
  (`1x1x2x2xf32=[[[54 63][90 99]]]`)

The core queue-state storage follow-up adds these fresh artifacts:

- Build: `build/verification/smmu-core-queue-state-build-20260511.log`
- Component test: `build/verification/smmu-core-queue-state-ctest-20260511.log`

The core stream/context-state storage follow-up adds these fresh artifacts:

- Build: `build/verification/smmu-core-stream-context-state-build-20260511.log`
- Component test:
  `build/verification/smmu-core-stream-context-state-ctest-20260511.log`

The core walker-state storage follow-up adds these fresh artifacts:

- Build: `build/verification/smmu-core-walker-state-build-20260511.log`
- Component test: `build/verification/smmu-core-walker-state-ctest-20260511.log`

The core fault/replay-state storage follow-up adds these fresh artifacts:

- Build: `build/verification/smmu-core-fault-replay-state-build-20260511.log`
- Component test:
  `build/verification/smmu-core-fault-replay-state-ctest-20260511.log`

The core walker-helper routing follow-up adds these fresh artifacts:

- Build: `build/verification/smmu-core-walker-helpers-build-20260511.log`
- Component test:
  `build/verification/smmu-core-walker-helpers-ctest-20260511.log`

The core descriptor-helper routing follow-up adds these fresh artifacts:

- Build: `build/verification/smmu-core-descriptor-helpers-build-20260511.log`
- Component test:
  `build/verification/smmu-core-descriptor-helpers-ctest-20260511.log`

The core fault-record-helper routing follow-up adds these fresh artifacts:

- Build: `build/verification/smmu-core-fault-record-helpers-build-20260511.log`
- Component test:
  `build/verification/smmu-core-fault-record-helpers-ctest-20260511.log`

The core stall-record storage follow-up adds these fresh artifacts:

- Build: `build/verification/smmu-core-stall-records-build-20260511.log`
- Component test:
  `build/verification/smmu-core-stall-records-ctest-20260511.log`

The core endpoint-replay-record storage follow-up adds these fresh artifacts:

- Build:
  `build/verification/smmu-core-endpoint-replay-records-build-20260511.log`
- Component test:
  `build/verification/smmu-core-endpoint-replay-records-ctest-20260511.log`

The core endpoint-replay-transition follow-up adds these fresh artifacts:

- Build:
  `build/verification/smmu-core-endpoint-replay-transitions-build-20260511.log`
- Component test:
  `build/verification/smmu-core-endpoint-replay-transitions-ctest-20260511.log`

The core endpoint-redrive-transaction-interface follow-up adds these fresh
artifacts:

- Build:
  `build/verification/smmu-core-endpoint-redrive-transaction-interface-build-20260511.log`
- Component test:
  `build/verification/smmu-core-endpoint-redrive-transaction-interface-ctest-20260511.log`
- Static checker:
  `build/verification/smmu-core-endpoint-redrive-transaction-interface-static-20260511.log`
  (`SUMMARY {"pass": 610}` and `full_smmuv3_compliance` remains
  `not_claimed`)
- Buildroot lane:
  `build/verification/smmu-core-endpoint-redrive-transaction-interface-lane-20260511.log`
- Guest runtime smoke:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-core-endpoint-redrive-transaction-interface.driver.log`
  with expected output `1x1x2x2xf32=[[[54 63][90 99]]]`.

The core adapter-io-executor follow-up adds these fresh artifacts:

- Build:
  `build/verification/smmu-core-adapter-io-executor-build-20260511.log`
- Component test:
  `build/verification/smmu-core-adapter-io-executor-ctest-20260511.log`
- Static checker:
  `build/verification/smmu-core-adapter-io-executor-static-rerun-20260511.log`
  (`SUMMARY {"pass": 610}` and `full_smmuv3_compliance` remains
  `not_claimed`)
- Buildroot lane:
  `build/verification/smmu-core-adapter-io-executor-lane-20260511.log`
- Diff checks:
  `build/verification/smmu-core-adapter-io-executor-qbox-diff-check-20260511.log`
  and
  `build/verification/smmu-core-adapter-io-executor-superproject-diff-check-20260511.log`
- Guest runtime smoke:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-core-adapter-io-executor.driver.log`
  with expected output `1x1x2x2xf32=[[[54 63][90 99]]]`.

The core swappable-io-executor follow-up adds these fresh artifacts:

- Build:
  `build/verification/smmu-core-swappable-io-executor-build-20260511.log`
- Component test:
  `build/verification/smmu-core-swappable-io-executor-ctest-20260511.log`
- Static checker:
  `build/verification/smmu-core-swappable-io-executor-static-20260511.log`
  (`SUMMARY {"pass": 610}` and `full_smmuv3_compliance` remains
  `not_claimed`)
- Buildroot lane:
  `build/verification/smmu-core-swappable-io-executor-lane-20260511.log`
- Diff checks:
  `build/verification/smmu-core-swappable-io-executor-qbox-diff-check-20260511.log`
  and
  `build/verification/smmu-core-swappable-io-executor-superproject-diff-check-20260511.log`
- Guest runtime smoke:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-core-swappable-io-executor.driver.log`
  with expected output `1x1x2x2xf32=[[[54 63][90 99]]]`.

## Current classification

- SMMU-COMP-010 remains a **functional slice**.
- The repository now has a durable ownership/core contract plus routed
  register-aperture, core-owned queue storage, core-owned stream/context
  selector storage, core-owned walker state, core-owned fault/replay scalar
  protocol state, queue-helper boundaries, and walker-helper boundaries that
  prevent silent ambiguity between the SystemC Apollo TBU and any future QEMU
  SMMUv3 bridge. Pure Stream-table, STE, CD, and effective-EATS descriptor
  decode helpers plus EVENTQ fault-record layout and replay/status packing
  helpers are also now routed through that core boundary. STAG stall-record
  table storage and lookup helpers now live behind the core boundary too.
  Endpoint replay payload record storage, pending/any lookup, reset helpers,
  allocation/retirement state transitions, redrive payload/status transitions,
  and downstream transaction request/result wrapping are now also core-owned;
  descriptor/replay physical I/O call sites now cross a swappable adapter
  executor interface. Descriptor-walk validation, fetch-address
  planning, descriptor step classification, and leaf PA/fault state transitions
  are now core-owned as well. Descriptor-fetch lifecycle bookkeeping and
  descriptor-fetch abort fault-state transitions are also now core-owned;
  descriptor memory-read request/result wrapping is core-owned too.
- Remaining work: connect a verified external memory/replay backend or QEMU
  bridge through the swappable I/O executor before changing the canonical owner
  or claiming full SMMUv3 compliance.
