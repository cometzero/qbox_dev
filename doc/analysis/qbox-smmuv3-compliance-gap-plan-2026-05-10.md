# QBox SMMUv3 compliance gap and improvement plan

- Date: 2026-05-10
- Workspace: `/build/qbox_dev`
- Target branch: `feature/qbox_dev`
- Scope: QBox Apollo ARM SMMUv3 model, `sources/smmu` reference corpus,
  Linux probe, Hexagon DMA/IREE integration, and verification documents.
- Goal: 현재 QBox의 SMMUv3 구현이 어느 수준까지 검증됐는지와 full ARM
  SMMUv3 compliance model까지 남은 차이를 분리하고, 구현 순서와 완료 기준을
  정한다.

## Executive summary

QBox는 이미 Apollo Hexagon DMA/IREE offload 경로에서 유용한 SMMUv3
functional slice를 갖고 있다. Linux device tree는 `arm,smmu-v3` 노드를
제공하고, QBox platform은 QEMU `arm-smmuv3` wrapper와 별도
`apollo_smmu_tbu` data path를 함께 배치한다. Apollo TBU는 custom MMIO
register block으로 dynamic map/unmap, 4KB page split, STE/CD fetch,
4-level descriptor probe, ATS/PRI response accounting, invalid STE negative
fault replay를 제공한다.

다만 이는 full bit-exact ARM SMMUv3 IP 모델이 아니다. 현재 구현은
architected register file, command/event/PRI memory queues, complete STE/CD
bitfields, stage-1/stage-2/nested translation, ATS/PRI packet semantics,
fault/event record formatting, GERROR/MSI/GIC interrupt ordering을 모두
구현하지 않는다. 그러므로 다음 단계는 기존 functional ABI를 깨지 않도록
compatibility layer로 유지하면서, `sources/smmu`를 ground-truth behavioral
oracle로 삼아 QBox 안에 architected SMMUv3 core와 검증 matrix를 단계적으로
추가하는 것이다.

## Ground-truth and evidence snapshot

### Reference corpus

- `sources/smmu` is pinned as a git submodule at
  `f15d96c9aefbd5f180a20cbc3ed9515937df860c`
  (`smmu-release-v1.7.8-07May2026`).
- The submodule includes the spec-derived corpus
  `IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`,
  C++ and Rust implementations, tests, and synthesis docs.
- The reference README claims broad conformance and lists stream architecture,
  two-stage translation, security-state handling, fault handling, event queue,
  and PRI features (`sources/smmu/README.md:15-25`). It also explicitly labels
  some omissions as acceptable software-model gaps, including no real
  page-table walker, no physical MMIO register map, no hardware-level memory
  bus, and limited ATS translated/prefetched hardware paths
  (`sources/smmu/README.md:544-623`).
- Current local build evidence must override stale README claims: C++ CTest has
  199/200 passing and fails `test_bug3_stall_pending_fields`
  (`build/verification/smmu-reference-cpp-v1.7.8-build-20260510.log:1114-1126`),
  while Rust cargo build completes
  (`build/verification/smmu-reference-rust-build-20260510.log:1-31`).
- License risk: `sources/smmu` contains a top-level GPLv3 `LICENSE` plus
  `LICENSE-APACHE` and `LICENSE-MIT`. Treat it as reference material until a
  repository license decision is made; do not copy code into BSD-licensed QBox
  paths without a license audit.

### QBox implementation evidence

- QEMU SMMUv3 wrapper: `sources/qbox/qemu-components/arm_smmuv3/include/arm-smmuv3.h:17-73`
  creates a thin `arm-smmuv3` QEMU device wrapper with one MMIO target socket,
  four IRQ outputs, and a `stage` property. It wires QEMU, but it does not
  implement a local architectural walker or queue model.
- Platform wiring: `sources/qbox/platforms/buildroot/conf_aarch64.lua:39-52`
  defines Apollo SMMUv3 and Hexagon DMA constants. Lines `142-150` instantiate
  `arm_smmuv3` and wire eventq, priq, cmdq-sync, and gerror IRQs. Lines
  `172-188` instantiate `apollo_smmu_tbu` and route `apollo_hexagon_dma` through
  its `translated_dma` socket with `stream_id = 0x1`.
- Linux-visible description: `configs/linux/apollo_soc.dts:116-126` describes
  `iommu@1c200000` as `arm,smmu-v3`; `configs/linux/apollo_soc.dts:128-139`
  attaches the Apollo Hexagon node with `iommus = <&smmu 0x1>` and the
  `smmu-translated` DMA path.
- Apollo TBU model: `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h:24-51`
  defines TLM sockets and parameters; lines `55-144` define custom registers,
  feature bits, and simplified descriptor constants; lines `180-223` translate
  fixed or dynamic mappings; lines `332-337` advertise all functional feature
  bits; lines `504-575` implement a 4-level descriptor probe; lines `577-643`
  fetch STE/CD descriptors; lines `645-721` log ATS/PRI responses and negative
  replay; lines `744-888` expose the custom register block; lines `944-979`
  split and forward translated TLM segments.
- Apollo DMA model: `sources/qbox/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h:30-39`
  exposes direct and translated DMA sockets; lines `92-101` define 256KiB max
  transfer, large tensor, multi-queue, and async fence capability bits; lines
  `292-303` model async IRQ/fence as status registers; lines `305-378` execute
  DMA through the selected direct or translated path.
- Linux guest probe: `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c:370-568`
  stages STE/CD/page-table descriptors in shared SRAM, triggers the TBU probe,
  checks descriptor/protocol status, corrupts the STE, and verifies negative
  fault replay.
- Smoke contract: `scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh:33-80`
  requires boot markers for STE/CD walk, 4-level descriptor walk, ATS/PRI
  response, fault replay, SG DMA, dynamic HAL plugin, and final tiny-CNN output.
- Verification report: `doc/verification/qbox-smmu-stream-context-replay-2026-05-10.md:11-26`
  classifies the current work as a compliance-oriented integration slice, not a
  full SMMUv3 register/queue/protocol/interrupt model. Lines `96-123` record the
  runtime markers and the final readiness classification.
- Task plan boundary: `doc/spec/qbox-iree-cnn-pipeline-tasks.md:37-45` keeps
  `IREE-CNN-SMMU-001` open for full register/descriptor/protocol compliance and
  marks STE/CD walk plus negative replay as partial/completed slices. Lines
  `103-131` repeat the current boundary and remaining bit-exact work.

## Current QBox SMMUv3 architecture

```text
A710 Linux guest
  |
  | DT: arm,smmu-v3 + Apollo Hexagon iommus stream-id 0x1
  v
QEMU arm-smmuv3 wrapper
  - Linux-visible MMIO and 4 IRQs
  - QEMU/libqemu-owned SMMUv3 behavior

Apollo Hexagon DMA data plane
  apollo_hexagon_dma.translated_dma
      -> apollo_smmu_tbu.upstream
          -> custom functional translation / probes
          -> router.target_socket
              -> shared SRAM / DDR
```

The important architectural split is that the Linux-visible QEMU `arm-smmuv3`
wrapper and the Apollo Hexagon DMA translation path are not one unified SMMUv3
core today. The QEMU wrapper makes Linux see an SMMUv3, while the Apollo TBU is
an independent SystemC/TLM functional bridge used by the Hexagon DMA path.

### Ownership contract and platform invariants

Until a QEMU/libqemu translation bridge is implemented and verified, the Apollo
TBU/SystemC core is the canonical owner of translation, queue, and fault state
for Apollo Hexagon DMA. The QEMU `arm-smmuv3` wrapper remains the
Linux-visible facade/control-plane device for the A710 guest.

| Component | Current responsibility | Not counted as proof of |
| --- | --- | --- |
| QEMU `arm_smmuv3` wrapper | `arm-smmuv3` device construction, `stage` property, optional PCI host link, MMIO socket, four IRQ output sockets | Apollo Hexagon DMA translation correctness, Apollo TBU queues, Apollo fault/event records |
| Apollo `apollo_smmu_tbu` | Hexagon DMA StreamID/IOVA translation, compatibility TBU registers, STE/CD probe, descriptor walk slice, ATS/PRI/fault observability | Generic Linux SMMUv3 driver register compliance until architected registers and queues exist |
| Apollo Linux probe | Shared-SRAM descriptor staging, current positive probe, invalid STE negative replay, feature marker checks | Full SMMUv3 protocol or interrupt compliance |
| Hexagon/IREE smoke | End-to-end compatibility slice through translated DMA, queues/fences, and tiny-CNN output | Full SMMUv3 compliance by itself |

Named IRQ/platform coherence must be checked by name, not only by IRQ count:

- QBox platform wiring: `irq_out_0 -> eventq`, `irq_out_1 -> priq`,
  `irq_out_2 -> cmdq-sync`, `irq_out_3 -> gerror`.
- Linux DTS must keep the `arm,smmu-v3` node at `0x1c200000` with
  `#iommu-cells = <1>` and named interrupts for eventq, gerror, cmdq-sync, and
  priq.
- Apollo Hexagon DTS `iommus = <&smmu 0x1>` must match the platform
  `APOLLO_HEXAGON_STREAM_ID = 0x1` and the DMA/TBU `stream_id` parameters.
- DTS `apollo,dma-path = "smmu-translated"` must match the QBox connection from
  `apollo_hexagon_dma.translated_dma` to `apollo_smmu_tbu.upstream`.
- Any positional mismatch between platform comments and DTS interrupt-name order
  must be resolved with an explicit named-IRQ validation, not inferred from line
  ordering.

## Gap matrix

| Area | Current QBox state | Gap to full ARM SMMUv3 compliance | Priority | Acceptance evidence |
| --- | --- | --- | --- | --- |
| Register file | QEMU wrapper exposes QEMU `arm-smmuv3`; Apollo TBU exposes custom regs. | No Apollo-local architected CR0/CR1/CR2, IDR, GBPA, STRTAB, queue base/prod/cons, GERROR/GERRORN, IRQ/MSI registers with side effects. | P0 | Static register map doc plus unit tests for reset values, enable/ack, queue register side effects. |
| Command queue | No Apollo TBU command queue. | Missing memory-backed CMDQ ring, PROD/CONS/wrap, CMD_SYNC, CFGI, TLBI, ATC_INV, PRI_RESP, RESUME, STALL_TERM processing. | P0 | CMDQ unit tests derived from `sources/smmu` command entry tests and guest negative probes. |
| Event/PRI/fault queues | Counters and log markers exist. | Missing architected event/PRI records, queue overflow/OVFLG, stall-pending retention, fault syndrome fields, PRG handling, dequeue semantics. | P0 | EventQ/PRIQ record binary format tests; overflow and stall replay suite; guest-visible markers. |
| Stream table / CD walk | Fetches first two 64-bit words for one flat STE/CD path. | Missing STRTAB_BASE/CFG, linear and 2-level stream tables, full STE.Config, S1DSS, EATS, S2 config, PASID/CD indexing, invalid/reserved encodings. | P0 | STE/CD decode table tests; invalid SID and invalid STE/CD negative replay tests. |
| Page-table walker | 4KB, 4-level descriptor probe with simple table/page checks. | Missing TCR/MAIR/OAS/IPS, start-level selection, 4K/16K/64K granules, block descriptors, AP/SH/AttrIndx/PXN/UXN/AF/DBM, table walk aborts, stage-2 and nested translation. | P1 | Stage-1, stage-2, and two-stage tests cross-checked against `sources/smmu` Rust/C++ behavior. |
| TLB/ATC/cache | Small ATS cache counter/fill model. | Missing architected TLB tags by VMID/ASID/PASID/SID, TLBI invalidations, STE/CD cache invalidation, endpoint ATC invalidation semantics. | P1 | TLBI/ATC_INV tests and counters proving stale translations are invalidated. |
| ATS protocol | Logs success/fault response and increments counters. | Missing ATS Translation Request/Completion statuses, ATSCHK/EATS checks, Secure-stream restrictions, translated transaction validation, event priority. | P1 | ATS negative test suite: UR/CA/success, REC_CFG_ATS gates, translated transaction faults. |
| PRI protocol | PRI is observable as counters/logs. | Missing PRIQ packet model, PRG tags, PRI_RESP command handling, overflow auto-failure, PPRG lifecycle. | P1 | PRI queue clear, overflow, PRI_RESP, and replay tests. |
| Interrupt/MSI/GIC | QEMU wrapper has four IRQ outputs; Apollo TBU has no IRQ outputs. DMA has polling status/fence registers. | Missing Apollo TBU eventq/priq/cmdq-sync/gerror IRQ lines, MSI ordering, GERROR/GERRORN behavior, actual async DMA interrupt delivery. | P1 | GIC-visible interrupt tests plus register ordering assertions. |
| Multi-master/SID topology | Single Apollo Hexagon StreamID `0x1` and one translated window. | Missing multiple masters, independent StreamIDs, invalid SID isolation, PCI RID/PASID-style cases. | P2 | Multi-SID platform config and negative isolation tests. |
| IREE HAL registry | Repo-local plugin and executable_plugin export/load are validated. | Upstream IREE HAL driver/device registry, build system integration, and upstream tests remain pending. | P2 | `iree-run-module` discovers `apollo-hexagon` without repo-local shim and upstream-style HAL tests pass. |

## Improvement plan

### Phase 0 — Freeze the compliance inventory

Objective: make overclaiming impossible before implementation starts.

Tasks:

1. Add a QBox compliance checklist that maps each SMMUv3 area to one of:
   `implemented`, `functional-slice`, `reference-only`, `missing`, or
   `blocked`.
2. Point every row to a concrete source or verification artifact:
   `apollo_smmu_tbu.h`, Linux probe, smoke scripts, `sources/smmu` tests, and
   existing verification logs.
3. Mark `sources/smmu` as a behavioral oracle, not a bit-exact MMIO hardware
   oracle, because its own docs classify no physical MMIO register map and no
   hardware bus as software-model gaps.
4. Add the known C++ reference failure to the checklist so the pinned reference
   is not treated as a perfect release oracle.
5. Make overclaiming machine-checkable: no row or section may claim
   `implemented`, `full compliance`, or `architected SMMUv3 model` unless it
   names the passing unit/model test, platform/DTS/IRQ check, and runtime smoke
   evidence that justify the claim.

Deliverables:

- `doc/spec/qbox-smmuv3-compliance-checklist.md`
- Optional JSON output from a script such as
  `scripts/check_qbox_smmuv3_compliance.py`

Done when:

- `git diff --check` passes.
- Existing Buildroot lane static checks still pass.
- The checklist clearly distinguishes QBox runtime proof from reference-only
  desired behavior.

### Phase 1 — Split compatibility ABI from architected core

Objective: keep the existing guest smoke stable while introducing an
architected SMMUv3 engine behind the Apollo TBU.

Tasks:

1. Keep the current custom TBU registers as a debug/compatibility aperture used
   by the Apollo Linux selftest.
2. Introduce an internal `apollo_smmuv3_core` component or namespace that owns:
   register state, stream table config, queue state, decoder utilities,
   translation state, and fault/event records.
3. Add an adapter so the current `apollo_smmu_tbu` TLM path calls the core for
   translation instead of duplicating feature-specific logic.
4. Make direct code reuse from `sources/smmu` conditional on license audit; if
   license compatibility is unclear, port behavior through tests/spec notes
   rather than copying implementation.

Candidate ownership:

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
- New files under
  `sources/qbox/systemc-components/apollo_smmu_tbu/include/` and `src/`
- `scripts/check_buildroot_arm64_lane.sh` for static guards

Done when:

- Current smoke markers in `scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh`
  still pass.
- TBU internal state has a single canonical translation path.

### Phase 2 — Implement architected register and queue surfaces

Objective: make software-visible SMMUv3 state explicit and testable.

Tasks:

1. Implement register reset values and side effects for the minimum viable
   control surface: CR0/CR0ACK, CR1, CR2, IDR0-IDR5, AIDR, GBPA,
   STRTAB_BASE/CFG, CMDQ_BASE/PROD/CONS, EVENTQ_BASE/PROD/CONS,
   PRIQ_BASE/PROD/CONS, GERROR/GERRORN, IRQ_CTRL/ACK.
2. Implement memory-backed circular queue helpers with index/wrap/overflow
   semantics. Use `sources/smmu/TASKS_CPP_OPERATION.md:141-168` as a behavior
   checklist for PROD/CONS, wrap, and visibility semantics.
3. Decode command entries for CFGI, TLBI, ATC_INV, PRI_RESP, RESUME,
   STALL_TERM, and SYNC.
4. Emit event and PRI records into guest memory, not only internal counters.

Done when:

- Unit tests can fill and drain CMDQ/EVENTQ/PRIQ rings with wrap and overflow.
- A guest selftest can observe queue records and IRQ status for an injected
  invalid STE.

### Phase 3 — Complete stream/context descriptor and translation walk

Objective: replace the current minimal STE/CD/page probe with a real
architected decode path.

Tasks:

1. Decode STRTAB linear and 2-level formats.
2. Decode STE fields required for Config, stream enable, S1/S2 enable, S1DSS,
   S1CDMax, S1ContextPtr, EATS, STRW, S2TTB, S2T0SZ, S2PS, VMID, and fault
   behavior flags.
3. Decode CD fields for TCR, TTBR, MAIR, ASID, TBI, HA/HD, EPD, WXN/UWXN, and
   permission behavior.
4. Implement 4K/16K/64K granule walks, start-level selection, table/block/page
   descriptors, AF/DBM, attributes, and permission checks.
5. Add stage-1-only, stage-2-only, and two-stage translation paths.
6. Keep the current 4KB/4-level probe as one compatibility test inside the
   larger suite.

Reference tests to mine:

- `sources/smmu/rust/smmu/tests/test_bug_rust1_stage2_ptw.rs`
- `sources/smmu/rust/smmu/tests/test_bug_rust3_s1dss.rs`
- `sources/smmu/cpp/tests/integration/test_two_stage_translation.cpp`
- `sources/smmu/cpp/tests/unit/test_smmu_phase1_two_stage_errors.cpp`

Done when:

- Positive and negative translations match the reference oracle for selected
  stage-1, stage-2, and nested cases.
- Guest logs still include the existing `SMMUv3 architectural descriptor probe
  ok` marker plus new stage-specific negative markers.

### Phase 4 — Implement ATS/PRI/fault replay protocol semantics

Objective: move from log/counter observability to protocol-level behavior.

Tasks:

1. Model ATS Translation Request outcomes: UR, CA, and Success responses,
   including ATSCHK/EATS, secure stream restrictions, disabled SMMU behavior,
   and translated transaction checks.
2. Model endpoint ATC invalidation as a command/response state machine, even if
   the endpoint is initially a synthetic Apollo endpoint.
3. Model PRI packets, PRG tags, queue overflow auto-failure, and CMD_PRI_RESP.
4. Model stall and terminate fault modes, including fault replay through
   CMD_RESUME and CMD_STALL_TERM.
5. Expand the negative replay suite beyond invalid STE to invalid SID, invalid
   CD, page-table fault, access fault, permission fault, stage-2 fault, PRI
   overflow, event queue overflow, and ATS forbidden cases.

Reference checklist:

- `sources/smmu/TASKS_CPP_OPERATION.md:230-297` for ATS and ATS configuration.
- `sources/smmu/TASKS_CPP_OPERATION.md:406-455` for fault model and stall
  behavior.
- `sources/smmu/TASKS_CPP_OPERATION.md:494-499` for ATS/PRI hardware flag
  update requirements.

Done when:

- Negative replay tests produce architected event/PRI records, not only log
  counters.
- Fault replay remains deterministic across repeated guest smoke runs.

### Phase 5 — Wire interrupt, MSI, and async completion semantics

Objective: make queue/fault/protocol events visible through architectural
interrupt paths.

Tasks:

1. Add Apollo TBU IRQ outputs for eventq, priq, cmdq-sync, and gerror, matching
   the SMMUv3 IRQ names already present in the platform and DTS.
2. Implement GERROR/GERRORN active-error semantics and IRQ_CTRL/ACK gating.
3. Decide whether the Apollo model should use wired SPIs only or a synthetic MSI
   write path for queue interrupts.
4. Upgrade `apollo_hexagon_dma` async fence from register-only pending bits to
   an actual interrupt line, while preserving polling fallback for smoke tests.

Reference checklist:

- `sources/smmu/TASKS_CPP_OPERATION.md:595-608` for interrupt sources and MSI
  synchronization.

Done when:

- A guest test can block on an interrupt rather than only polling custom status
  registers.
- Existing queue 0/1 async fence markers still pass.

### Phase 6 — Integrate with QEMU SMMUv3 and upstream IREE HAL registry

Objective: remove architectural duplication where possible and upstream the
runtime-facing HAL path.

Tasks:

1. Decide the long-term QEMU strategy:
   - Short term: keep QEMU `arm_smmuv3` as Linux-visible control plane and use
     the Apollo architected TBU core for Hexagon DMA.
   - Long term: investigate a libqemu/QBox bridge so Apollo DMA traffic can use
     QEMU SMMUv3 translation state directly, or intentionally document why the
     SystemC core remains the canonical Apollo SMMUv3 model.
2. Move the repo-local Apollo Hexagon IREE HAL from a `dlopen()` runner/plugin
   into an upstream-style HAL driver/device registry path.
3. Add build integration and tests so `iree-run-module` can discover/open the
   Apollo HAL device without the repo-local shim.
4. Keep executable plugin export/load tests as a compatibility check, but do not
   count them as full HAL device registry completion.

Done when:

- The QBox SMMUv3 plan names one canonical translation state owner.
- `IREE-CNN-UPSTREAM-001` in `doc/spec/qbox-iree-cnn-pipeline-tasks.md` can be
  reclassified from pending to implemented with upstream-style tests.

## Proposed backlog

| ID | Priority | Area | Primary files | Deliverable | Stop condition |
| --- | --- | --- | --- | --- | --- |
| SMMU-COMP-000 | P0 | Inventory | `doc/spec/`, `scripts/` | Compliance checklist and optional JSON checker | No unsupported “full compliance” claim remains. |
| SMMU-COMP-010 | P0 | Core split | `apollo_smmu_tbu` | Architected core object plus compatibility adapter | Current guest smoke still passes. |
| SMMU-COMP-020 | P0 | Register/queues | `apollo_smmu_tbu` | Register map and CMDQ/EVENTQ/PRIQ ring helpers | Unit wrap/overflow tests pass. |
| SMMU-COMP-030 | P0 | STE/CD | `apollo_smmu_tbu`, Linux probe | Linear and 2-level STRTAB, CD lookup, invalid descriptor events | Invalid SID/STE/CD tests pass. |
| SMMU-COMP-040 | P1 | Walker | `apollo_smmu_tbu` | Granule/start-level/stage-1/stage-2 walker | Reference-matched translation tests pass. |
| SMMU-COMP-050 | P1 | Fault replay | TBU + Linux probe | Event records, stall/terminate, replay commands | Negative replay matrix passes. |
| SMMU-COMP-060 | P1 | ATS/PRI | TBU + synthetic endpoint | ATS/PRI packet-level model | ATS/PRI protocol tests pass. |
| SMMU-COMP-070 | P1 | IRQ/MSI | Platform + TBU + Linux probe | eventq/priq/cmdq-sync/gerror IRQs | Guest interrupt wait test passes. |
| SMMU-COMP-080 | P2 | Multi-SID | Platform + DTS + probe | Multiple DMA masters and invalid SID isolation | Multi-master smoke passes. |
| SMMU-COMP-090 | P2 | IREE upstream | IREE integration tree/buildroot package | Upstream-style Apollo HAL registry | `iree-run-module` discovers Apollo HAL directly. |

## Verification strategy

Use three layers so each phase has fast feedback before full boot smoke:

1. Static/source contracts
   - `./scripts/check_buildroot_arm64_lane.sh`
   - `./scripts/check_iree_cnn_pipeline_readiness.py --json ...`
   - A new SMMUv3 compliance checklist script.
2. Unit/model tests
   - QBox TBU core unit tests for register reset, queue wrap, descriptor decode,
     translation, ATS/PRI, and fault events.
   - Reference-derived test vectors from `sources/smmu` without blindly copying
     implementation code.
3. Runtime smoke
   - Existing Buildroot boot lane.
   - Existing Hexagon guest smoke markers from
     `scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh`.
   - New negative replay smoke covering invalid SID, invalid CD, permission
     fault, PRI overflow, event queue overflow, and IRQ delivery.

Evidence classification rule:

- Guest smoke proves the current Apollo/QBox compatibility slice only.
- Reference-derived unit/model tests prove selected model behavior.
- Platform/DTS/IRQ checks prove wiring invariants.
- Only the full backlog verification matrix can justify any `full compliance`
  wording.

Every milestone should produce one durable artifact bundle:

```bash
mkdir -p build/verification
{
  date -Is
  git status --short
  git submodule status --recursive
  # milestone-specific commands and grep gates here
} | tee build/verification/smmu-comp-<ID>-<YYYYMMDD-HHMMSS>.log
```

Each milestone stop condition requires both: fast checks/unit tests pass, and
runtime smoke either passes or is explicitly classified as blocked with exact
missing artifact/tool/log.

### Backlog verification matrix

#### SMMU-COMP-000 — Inventory/checklist

Commands:

```bash
python3 scripts/check_qbox_smmuv3_compliance.py \
  --json build/verification/qbox-smmuv3-compliance.json
./scripts/check_buildroot_arm64_lane.sh
git diff --check
```

Artifacts:

- `doc/spec/qbox-smmuv3-compliance-checklist.md`
- `build/verification/qbox-smmuv3-compliance.json`
- `build/verification/smmu-comp-000-<stamp>.log`

Pass gates:

- Every checklist row has a status, owner, source evidence, and runtime or
  explicit reference-only evidence.
- No row claims `implemented` without file/log proof.
- The known `sources/smmu` C++ `test_bug3_stall_pending_fields` failure is
  recorded.
- Platform/DTS invariants and named IRQ mapping are checked.

Fail gates:

- Any unsupported `full compliance` claim remains.
- Any `implemented` row lacks evidence.

Negative tests:

- Inject a fake `implemented` row without evidence; the checker must fail with
  the row ID and missing proof.
- Temporarily mismatch the documented StreamID or IRQ name in a fixture; the
  checker must fail without relying on positional IRQ order.

#### SMMU-COMP-010 — Core split

Commands:

```bash
bash -n scripts/*.sh
./scripts/build_qbox_buildroot_platform.sh \
  2>&1 | tee build/verification/qbox-platform-smmuv3-core-split.log
QBOX_BOOT_TIMEOUT=180 \
  ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh \
  2>&1 | tee build/verification/qbox-smmuv3-core-split-smoke.log
```

Artifacts:

- `build/verification/qbox-platform-smmuv3-core-split.log`
- `build/verification/qbox-smmuv3-core-split-smoke.log`
- TBU core ownership note in the implementation patch or checklist.

Pass gates:

- Existing markers still appear: `SMMUv3 architectural descriptor probe ok`,
  `SMMUv3 negative fault replay ok`, and the tiny-CNN tensor output.
- Apollo TBU translation, queue, and fault state route through one canonical
  core path.
- Compatibility custom TBU registers remain readable/writable for the current
  Linux probe.

Fail gates:

- Existing smoke markers regress.
- The old compatibility ABI bypasses the new core for normal translation.

Negative tests:

- Run invalid STE replay; the legacy marker and the new core-owned fault path
  must both trigger.
- Force a translation miss and confirm the core produces the fault before the
  TLM path returns an address error.

#### SMMU-COMP-020 — Registers/queues

Commands:

```bash
ctest --test-dir build/qbox-buildroot-platform \
  -R 'apollo_smmuv3_(regs|queue)' --output-on-failure \
  2>&1 | tee build/verification/apollo-smmuv3-regs-queue-ctest.log
QBOX_SMMU_QUEUE_SELFTEST=1 QBOX_BOOT_TIMEOUT=180 \
  ./scripts/run_qbox_buildroot_boot.sh \
  2>&1 | tee build/verification/qbox-smmuv3-queue-selftest.log
```

Artifacts:

- `build/verification/apollo-smmuv3-regs-queue-ctest.log`
- `build/verification/qbox-smmuv3-queue-selftest.log`
- Register reset/side-effect table in
  `doc/spec/qbox-smmuv3-compliance-checklist.md`.

Pass gates:

- CR0/CR0ACK, CR1, CR2, IDR0-IDR5, AIDR, GBPA, STRTAB, CMDQ, EVENTQ, PRIQ,
  GERROR/GERRORN, and IRQ_CTRL/ACK reset values match the documented map.
- CMDQ/EVENTQ/PRIQ rings prove PROD/CONS, wrap, empty/full, overflow, and
  visibility semantics.
- Guest can observe a queue record plus matching status/IRQ bit.

Fail gates:

- Queue producer/consumer desynchronizes.
- Overflow is silent.
- CMD_SYNC completion is missing or visible before its queue update.

Negative tests:

- Fill a queue to overflow.
- Submit malformed command opcode.
- Write invalid queue base alignment.
- Verify GERROR/EVENTQ record emission.

#### SMMU-COMP-030 — STE/CD

Commands:

```bash
ctest --test-dir build/qbox-buildroot-platform \
  -R 'apollo_smmuv3_(ste|cd|strtab)' --output-on-failure \
  2>&1 | tee build/verification/apollo-smmuv3-ste-cd-ctest.log
QBOX_SMMU_NEGATIVE=invalid_sid,invalid_ste,invalid_cd QBOX_BOOT_TIMEOUT=180 \
  ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh \
  2>&1 | tee build/verification/qbox-smmuv3-invalid-descriptor-smoke.log
```

Artifacts:

- `build/verification/apollo-smmuv3-ste-cd-ctest.log`
- `build/verification/qbox-smmuv3-invalid-descriptor-smoke.log`
- STE/CD decode coverage table.

Pass gates:

- Linear and 2-level STRTAB cases pass.
- STE.Config, S1DSS, EATS, S1CDMax, S1ContextPtr, S2 fields, CD TCR/TTBR/MAIR,
  ASID, TBI, HA/HD, and EPD coverage is recorded.
- Valid STE/CD produces translation; invalid SID/STE/CD emits architected event
  records.

Fail gates:

- Invalid descriptor falls through to DMA success.
- Reserved encoding is silently accepted.

Negative tests:

- SID outside STRTAB range.
- STE valid bit clear.
- CD pointer invalid or misaligned.
- PASID/CD index out of range.
- Reserved STE/CD encoding rejected.

#### SMMU-COMP-040 — Walker

Commands:

```bash
ctest --test-dir build/qbox-buildroot-platform \
  -R 'apollo_smmuv3_(ptw|stage1|stage2|nested)' --output-on-failure \
  2>&1 | tee build/verification/apollo-smmuv3-walker-ctest.log
ctest --test-dir build/smmu-cpp-v1.7.8 \
  -R 'stage|translation|ptw' --output-on-failure \
  2>&1 | tee build/verification/smmu-reference-walker-compare.log
```

Artifacts:

- `build/verification/apollo-smmuv3-walker-ctest.log`
- `build/verification/smmu-reference-walker-compare.log`
- Reference-vector comparison table. If the pinned reference still has unrelated
  failing tests, scope the comparison to the selected walker vectors and record
  the known failure separately.

Pass gates:

- Selected stage-1, stage-2, and nested vectors match the reference oracle.
- 4K, 16K, and 64K granules; start-level selection; table/block/page
  descriptors; AF/DBM; attributes; permissions; and address-size checks are
  covered or explicitly marked unsupported with matching IDR bits disabled.
- Existing `SMMUv3 architectural descriptor probe ok 4-level` remains passing.

Fail gates:

- Mismatch in output PA, IPA, attributes, permissions, or fault type.
- Unsupported granule is advertised as supported.

Negative tests:

- Translation fault.
- Address-size fault.
- Access flag fault.
- Permission fault.
- Unsupported granule.
- Stage-2 fault after successful stage-1 walk.

#### SMMU-COMP-050 — Fault replay

Commands:

```bash
ctest --test-dir build/qbox-buildroot-platform \
  -R 'apollo_smmuv3_fault' --output-on-failure \
  2>&1 | tee build/verification/apollo-smmuv3-fault-ctest.log
for i in 1 2 3; do
  QBOX_SMMU_NEGATIVE=all QBOX_BOOT_TIMEOUT=180 \
    ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh \
    2>&1 | tee build/verification/qbox-smmuv3-negative-replay-run${i}.log
done
```

Artifacts:

- `build/verification/apollo-smmuv3-fault-ctest.log`
- `build/verification/qbox-smmuv3-negative-replay-run{1,2,3}.log`
- Event-record byte-layout notes.

Pass gates:

- Event records include required syndrome fields, including stream/substream,
  address, class, stage, read/write, privilege, and IPA fields where applicable.
- Terminate and stall modes are distinguished.
- CMD_RESUME and CMD_STALL_TERM produce deterministic retry/termination.
- Three repeated runs produce the same ordered fault markers.

Fail gates:

- Fault appears only as a log counter without architected event record.
- Stall-pending records are lost when the queue fills.

Negative tests:

- Invalid SID.
- Invalid CD.
- Page-table fault.
- Permission fault.
- Event queue overflow.
- Stall pending then terminate.
- Resume retry after mapping fix.

#### SMMU-COMP-060 — ATS/PRI

Commands:

```bash
ctest --test-dir build/qbox-buildroot-platform \
  -R 'apollo_smmuv3_(ats|pri)' --output-on-failure \
  2>&1 | tee build/verification/apollo-smmuv3-ats-pri-ctest.log
QBOX_SMMU_PROTOCOL_SELFTEST=ats,pri QBOX_BOOT_TIMEOUT=180 \
  ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh \
  2>&1 | tee build/verification/qbox-smmuv3-ats-pri-smoke.log
```

Artifacts:

- `build/verification/apollo-smmuv3-ats-pri-ctest.log`
- `build/verification/qbox-smmuv3-ats-pri-smoke.log`
- ATS/PRI outcome matrix.

Pass gates:

- ATS success, UR, and CA outcomes are distinguishable.
- ATSCHK/EATS gating and secure-stream prohibition are covered or unsupported
  with matching IDR bits disabled.
- PRIQ records are memory-visible.
- PRI PRG tags and CMD_PRI_RESP clear/reject expected requests.

Fail gates:

- PRI is represented only by counters.
- ATS failure records are emitted when the spec says the endpoint response only
  should carry the failure.

Negative tests:

- ATS disabled by STE.
- EATS mismatch.
- Secure StreamID ATS request if Secure support is advertised.
- Translated transaction without valid ATC.
- PRIQ overflow auto-failure.
- PRI_RESP for unknown PRG.

#### SMMU-COMP-070 — IRQ/MSI

Commands:

```bash
ctest --test-dir build/qbox-buildroot-platform \
  -R 'apollo_smmuv3_irq' --output-on-failure \
  2>&1 | tee build/verification/apollo-smmuv3-irq-ctest.log
QBOX_SMMU_IRQ_SELFTEST=1 QBOX_BOOT_TIMEOUT=180 \
  ./scripts/run_qbox_buildroot_boot.sh \
  2>&1 | tee build/verification/qbox-smmuv3-irq-guest.log
```

Artifacts:

- `build/verification/apollo-smmuv3-irq-ctest.log`
- `build/verification/qbox-smmuv3-irq-guest.log`
- Platform/DTS named-IRQ coherence report.

Pass gates:

- eventq, priq, cmdq-sync, and gerror IRQs assert and deassert through ACK.
- Queue records are visible before interrupt assertion.
- Guest can block on an interrupt, not only poll custom registers.
- Existing queue 0/1 async fence markers still pass.
- Wired SPI versus MSI support is explicitly selected; the unimplemented path is
  marked N/A with IDR/feature bits consistent with that choice.

Fail gates:

- IRQ fires before queue record visibility.
- Positional IRQ order is assumed without name validation.

Negative tests:

- IRQ masked: event record exists but no interrupt.
- ACK without active IRQ is harmless.
- GERRORN clears only acknowledged bits.
- Back-to-back queue events preserve order.

#### SMMU-COMP-080 — Multi-SID

Commands:

```bash
ctest --test-dir build/qbox-buildroot-platform \
  -R 'apollo_smmuv3_multi_sid' --output-on-failure \
  2>&1 | tee build/verification/apollo-smmuv3-multi-sid-ctest.log
QBOX_SMMU_MULTI_SID_SELFTEST=1 QBOX_BOOT_TIMEOUT=180 \
  ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh \
  2>&1 | tee build/verification/qbox-smmuv3-multi-sid-smoke.log
```

Artifacts:

- `build/verification/apollo-smmuv3-multi-sid-ctest.log`
- `build/verification/qbox-smmuv3-multi-sid-smoke.log`
- Multi-master StreamID map.

Pass gates:

- Two or more masters translate through independent SIDs.
- Invalid SID cannot access another SID mapping.
- Per-SID invalidation affects only matching translations.

Fail gates:

- Any cross-SID data leak or shared stale translation.
- A hard-coded StreamID remains in the architected path after multi-SID support
  is enabled.

Negative tests:

- SID `0x1` attempts SID `0x2` buffer.
- Unknown SID DMA.
- PASID/CD index out of range.
- Per-SID TLBI invalidates only matching SID.

#### SMMU-COMP-090 — IREE upstream HAL

Commands:

```bash
./scripts/build_apollo_hexagon_guest_tools.sh \
  2>&1 | tee build/verification/apollo-iree-hal-registry-build.log
iree-run-module --device=apollo-hexagon \
  --module=build/iree-guest-artifacts/tiny-cnn/*.vmfb \
  --function=tiny_cnn_graph \
  2>&1 | tee build/verification/apollo-iree-run-module-direct.log
QBOX_BOOT_TIMEOUT=180 \
  ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh \
  2>&1 | tee build/verification/qbox-iree-hal-registry-compat-smoke.log
```

Artifacts:

- `build/verification/apollo-iree-hal-registry-build.log`
- `build/verification/apollo-iree-run-module-direct.log`
- `build/verification/qbox-iree-hal-registry-compat-smoke.log`

Pass gates:

- `iree-run-module` discovers `apollo-hexagon` directly without the repo-local
  runner or manual `dlopen()` shim.
- Existing executable plugin export/load remains as compatibility proof only.
- CPU fallback is disabled or explicitly rejected when proving Apollo execution.

Fail gates:

- HAL only works through the custom runner or `dlopen()` shim.
- `iree-run-module` succeeds by falling back to CPU/local-task execution.

Negative tests:

- Unknown device name fails cleanly.
- Missing HAL plugin reports actionable error.
- Device opens but rejects incompatible executable format.
- CPU fallback is not counted as Apollo execution.

Minimum commands for each implementation milestone:

```bash
bash -n scripts/*.sh
python3 -m py_compile scripts/check_iree_cnn_pipeline_readiness.py scripts/qbox_pty_runner.py
./scripts/check_buildroot_arm64_lane.sh
./scripts/check_iree_cnn_pipeline_readiness.py --json build/verification/iree-cnn-readiness-smmu-compliance.json
git diff --check
```

Boot-level milestones should additionally run:

```bash
./scripts/build_qbox_linux_arm64.sh
./scripts/build_qbox_buildroot_platform.sh
./scripts/stage_buildroot_artifacts.sh
./scripts/build_apollo_hexagon_guest_tools.sh
QBOX_BOOT_TIMEOUT=180 ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh
```

## Risks and blockers

1. Reference is not a perfect hardware oracle. It is valuable as a behavioral
   oracle, but it intentionally omits hardware MMIO/bus details and currently
   has one C++ failing test in local verification.
2. License compatibility must be resolved before copying any `sources/smmu`
   implementation into BSD-licensed QBox code.
3. QEMU and Apollo TBU currently own separate SMMU stories. Full compliance
   requires choosing a canonical translation state owner or building a robust
   bridge.
4. Stricter SMMUv3 behavior can break current smoke tests that depend on the
   custom Apollo TBU register ABI. Keep compatibility registers until new
   architected tests fully replace them.
5. Interrupt correctness can expose scheduling/order issues because the current
   DMA and TBU paths are mostly synchronous TLM plus polling registers.
6. Upstream IREE HAL registry work should refresh against the current IREE
   tree before implementation; the local repo only proves dynamic plugin and
   executable plugin export/load, not upstream HAL driver registration.

## Recommended next action

Start with `SMMU-COMP-000` and `SMMU-COMP-010` in one small patch series:

1. Add the compliance checklist document and optional checker.
2. Split the TBU internals so future architected register/queue work has a
   single home.
3. Re-run the current guest smoke unchanged. If existing markers regress, stop
   and fix compatibility before expanding protocol coverage.

## 2026-05-11 SMMU-COMP-010 architected core ownership progress note

SMMU-COMP-010 now has a small architected core ownership object in
`sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_arch_core.h`.
The object records the current canonical owner as `apollo_smmu_tbu/SystemC`,
keeps the compatibility adapter explicitly required, and leaves the QEMU
translation bridge disabled until a verified bridge exists. The existing
`apollo_smmu_tbu` owns this object via `m_arch_core`; component coverage
`ArchitectedCoreOwnsCanonicalTranslationState` verifies the contract without
changing the guest-visible feature mask.

The follow-up core-routing slice extends this object with explicit ownership
metadata for the architected register/queue state, stream/context descriptor
state, page-table walker state, and fault replay state. The TBU now also asks
`m_arch_core.classify_register()` whether an access targets the compatibility
adapter or the SMMUv3 register aperture, so future behavior migration can move
behind the core boundary without changing the existing MMIO ABI. Queue geometry
helpers (`queue_entries`, `queue_base_addr`, and `queue_index`) now live on the
core object and the TBU calls those helpers, which is the first small migration
of register-queue behavior behind the core boundary.

The next register-queue storage slice moves the actual CMDQ/EVENTQ/PRIQ
producer/consumer/base/overflow storage into `apollo_smmu_arch_core::queue_state`.
`apollo_smmu_tbu` now keeps reference aliases (`m_cmdq`, `m_eventq`, `m_priq`)
to the core-owned state, preserving the existing compatibility ABI and test
surface while making the core the canonical storage owner for architected
queues.

The stream/context state follow-up moves the current STRTAB base/configuration,
compatibility STE base, current CD table base, selected StreamID, and selected
SSID storage into `apollo_smmu_arch_core::stream_context_descriptor_state`.
`apollo_smmu_tbu` keeps reference aliases for the existing field names, so the
guest-facing compatibility registers and Linux probe behavior remain stable
while the architected core becomes the canonical owner for stream/context
selector state.

The walker-state follow-up moves the current TTBR/IOVA/S2TTB, last descriptor,
last PA/IPA/fetch address, walk depth, and last-stage fields into
`apollo_smmu_arch_core::page_table_walker_state`. As with the stream/context
slice, `apollo_smmu_tbu` keeps reference aliases for the existing field names
so the compatibility ABI and component/Linux probes remain unchanged while the
core becomes the canonical owner for walker state.

The fault/replay-state follow-up moves the scalar fault, ATS/PRI response,
stall/replay, endpoint replay, early-retry, STAG, PRG, and replay sequence
state into `apollo_smmu_arch_core::fault_replay_state`. The existing record
tables, buffered event queue, SystemC event, and replay algorithms remain in the
TBU adapter for now, but the protocol-visible counters and tags are now
core-owned reference aliases rather than duplicate adapter storage.

The walker-helper follow-up moves page/granule geometry, walk-depth,
level-index, output-mask, and leaf-offset calculations into the core object as
`walker_*` helpers. The TBU still performs downstream descriptor fetches and
fault handling, but the arithmetic used by the SMMUv3 architectural page-table
walker now crosses the same core boundary as the canonical walker state.

The descriptor-helper follow-up moves the pure Stream-table, STE, CD, and
effective-EATS decode helpers into `apollo_smmu_arch_core`. The TBU continues to
own downstream memory fetches, logging, and compatibility status registers, but
the side-effect-free descriptor arithmetic and field extraction now lives behind
the canonical core API.

The fault-record-helper follow-up moves the pure EVENTQ fault-record layout,
fault-detail/event-number mapping, and replay/status packing helpers into
`apollo_smmu_arch_core`. The TBU still owns memory-backed queue writes, log
emission, buffered stall-event storage, the SystemC resume event, and endpoint
redrive side effects; the side-effect-free reporting algorithms now cross the
same canonical core API as the fault/replay scalar state.

The stall-record follow-up moves STAG stall-record table storage plus STAG and
fault lookup helpers into `apollo_smmu_arch_core`. The TBU still owns logging,
buffered EVENTQ redrive, endpoint replay payload records, and downstream
redrive side effects; stalled fault table state now has the same canonical
owner as the scalar stall counters and STAG allocator state.

The endpoint-replay-record follow-up moves the mutable endpoint replay payload
record table, pending/any lookup helpers, and reset helper into
`apollo_smmu_arch_core`. The TBU still owns SystemC wait/notify, log emission,
and downstream `b_transport()` redrive side effects, but the stored replay
payload, STAG association, replay status, and retry bookkeeping record now
share the same canonical core owner as the STAG table and scalar replay
counters.

The endpoint-replay-transition follow-up moves replay-record allocation,
duplicate detection, capacity failure accounting, and CMD_RESUME retirement
counter transitions into `apollo_smmu_arch_core`. The TBU adapter now keeps the
side-effect boundary focused on logging, SystemC wait/notify, translation
retry, and downstream payload re-drive, while the core owns replay pending,
retried, succeeded, failed, terminated, and redriven accounting updates.

The endpoint-replay-redrive-state follow-up moves the replay payload/status
side of the downstream redrive path into `apollo_smmu_arch_core`: redrive
begin validates payload capacity or sizes read buffers, segment preparation
captures the first replay PA and validates payload windows, segment completion
records TLM response status and replay length, and final/failure helpers own
the replay success/failure state transitions. The adapter still performs
translation retry, SystemC wait/notify, log emission, and the downstream
`b_transport()` I/O call.

The descriptor-walk-state follow-up moves the first behavioral page-table walk
algorithm pieces into `apollo_smmu_arch_core`: walk-begin granule/level/address
validation, descriptor-fetch address planning, table/block/page step
classification, AF/permission fault transitions, and final leaf PA calculation.
The TBU adapter still performs downstream descriptor memory fetches,
compatibility logging, ATS fills, and nested stage-2 orchestration. The
top-level request IOVA is explicitly preserved across nested descriptor-fetch
walks before emitting ATS/PRI/fault records, keeping EVENTQ InputAddr payloads
architectural while the core walker scratch state is reused by recursive walks.

The descriptor-fetch-lifecycle follow-up moves fetch lifecycle state transitions
for translation-table descriptor memory accesses into `apollo_smmu_arch_core`.
The core now records descriptor fetch addresses as walk state, captures the
successfully fetched descriptor before step evaluation, and owns the
`F_WALK_EABT` fault-state transition for descriptor-fetch aborts. The adapter
still performs the physical `read_downstream_u64()` TLM transaction, but the
architectural fetch bookkeeping and fault state no longer live in adapter-only
code.

The descriptor-memory-read-interface follow-up wraps the adapter-owned physical
descriptor memory transaction in a core-owned request/result object. The core
now records the original descriptor PA, the actual transaction PA after optional
nested stage-2 translation, the owning walk stage, the stage-2-translation flag,
and the success/failure state transitions for the read result. The adapter still
executes `read_downstream_u64()`, but descriptor memory I/O now crosses an
explicit core API boundary instead of open-coding fetch completion/fault state
in the adapter.

The endpoint-redrive-transaction-interface follow-up wraps each downstream
endpoint replay segment in a core-owned TLM transaction request/result object.
The core now validates segment validity, captures replay PA/length/payload/write
metadata for the adapter-executed `b_transport()`, resets replay status to the
in-flight state, and validates the returned transaction identity before
committing the segment status/result. The adapter still performs translation
retry, SystemC wait/notify, log emission, and the actual downstream
`b_transport()` call, but the I/O boundary now consumes an explicit core request
and reports completion through an explicit core result path.

The adapter-io-executor follow-up moves the remaining open-coded physical I/O
call sites out of the descriptor walker and endpoint replay redrive loops. The
TBU adapter now uses `execute_descriptor_memory_read()` for descriptor-table
fetches and `execute_endpoint_replay_transaction()` for endpoint replay
redrive I/O. Both helpers are still adapter-executed because they ultimately
call `read_downstream_u64()` or `downstream->b_transport()`, but they provide
small, named, grep-checked executor seams that consume core-owned request
objects and return explicit result status to the core-owned state machines.

The swappable-io-executor follow-up replaces those named helper bodies with a
small `arch_io_executor` interface and a default TLM-backed executor. Descriptor
memory reads and endpoint replay transactions now dispatch through
`m_arch_io_executor` before reaching the adapter's downstream TLM helpers, and
the component test injects a fake executor to prove the seam can be replaced
without touching the core-owned request/result state. The default executor still
performs the physical descriptor read and endpoint replay `b_transport()` in
SystemC, so this is an interface/ownership hardening step rather than a QEMU
bridge claim.

This is still a functional slice, not a complete behavioral core split. The
next SMMU-COMP-010 step is to connect a verified external memory/replay backend
or QEMU bridge through this interface before changing the canonical owner.

## 2026-05-10 implementation progress note

SMMU-COMP-020 has a first functional slice in `apollo_smmu_tbu`: the custom
compatibility register ABI remains at offsets `0x00..0x8c`, and a new
compatibility-preserving SMMUv3 architectural register/queue aperture starts at
`0x1000`.  The new aperture models reset-readable ID/status registers,
CR0/CR0ACK and IRQ_CTRL/IRQ_CTRLACK acknowledgement, STRTAB/CMDQ/EVENTQ/PRIQ
base/prod/cons registers, CMDQ fetch/consume for the command opcodes used by the
first compliance slice, EVENTQ/PRIQ record helpers, and queue overflow/GERROR
bits.  The slice now has component regression coverage in
`sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` for
register socket access, queue wrap/base decode, memory-backed CMDQ consume,
EVENTQ/PRIQ record writes, overflow, and GERROR acknowledgement.  The QBox
platform now maps a `0x2000` Apollo TBU register window so Linux can reach the
relative `0x1000` SMMUv3 aperture, and the Apollo Linux probe adds a
guest-visible CMDQ/EVENTQ/PRIQ selftest that verifies CMDQ consumption, PRIQ
push, EVENTQ push, CR0/IRQ acknowledgement, and status bits from the guest.
This is still classified as `functional-slice`, not full SMMUv3 compliance:
binary command/event/PRI formats, stall retention, PRG lifecycle, MSI/GIC
delivery, multi-master isolation, and the full negative replay suite remain
open.

## 2026-05-10 SMMU-COMP-070 progress note

SMMU-COMP-070 now has a signal-level functional slice in `apollo_smmu_tbu`: the
TBU exposes four `irq_out` signals for EVENTQ, PRIQ, CMDQ_SYNC, and GERROR and
updates them from architected status bits gated by `IRQ_CTRL`. Component test
`ArchitectedIrqOutputsFollowQueueStatus` verifies assertion/deassertion for
EVENTQ/PRIQ cons updates, CMD_SYNC consumption, and GERROR/GERRORN overflow
acknowledgement. This is still not full architectural IRQ/MSI compliance: Linux
GIC ownership, MSI doorbells, interrupt ordering/coalescing, and negative IRQ
replay tests remain open.

Verification follow-up: the signal-level IRQ slice also passes the full QBox
Buildroot platform rebuild in
`build/verification/qbox-platform-smmu-comp-070-irq-output-20260510.log` and the
IREE tiny-CNN guest smoke in
`build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-070-irq-output.driver.log`.
The smoke result is `PASS: QBox guest IREE Hexagon tiny-CNN output matched` and
retains `APOLLO_SMMU_TBU: architected IRQ update` runtime markers. The IRQ
signals remain intentionally unbound from the platform GIC in this slice because
the existing QEMU SMMUv3 wrapper owns the architected SMMUv3 SPIs; full IRQ/MSI
routing is a later compliance gate.

## 2026-05-10 SMMU-COMP-080 progress note

SMMU-COMP-080 now has a component-level functional slice. Apollo translated TLM
transactions can carry `gs::ApolloSmmuStreamIdExtension`; `apollo_hexagon_dma`
sets this extension on SMMU-translated requests, and `apollo_smmu_tbu` tags
dynamic mappings plus ATS cache entries by StreamID. Component test
`MultiStreamIdMapsAreIsolated` verifies same-IOVA mappings for SID `0x1` and
SID `0x2`, unknown SID denial, and per-SID invalidation that leaves the other
SID valid. This remains a `functional-slice`: QBox DTS still exposes only the
Hexagon StreamID `0x1`, and full multi-master/PASID/STRTable invalidation
coverage remains open.

## 2026-05-10 SMMU-COMP-030 progress note

SMMU-COMP-030 now has a broader stream/context descriptor functional slice in
`apollo_smmu_tbu`. The TBU keeps the legacy Apollo Linux probe ABI but also
accepts spec-bitfield S1 descriptors (`STE.Config=S1_TRANS`, `STE.S1ContextPtr`,
`CD.V`, and `CD.TTB0`) and can select the architectural probe StreamID through
`REG_ARCH_STREAM_ID`. Component tests cover bounded linear STRTAB lookup, bad
StreamID replay via `ARCH_FAULT_BAD_STREAM_ID`, and a two-level STRTAB L1/L2 STE
selection path. The full compliance blockers remain: PASID/SSID and S1DSS,
S1CDMax and two-level CD tables, stage-2/nested STE/CD fields, reserved-bit
validation, and command-driven STRTAB/CD invalidation.

## 2026-05-10 SMMU-COMP-060 progress note

SMMU-COMP-060 now has a broader component-level ATS/PRI protocol slice in
`apollo_smmu_tbu`. The TBU distinguishes ATS success, Unsupported Request, and
Completer Abort outcomes; allocates PRG-tagged pending PRI requests; writes
memory-backed PRIQ records that preserve the current guest compatibility record
type while carrying ATS status and PRG metadata; and consumes CMD_PRI_RESP for
accept/clear, reject, and unknown-PRG cases.

The new component tests are `ArchitectedAtsPriProtocolMatrixAndPriResp` and
`CmdPriRespUnknownPrgIsAccounted`. This is still not full ARM SMMUv3 ATS/PRI
compliance: ATSCHK/EATS/secure-stream gating, byte-exact PRIQ layout, stall/PRG
lifecycle, endpoint ATC invalidation ordering, and full IRQ/MSI/GIC delivery
remain open.

## 2026-05-10 SMMU-COMP-050 progress note

SMMU-COMP-050 now has a broader component-level fault replay slice in
`apollo_smmu_tbu`. EVENTQ records carry a compact syndrome detail word with
reason, fault class, stage, attributes, and replay sequence; negative replay
tracks stall-pending state; CMD_RESUME covers retry/terminate accounting; and
EVENTQ overflow preserves stall-pending accounting while raising GERROR. The
component tests `FaultReplayRecordsSyndromeAndResumeState` and
`FaultReplayOverflowKeepsStallPending` cover CD/page fault syndrome details,
resume retry/terminate, and overflow retention.

This remains a `functional-slice`, not full SMMUv3 event/stall replay: byte-exact
EVENTQ layout, PASID/substream, stage-2 IPA, access/permission/security fields,
and endpoint transaction re-drive are still open.

## 2026-05-10 SMMU-COMP-040 progress note

SMMU-COMP-040 now has a broader component-level walker slice in
`apollo_smmu_tbu`: the functional walker can stage selected 4K/16K/64K granule
vectors, honor start-level selection in component tests, terminate on
block/page descriptors, reject missing access-flag and write-to-read-only leaf
faults, and run selected stage-2-only plus nested S1+S2 translations. The
coverage is intentionally classified as a functional slice: full Arm descriptor
bitfield parity, PASID/S1CDMax, VTCR/TCR decode, DBM/attributes, reserved-bit
validation, and reference-vector parity remain open.

## 2026-05-10 SMMU-COMP-090 progress note

SMMU-COMP-090 now has a repo-local upstream-style HAL registry dispatch slice.
The staged guest `iree-run-module` wrapper forwards `--device=apollo-hexagon`
to a new `apollo-iree-run-module` frontend, which discovers the Apollo HAL via
`apollo_iree_hal_registry_lookup()` and rejects CPU fallback device names. The
legacy `apollo-iree-hexagon-runner` and `iree_hal_executable_plugin_query`
plugin remain staged for compatibility, but the default Hexagon guest smoke now
uses the `iree-run-module --device=apollo-hexagon` registry path.

Validation evidence is in
`doc/verification/qbox-smmuv3-comp-090-verification-2026-05-10.md` and includes
AArch64/host tool builds, negative registry tests, guest artifact staging,
Buildroot rootfs rebuild, platform build, and a QBox guest IREE Hexagon smoke
PASS at
`build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-090-hal-registry-fixed.driver.log`.

Full upstream IREE completion remains open: this workspace still has no IREE
source tree modified with a native HAL driver registry entry, build-system
integration, or upstream HAL tests.

## 2026-05-11 SMMU-COMP-090 dynamic C HAL plugin progress note

SMMU-COMP-090 now exercises a dynamically loaded C HAL plugin on the normal
QBox guest `iree-run-module --device=apollo-hexagon` path. The staged guest
command passes `--executable_plugin` for
`libapollo_iree_hexagon_hal_plugin.so`; `apollo_iree_hal_registry_lookup()`
uses `dlopen()`/`dlsym()` to resolve the Apollo plugin query export, validates
the queue operation ABI, and logs the registered plugin path, driver name, and
API version before dispatch.

Negative host checks fail closed for `--device=local-task` CPU fallback and for
a missing plugin path. The QBox guest tiny-CNN smoke reached the dynamic
registration marker, completed queue 0/1 async fence waits, and matched
`1x1x2x2xf32=[[[54 63][90 99]]]`; see
`doc/verification/qbox-smmuv3-iree-dynamic-registry-verification-2026-05-11.md`
and
`build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-iree-dynamic-registry.driver.log`.

This is still a repo-local functional slice. Full upstream IREE completion
remains open until an actual IREE source tree has a native Apollo HAL driver
registry entry, build-system integration, and upstream HAL tests.

## 2026-05-10 SMMU-COMP-020/080 command invalidation progress note

A command-driven invalidation functional slice is now implemented in
`apollo_smmu_tbu`. The CMDQ decoder no longer treats `CFGI_*`, `TLBI_NH_*`,
and `ATC_INV` as pure no-ops: it records command progress and invalidates the
modeled ATS cache by StreamID, IOVA page, or global scope. Component coverage
now verifies:

- `CFGI_STE` invalidates only the selected StreamID cache entries.
- `TLBI_NH_VA` invalidates the selected page across modeled StreamIDs.
- per-SID `ATC_INV` invalidates only the requested StreamID/page.
- global `ATC_INV` clears all modeled ATS entries.

This closes a concrete part of the earlier command-invalidation gap, but it is
still a functional slice. Byte-exact SMMUv3 command encodings, ASID/VMID/PASID
TLB tags, endpoint ATC completion ordering, command error states, and Linux
arm-smmu-v3-driven invalidation coverage remain open.

## 2026-05-10 SMMU-COMP-020/080 tagged invalidation progress note

Implemented a follow-up functional slice for modeled ASID/VMID/SSID-aware
invalidation in the Apollo SMMU TBU. The slice adds tag fields to modeled ATS
cache entries, decodes the Linux/Arm SMMUv3 CMDQ TLBI ASID/VMID fields, and
honors SSID-valid ATC_INV targeting for component-level cache invalidation. This
narrows the earlier TLBI/ATC gap, but it is still not full architectural
compliance: PASID/CD-table indexing, endpoint ATC completion ordering,
Linux-driver-generated TLBI/ATC command paths, byte-exact error states, and full
multi-master runtime coverage remain open.

Evidence is recorded in
`doc/verification/qbox-smmuv3-tagged-invalidation-verification-2026-05-10.md`.

## 2026-05-10 SMMU-COMP-030 CD-table SSID indexing progress note

Implemented a follow-up SMMU-COMP-030 functional slice for context descriptor
SSID indexing in `apollo_smmu_tbu`. The TBU now exposes
`FEATURE_ARCH_CD_TABLE_INDEX`, a compatibility-preserving `REG_ARCH_SSID`
selector for component vectors, and `REG_ARCH_CD_DETAIL` observability. The
stream/context walk decodes `STE.S1CDMax`, `STE.S1DSS`, `STE.S1FMT=linear`, and
the modeled `STE.S1FMT=64K_L2` path, then indexes the CD table by selected SSID
with out-of-range `ARCH_FAULT_CD_INVALID` replay behavior. Component coverage
now verifies selected SSID linear CD lookup, SSID0 no-substream fallback,
S1CDMax bounds faults, and 64K-L2 CD table selection.

This remains a functional slice rather than full architectural compliance:
S1DSS bypass/terminate is only modeled conservatively for explicit test paths,
full PASID plumbing from PCIe/ATS transactions is not present, S2/nested CD
formats still need full Arm parity, modeled reserved/illegal encoding checks are
covered by the follow-up note below, and Linux `arm-smmu-v3`-generated CD
invalidation coverage is still open.


## 2026-05-10 SMMU-COMP-030 S1DSS policy progress note

Implemented a follow-up SMMU-COMP-030 functional slice for no-substream
`STE.S1DSS` policy handling in `apollo_smmu_tbu`. Explicit CD-table STEs now
distinguish `S1DSS=SSID0`, `S1DSS=TERMINATE`, and `S1DSS=BYPASS` when no
SSID/PASID is selected: SSID0 preserves the legacy CD0 fallback, terminate
reports an S1 CD fault, and bypass records `m_arch_last_cd_bypass` plus an
identity S1-bypass translation for the component model.

The existing component test `ArchitectedContextDescriptorTableIndexesSelectedSsid`
now covers terminate and bypass in addition to SSID-selected linear CD lookup,
S1CDMax bounds faulting, and 64K-L2 CD table selection. This is still a
functional slice, not full SMMUv3 compliance: PASID plumbing from endpoint
transactions, byte-exact fault event encoding, full Arm reserved-matrix parity,
and Linux `arm-smmu-v3` generated CD invalidation coverage remain open. Nested S2
translation after S1DSS bypass is covered by the follow-up progress note below.

## 2026-05-10 SMMU-COMP-030/040 nested S1DSS-bypass S2 progress note

Implemented a follow-up functional slice for nested `STE.S1DSS=BYPASS` behavior
in `apollo_smmu_tbu`. The S1DSS bypass path still preserves the existing
S1-only identity-bypass behavior, but when `STE.Config=NESTED` it now treats the
bypassed S1 output as an IPA and invokes the stage-2 descriptor walker using the
STE S2 table pointer. Component coverage extends
`ArchitectedWalkerStage2AndNestedMatrix` with a `bypass_s2ttb` vector that
checks the final PA comes from the S2 table and that the previous S2 fault replay
vector still fails after restoring the normal nested path.

This narrows the earlier nested-bypass gap, but remains a functional slice rather
than full SMMUv3 compliance: endpoint PASID/SSID plumbing, byte-exact
event/fault records, Linux `arm-smmu-v3` command-driven CD invalidation, full
reference-vector parity, and broader Arm reserved-matrix parity remain open.
Modeled STE/CD reserved and illegal encoding checks are covered by the follow-up
progress note below.


## 2026-05-10 SMMU-COMP-030 reserved/illegal encoding progress note

Implemented a follow-up SMMU-COMP-030 functional slice for modeled STE/CD
reserved-bit and illegal-encoding validation in `apollo_smmu_tbu`. The TBU now
advertises `FEATURE_ARCH_RESERVED_ENCODING_CHECKS`, rejects unsupported
`STE.Config` encodings, rejects modeled reserved bits in STE word0/word1/word2,
rejects modeled reserved CD word0/word1 bits, rejects illegal `S1DSS=0x3`, and
rejects reserved bits in modeled 64K-L2 CD L1 descriptors before consuming the
descriptor state. The new component vector
`ArchitectedSteCdReservedEncodingFaults` verifies each negative case produces
`ARCH_FAULT_STE_INVALID` or `ARCH_FAULT_CD_INVALID` at S1 as appropriate.

This removes the previous local QBox blocker for the modeled STE/CD reserved and
illegal encoding slice, but it is still not full Arm SMMUv3 compliance:
endpoint-derived PASID/SSID plumbing, byte-exact event/fault record layouts,
Linux `arm-smmu-v3` generated CD invalidation, complete Arm reserved-field
parity across all STE/CD formats, and external reference-vector parity remain
open.

## 2026-05-10 SMMU-COMP-050 EVENTQ common-layout progress note

Implemented a follow-up SMMU-COMP-050 functional slice in `apollo_smmu_tbu` for
architected common EVENTQ record fields and modeled `CMD_STALL_TERM` handling.
The TBU now advertises `FEATURE_ARCH_EVENT_RECORD_LAYOUT`, maps modeled fault
reasons onto architected event numbers (`C_BAD_STREAMID`, `C_BAD_STE`,
`C_BAD_CD`, `F_TRANSLATION`, `F_ADDR_SIZE`, `F_ACCESS`, `F_PERMISSION`), writes
word0 with event number, SSV/SubstreamID, and StreamID, keeps InputAddr in word1,
and preserves the modeled syndrome/STAG detail in word3. Component coverage adds
`ArchitectedEventRecordLayoutCarriesSubstream` and
`CmdStallTermTerminatesPendingStalls`.

This narrows the byte-layout and stall-command gap, but remains a functional
slice rather than full SMMUv3 compliance: complete byte-exact layouts for all
event types, fetch-address fields, IPA/security/permission parity, true STAG
matching, endpoint transaction re-drive, Linux arm-smmu-v3 event consumption, and
PASID/SSID plumbing remain open.

## 2026-05-10 SMMU-COMP-030/080 endpoint PASID/SSID progress note

Implemented a follow-up functional slice for endpoint-derived SubstreamID/PASID
plumbing across the Apollo Hexagon DMA endpoint and Apollo SMMU TBU data path.
The common `ApolloSmmuStreamIdExtension` now carries optional `substream_id`
metadata, `apollo_hexagon_dma` advertises an endpoint PASID capability and
attaches the configured PASID/SSID to SMMU-translated TLM transactions, and the
Buildroot QBox platform configures a non-zero endpoint PASID/SSID on the Hexagon
DMA endpoint. The TBU consumes the endpoint SSID for ATS cache tags, page-walk
traceability, and EVENTQ SSV/SubstreamID fields; the component test
`EndpointSubstreamIdTagsAtsAndFaultEvents` covers the positive ATS tagging path
and endpoint-SSID event record path.

This narrows the previous endpoint PASID/SSID blocker but remains a functional
slice rather than full SMMUv3 compliance: PCIe PASID request semantics,
Linux-driver generated CD invalidation, full CD table parity for endpoint PASID
traffic, platform-visible multi-master topology, and true endpoint transaction
re-drive remain open.

## 2026-05-10 SMMU-COMP-020/030/080 Linux CMDQ invalidation progress note

Implemented a follow-up functional slice for Linux guest-driven CMDQ
invalidation through the QBox guest-visible SMMUv3 command queue model. The
Apollo Linux probe now requires the TBU architectural command-invalidation
feature, writes a four-entry `CMD_SYNC`/`CMD_PRI_RESP`/`ATC_INV`/`TLBI_NH_ALL`
sequence, advances `CMDQ_PROD`, verifies `CMDQ_CONS == 4`, and checks that the
modeled command-invalidation counter advanced. The guest smoke test now gates on
the Linux selftest marker plus TBU `ATC_INV` and `TLBI_NH_ALL` invalidation side
effect logs, so the boot regression proves Linux-originated commands exercised
the runtime model before the IREE Hexagon workload passes.

Verification completed in
`doc/verification/qbox-smmuv3-linux-cmd-invalidation-verification-2026-05-10.md`:
the standalone Linux Image rebuilt, artifacts were staged, the QBox platform
runtime rebuilt, the QBox guest IREE Hexagon tiny-CNN smoke passed, runtime logs
recorded `invalidations=3 ops=ATC_INV,TLBI_NH_ALL`, and the final
static/checker/lane pass reported `SUMMARY {"pass": 180}`.

This narrows the remaining command-invalidation gap but is still not full Arm
SMMUv3 compliance. Open blockers remain: generic upstream `arm-smmu-v3` CD
invalidation/PASID lifecycle coverage, PCIe PASID request semantics, endpoint
ATC completion ordering, full CD-table parity for endpoint PASID traffic,
platform-visible multi-master topology, stalled endpoint transaction
buffering/re-drive, byte-exact event/command/PRI layouts for every Arm SMMUv3
type, and true upstream IREE source integration.

## 2026-05-10 SMMU-COMP-080 platform multi-master progress note

Implemented a follow-up functional slice for platform-visible multi-master
coverage. QBox now instantiates an auxiliary Apollo DMA/TBU pair at
`0x1c300000` with StreamID `0x2`, exposes it in the Linux DTS as
`hexagon-aux@1c300000` behind the same SMMUv3 with `iommus = <&smmu 0x2>`, and
keeps the primary userspace ABI at `/dev/apollo-hexagon` while auxiliary
endpoints register as `/dev/apollo-hexagon-%x`. The guest smoke now gates on the
auxiliary probe marker, so runtime validation proves Linux sees and probes both
StreamID `0x1` and `0x2` endpoints while the primary IREE Hexagon path still
passes.

Verification completed in
`doc/verification/qbox-smmuv3-multi-master-topology-verification-2026-05-10.md`:
Linux, Buildroot DTB/rootfs, QBox platform runtime, artifact staging, guest
smoke, and static/checker/lane all passed; runtime logs record
`platform 1c300000.hexagon-aux: Adding to iommu group 1`,
`dma path smmu-translated ... stream-id=0x2`,
`SMMUv3 stream/context descriptor probe ok stream-id=0x2`, and
`/dev/apollo-hexagon-2`.

This narrows the previous platform/DTS multi-master blocker, but remains a
functional slice rather than full SMMUv3 topology compliance: full PCIe
RID/PASID requester semantics, endpoint ATC completion ordering across real
multi-master traffic, shared CD invalidation lifecycle driven by upstream
`arm-smmu-v3`, byte-exact event/command/PRI layouts, and endpoint transaction
re-drive remain open.


## 2026-05-10 SMMU-COMP-020/050/060/070 CR0 queue-gate progress note

Implemented a follow-up functional slice for spec-position CR0 queue enable
gates. The Apollo SMMUv3 TBU now advertises
`FEATURE_ARCH_CR0_QUEUE_GATES`, defines CR0 `SMMUEN`, `PRIQEN`,
`EVENTQEN`, `CMDQEN`, and `ATSCHK` bits at their architectural positions,
gates CMDQ consumption on `SMMUEN|CMDQEN`, gates normal EVENTQ records on
`SMMUEN|EVENTQEN`, and gates PRIQ records on `SMMUEN|PRIQEN`. Stall event
records intentionally remain allowed so software can read the STAG and issue
`CMD_RESUME`/`CMD_STALL_TERM`. The Apollo Linux probe now requires the
feature and writes `APOLLO_SMMUV3_CR0_ENABLE_QUEUES` before using
memory-backed queues.

Verification completed in
`doc/verification/qbox-smmuv3-cr0-queue-gates-verification-2026-05-10.md`:
Apollo TBU component build and CTest passed, Linux Image rebuilt, QBox
platform runtime rebuilt, artifacts were staged, guest smoke passed with
`features=0x7ffff`, and the final checker/lane pass reported
`SUMMARY {"pass": 196}`.

This narrows the command/event/PRI and queue-control gaps, but remains a
functional slice rather than full SMMUv3 compliance: EATS/ATSCHK behavior,
byte-exact record layouts, MSI delivery/order, endpoint ATC completion
ordering, transaction re-drive, upstream `arm-smmu-v3` lifecycle, full PCIe
RID/PASID requester semantics, and true upstream IREE integration remain open.

## 2026-05-10 SMMU-COMP-060 ATSCHK/EATS progress note

Implemented a follow-up functional slice for CR0.ATSCHK plus STE.EATS
gating of ATS Translation Requests. The Apollo SMMUv3 TBU now advertises
`FEATURE_ARCH_ATSCHK_EATS_GATES`, exposes
`ARCH_CTRL_ATS_TRANSLATION_REQUEST`, decodes STE.EATS bits, treats
split/DPT EATS encodings as disabled when CR0.ATSCHK is clear, emits UR
plus `F_BAD_ATS_TREQ` for disabled effective EATS, and accepts Full ATS
when CR0.ATSCHK is enabled and the stream/context/table walk succeeds.
The Apollo Linux probe stages EATS Full in the boot descriptor path,
validates split-without-ATSCHK and EATS-disabled rejection, and records
`SMMUv3 ATSCHK/EATS translation request selftest ok` on success.

Verification completed in
`doc/verification/qbox-smmuv3-atschk-eats-verification-2026-05-10.md`:
Apollo TBU component build and CTest passed, checker preflight reported
`SUMMARY {"pass": 202}`, Linux Image rebuilt, QBox platform runtime
rebuilt, artifacts were staged, guest smoke passed with `features=0xfffff`,
and the final static/checker/lane pass reported `SUMMARY {"pass": 202}`.

This narrows the ATS/PRI protocol gap, but remains a functional slice
rather than full SMMUv3 compliance: full packet-level ATS/PRI, secure
stream ATS routing, `SMMU_CR2.REC_CFG_ATS` policy, EATS split-stage IPA
return semantics, DPT checks, endpoint ATC completion ordering,
translated-transaction re-drive, MSI delivery/order, upstream
`arm-smmu-v3` lifecycle, and true upstream IREE integration remain open.

## 2026-05-10 SMMU-COMP-060 REC_CFG_ATS progress note

Implemented a follow-up functional slice for CR2.REC_CFG_ATS and
CR2.RECINVSID event-recording gates on ATS Translation Requests. The
Apollo SMMUv3 TBU now advertises `FEATURE_ARCH_REC_CFG_ATS_GATES`,
reports IDR0.ATSRECERR, masks modeled CR2 writes to E2H/RECINVSID/PTM/
REC_CFG_ATS, suppresses SMMUEN-disabled ATS Translation Request fault
recording until CR2.REC_CFG_ATS is set, and suppresses ATS bad-StreamID
recording unless CR2.REC_CFG_ATS and CR2.RECINVSID are both set. The
Apollo Linux probe validates REC_CFG_ATS-disabled suppression and
REC_CFG_ATS-enabled recording at boot with
`SMMUv3 REC_CFG_ATS translation request selftest ok`.

Verification completed in
`doc/verification/qbox-smmuv3-rec-cfg-ats-verification-2026-05-10.md`:
checker preflight reported `SUMMARY {"pass": 207}`, Apollo TBU component
build and CTest passed, Linux Image rebuilt, artifacts were staged, QBox
platform runtime rebuilt, guest smoke passed with `features=0x1fffff`,
and the final static/checker/lane pass reported `SUMMARY {"pass": 207}`.

This narrows the ATS event-recording policy gap, but remains a functional
slice rather than full SMMUv3 compliance: full packet-level ATS/PRI,
secure stream ATS routing, EATS split-stage IPA return semantics, DPT
checks, endpoint ATC completion ordering, translated-transaction re-drive,
MSI delivery/order, upstream `arm-smmu-v3` lifecycle, and true upstream
IREE integration remain open.

## 2026-05-10 SMMU-COMP-020 DPTI unsupported-command progress note

Implemented a follow-up SMMU-COMP-020 functional slice for DPT maintenance
command handling when dirty page tracking is not advertised. The Apollo TBU
still reports `ARCH_IDR3 = 0`, but now advertises
`FEATURE_ARCH_DPTI_UNSUPPORTED`, decodes `CMD_DPTI_ALL`/`CMD_DPTI_PA`, and
routes them through the existing guest-visible GERROR command-abort path instead
of silently treating them as generic unsupported commands/no-ops. The Apollo
Linux probe validates `IDR3==0`, drives `CMD_DPTI_ALL`, observes GERROR,
acknowledges it through GERRORN, and emits
`SMMUv3 DPTI unsupported command selftest ok`.

Verification completed in
`doc/verification/qbox-smmuv3-dpti-unsupported-verification-2026-05-10.md`:
Apollo TBU component build and CTest passed, Linux Image rebuilt, artifacts were
staged, QBox platform runtime rebuilt, guest smoke passed with
`features=0x3fffff`, and final static/checker/lane pass reported the updated
checker summary.

This narrows the DPT maintenance-command blocker, but remains a functional slice
rather than full SMMUv3/DPT compliance: DPT walk tables, DPT_CFG_FAR and DPT_ERR
ordering, DPT VMID matching, DPT TLB, DPTI completion semantics, Secure/Realm
DPT separation, byte-exact CMDQ_CONS.CERROR encoding, and broader
full-compliance blockers remain open.

## 2026-05-10 SMMU-COMP-020 CMDQ CERROR progress note

Implemented a follow-up SMMU-COMP-020 functional slice for architected CMDQ_CONS.ERR reporting. The Apollo TBU now advertises `FEATURE_ARCH_CMDQ_CERROR`, exposes CMDQ_CONS.RD and CMDQ_CONS.ERR at their architected positions, reports `CERROR_ILL` for IDR3.DPT=0 `CMD_DPTI_ALL`/`CMD_DPTI_PA`, leaves RD pointing at the failing command, asserts the existing GERROR command-queue line, and lets software rewrite CMDQ_CONS to clear and skip the failed command. The Apollo Linux probe decodes raw CMDQ_CONS, validates RD=4 plus `cerror=1` for `CMD_DPTI_ALL`, then acknowledges GERROR and writes CMDQ_CONS=5 before continuing.

Verification completed in `doc/verification/qbox-smmuv3-cmdq-cerror-verification-2026-05-10.md`: Apollo TBU component build and CTest passed, Linux Image rebuilt, artifacts were staged, QBox platform runtime rebuilt, guest smoke passed with `features=0x7fffff`, and final static/checker/lane pass reported the updated checker summary.

This narrows command queue error reporting for DPTI, but remains a functional slice rather than full SMMUv3 CMDQ/DPT compliance: the complete illegal-command matrix, CERROR_ABT/CERROR_ATC_INV_SYNC ordering, CMDQ pause/retry and software recovery corner cases, DPT walk tables, DPT_CFG_FAR/DPT_ERR ordering, DPT VMID/TLB/completion semantics, Secure/Realm DPT separation, and broader full-compliance blockers remain open.

## 2026-05-10 SMMU-COMP-020 CMDQ CERROR_ABT progress note

Implemented a follow-up SMMU-COMP-020 component verification slice for architected `CMDQ_CONS.CERROR_ABT`. The Apollo TBU already reports `CERROR_ABT` for enabled-but-unconfigured or unfetchable command queues; the new `CmdqUnconfiguredQueueSetsCerrorAbt` test now fixes that behavior in CI by driving `CMDQ_PROD` before a valid CMDQ base is configured, checking `CMDQ_CONS.RD=0`, `CMDQ_CONS.ERR=CERROR_ABT`, `GERROR.CMDQ_ABORT`, and the GERROR IRQ line, then acknowledging GERROR and rewriting `CMDQ_CONS=1` to clear/skip the failed position.

Verification is recorded in `doc/verification/qbox-smmuv3-cmdq-cerror-abt-verification-2026-05-10.md`: Apollo TBU component build and CTest passed, and the final static/checker/lane pass includes the new `tbu:cmdq-cerror-abt` invariant.

This narrows command queue abort reporting but remains a functional slice rather than full SMMUv3 CMDQ compliance: queue-memory abort ordering, all memory abort cases, CERROR_ATC_INV_SYNC, CMDQ retry/pause behavior, GERRORN/CMDQ_CONS corner cases, MSI delivery, and upstream `arm-smmu-v3` queue lifecycle parity remain open.

## 2026-05-10 SMMU-COMP-020 CMDQ CERROR_ATC_INV_SYNC progress note

Implemented a follow-up SMMU-COMP-020 component verification slice for
architected `CMDQ_CONS.CERROR_ATC_INV_SYNC`. The Apollo TBU now has a modeled
ATC invalidation completion-failure state: a test hook marks the next
`CMD_ATC_INV` as failed, and the following `CMD_SYNC` reports
`CERROR_ATC_INV_SYNC`, leaves `CMDQ_CONS.RD` at the sync command, raises
`GERROR.CMDQ_ABORT`, suppresses the normal CMDQ_SYNC IRQ, and lets software
acknowledge GERROR plus rewrite `CMDQ_CONS` to clear/skip the failed sync.

Verification is recorded in
`doc/verification/qbox-smmuv3-cmdq-cerror-atc-inv-sync-verification-2026-05-10.md`:
Apollo TBU component build and CTest passed, and the final
static/checker/lane pass includes the new `tbu:cmdq-cerror-atc-inv-sync`
invariant.

This narrows command queue ATC invalidation sync error reporting but remains a
functional slice rather than full SMMUv3 endpoint ATC protocol compliance: real
ATS Invalidate Request packets, timeout/UR response semantics, endpoint ATC
completion ordering, broader timeout/retry ordering, MSI delivery, and
upstream `arm-smmu-v3` queue lifecycle parity remain open.

## 2026-05-10 SMMU-COMP-020 CMDQ CERROR_ATC_INV_SYNC multi-outstanding progress note

Implemented a follow-up SMMU-COMP-020 component verification slice for
multi-outstanding `CMDQ_CONS.CERROR_ATC_INV_SYNC` handling. Apollo TBU now tracks
multiple modeled failed `CMD_ATC_INV` completions before `CMD_SYNC` through a
pending failure count. The next `CMD_SYNC` coalesces those pending failures into
one architected `CERROR_ATC_INV_SYNC`, leaves `CMDQ_CONS.RD` at the failing sync,
raises `GERROR.CMDQ_ABORT`, and pauses later command processing until software
acknowledges GERROR and rewrites `CMDQ_CONS` to skip the failing sync. A
component test then proves a later `CMD_SYNC` runs normally after recovery.

Verification is recorded in
`doc/verification/qbox-smmuv3-cmdq-cerror-atc-inv-sync-multi-verification-2026-05-10.md`:
Apollo TBU component build and CTest passed, and the final
static/checker/lane pass includes the new
`tbu:cmdq-cerror-atc-inv-sync-multi` invariant.

This narrows CMDQ CERROR_ATC_INV_SYNC ordering and software-recovery coverage
but remains a functional slice rather than full endpoint ATS/PCIe protocol
compliance: real ATS Invalidate Request packets, timeout/UR semantics,
endpoint completion ordering, MSI delivery, and upstream `arm-smmu-v3` queue
lifecycle parity remain open.

## 2026-05-10 SMMU-COMP-070 IRQ_CTRL mask progress note

Implemented a SMMU-COMP-070 component verification slice for IRQ_CTRL reserved
bit handling. The Apollo TBU now masks `SMMUV3_IRQ_CTRL` writes with
`ARCH_IRQ_CTRL_WRITABLE_MASK` and mirrors the masked value in
`SMMUV3_IRQ_CTRLACK`; the new `IrqCtrlReservedBitsAreMaskedInCtrlAck` component
test writes all ones and verifies only the modeled EVENTQ/PRIQ/CMDQ_SYNC/GERROR
signal-level bits remain visible.

Verification is recorded in
`doc/verification/qbox-smmuv3-irq-ctrl-mask-verification-2026-05-10.md`: Apollo
TBU component build and CTest passed, and the final static/checker/lane pass
includes the new `tbu:irq-ctrl-reserved-mask` invariant.

This narrows IRQ register semantics but remains a functional slice rather than
full SMMUv3 IRQ/MSI compliance: PCIe MSI writes, abort reporting, GIC/MSI
routing, interrupt ordering, architected MSI configuration registers, and
upstream `arm-smmu-v3` interrupt lifecycle parity remain open.

## 2026-05-10 SMMU-COMP-070 GERROR/GERRORN toggle progress note

Implemented a SMMU-COMP-070 component verification slice for global-error
acknowledgement. Apollo TBU now keeps raw `GERROR`/`GERRORN` state and computes
active errors as `GERROR ^ GERRORN`; `set_arch_gerror()` toggles raw `GERROR`
only when the requested error is inactive, and `ack_arch_gerror()` toggles
`GERRORN` only for currently-active bits. The externally-read `SMMUV3_GERROR`
value remains active-bit oriented for the existing QBox guest ABI, preserving
Linux probe behavior while adding internal retoggle semantics.

Verification is recorded in
`doc/verification/qbox-smmuv3-gerrorn-toggle-verification-2026-05-10.md`:
Apollo TBU component build and CTest passed, and the final static/checker/lane
pass includes the new `tbu:gerrorn-active-toggle` invariant.

This narrows global-error acknowledgement behavior but remains a functional
slice rather than full SMMUv3 IRQ/MSI compliance: PCIe MSI writes, MSI abort
reporting, GIC/MSI routing, interrupt ordering, and upstream `arm-smmu-v3`
lifecycle parity remain open.

## 2026-05-10 SMMU-COMP-070 raw GERROR toggle progress note

Implemented a SMMU-COMP-070 follow-up slice for architectural raw `GERROR`
register exposure. Apollo TBU now returns raw `GERROR` toggle state from the
architected register while preserving `read_arch_gerror()` as the active-error
predicate (`GERROR ^ GERRORN`) used by `set_arch_gerror()` and
`ack_arch_gerror()`. Component tests and the Apollo Linux probe now compute
active global errors from the raw `GERROR/GERRORN` pair, and the guest DPTI
unsupported-command selftest records raw `gerror`, raw `gerrorn`, and active-XOR
values.

Verification is recorded in
`doc/verification/qbox-smmuv3-gerror-raw-toggle-verification-2026-05-10.md`:
Apollo TBU component build/CTest passed, Linux Image rebuilt, Buildroot artifacts
were staged, QBox platform runtime rebuilt, guest Hexagon tiny-CNN smoke passed
with the raw GERROR active-XOR marker, and the final static/checker/lane pass
includes the strengthened `tbu:gerrorn-active-toggle` and new
`linux:gerror-active-xor` invariants.

This narrows the global-error register model toward the architecture but remains
a functional slice rather than full SMMUv3 IRQ/MSI compliance: PCIe MSI writes,
MSI abort reporting, GIC/MSI routing, interrupt ordering, and upstream
`arm-smmu-v3` lifecycle parity remain open.

## 2026-05-10 SMMU-COMP-020/050/060 output queue OVFLG progress note

Implemented a follow-up functional slice for architected EVENTQ/PRIQ overflow
flags in the Apollo TBU SMMUv3 aperture. The model now carries per-output-queue
`OVFLG` and `OVACKFLG` state, exposes `OVFLG` through `SMMU_EVENTQ_PROD` and
`SMMU_PRIQ_PROD`, accepts `OVACKFLG` acknowledgement through the corresponding
consumer registers, and coalesces repeated overflows while an overflow remains
unacknowledged. `EventAndPriQueueOverflowFlagsToggleAndAck` fixes this behavior
in the component test suite, and the compliance checker/lane gates require the
feature marker and test.

This narrows queue overflow compliance, but it remains a functional slice rather
than full SMMUv3 queue/protocol compliance: byte-exact EVENTQ/PRIQ records for
all architected events, stall buffering/re-drive when EVENTQ is full,
packet-level PCIe PRI/PASID response behavior, MSI/GIC delivery and abort
reporting, and upstream Linux `arm-smmu-v3` recovery parity remain open.

## 2026-05-10 SMMU-COMP-020/050/060/070 queue abort GERROR progress note

Implemented a follow-up output-queue abort functional slice. The Apollo TBU now
uses architected `SMMU_GERROR.EVENTQ_ABT_ERR` and `SMMU_GERROR.PRIQ_ABT_ERR`
bits when downstream writes of EVENTQ/PRIQ records abort, keeps the producer
index unchanged on the failed write, raises the GERROR IRQ status, and accepts
normal active-bit acknowledgement through `SMMU_GERRORN`. The Linux probe's
known GERROR mask was extended with the same architected bits so active-error
XOR decoding remains aligned with the modeled register surface.

Verification is recorded in
`doc/verification/qbox-smmuv3-queue-abort-gerror-verification-2026-05-10.md`.
Apollo TBU component build and CTest passed; static/checker/lane verification
is run as the final gate for this slice. This remains a functional slice: MSI
abort bits, GIC/MSI ordering, full Linux `arm-smmu-v3` queue-abort recovery,
stall re-drive, and packet-level PRI completion remain open.

## 2026-05-10 SMMU-COMP-050 EVENTQ stall buffer/redrive progress note

Implemented a follow-up functional slice for Event queue full behavior on
stalled faults. The Apollo SMMUv3 TBU now advertises
`FEATURE_ARCH_STALL_BUFFER_REDRIVE`, buffers stalled EVENTQ records when the
configured Event queue is full, avoids setting `OVFLG`/GERROR for that stall
record, and redrives the buffered record into the memory-backed Event queue when
software advances `SMMU_EVENTQ_CONS`. Non-stall events continue to use the
existing OVFLG/OVACKFLG overflow path.

Verification is recorded in
`doc/verification/qbox-smmuv3-eventq-stall-buffer-redrive-verification-2026-05-10.md`:
Apollo TBU component build and CTest passed, including
`FaultReplayFullEventQueueBuffersAndRedrivesStall`.

This narrows the Event queue replay gap, but remains a functional slice rather
than full Arm SMMUv3 compliance. Remaining blockers include byte-exact STAG
allocation, endpoint transaction hold/reissue on the TLM data path, full stall
suppression/merge and early-retry semantics, and ordering against `CMD_SYNC`,
MSI/GIC delivery, and upstream `arm-smmu-v3` event-thread recovery.

## 2026-05-10 SMMU-COMP-060 PRI auto-response progress note

Implemented a follow-up functional slice for PRI automatic response handling in
QBox Apollo SMMUv3 TBU. The model now advertises
`FEATURE_ARCH_PRI_AUTO_RESPONSE`, records automatic PRI failure responses through
`record_pri_auto_response()`, clears the matching pending PRG, and covers PRIQ
full/overflow, CR0.PRIQEN-disabled, and active `PRIQ_ABT_ERR` cases in
`PriProtocolAutoRespondsOnOverflowDisabledAndAbort`.

Ground-truth scope is the local SMMUv3 reference under `sources/smmu`, especially
its PRI queue overflow notes: PRIQ full toggles `SMMU_PRIQ_PROD.OVFLG`; Last==1
PPRs are automatically responded to; PRIQ disabled or active `PRIQ_ABT_ERR`
returns automatic failure. QBox still models this as a compact functional slice,
not a byte-exact PCIe PRI packet engine: PASID-prefix response selection,
Stop-PASID markers, multi-entry PRG interleaving, and endpoint-visible PRG
response packets remain open.

Verification report:
`doc/verification/qbox-smmuv3-pri-auto-response-verification-2026-05-10.md`.

## 2026-05-10 SMMU-COMP-070 MSI IRQ_CFG progress note

Implemented a follow-up SMMU-COMP-070 functional slice for architected MSI
configuration and abort reporting. The Apollo TBU now exposes non-secure
`SMMU_GERROR_IRQ_CFG{0,1,2}`, `SMMU_EVENTQ_IRQ_CFG{0,1,2}`, and
`SMMU_PRIQ_IRQ_CFG{0,1,2}` registers, advertises `SMMU_IDR0.MSI`, records MSI
writes through the downstream TLM path, and reports failed MSI writes through
`MSI_CMDQ_ABT_ERR`, `MSI_EVENTQ_ABT_ERR`, `MSI_PRIQ_ABT_ERR`, and
`MSI_GERROR_ABT_ERR` GERROR bits. Component coverage adds MSI IRQ_CFG guard and
mask checks, EVENTQ/PRIQ MSI write and abort checks, and CMD_SYNC SIG_IRQ MSI
write/abort checks.

The Linux Apollo probe was updated to treat the TBU-local SMMUv3 aperture as
MSI-capable (`IDR0=0x0181a705`) and to read the private status register at
`0x0e0`, leaving the architected `0x0d0..0x0dc` window for `PRI_IRQ_CFG`.

This remains a functional slice rather than full SMMUv3 IRQ/MSI compliance:
real PCIe/GIC MSI delivery, Secure/Realm MSI banks, ordering/coalescing parity,
and upstream Linux `arm-smmu-v3` interrupt lifecycle parity remain open.

## 2026-05-10 SMMU-COMP-050 STAG/RESUME progress note

Implemented a follow-up functional slice for architected stalled-event tags and
resume matching. The Apollo SMMUv3 TBU now allocates nonzero STAG values for
modeled stalled faults, stores pending stall records in a StreamID+STAG table,
emits stalled EVENTQ records with `EVTQ_1.STAG` and `EVTQ_1.STALL` in word 1,
and writes the faulting IOVA in word 2 for stalled records. `CMD_RESUME` now
uses the architected command layout: StreamID and response in word 0 plus STAG
in word 1. Unknown StreamID/STAG pairs are accounted without clearing pending
state, while matching retry/terminate/abort responses update the replay
counters. `CMD_STALL_TERM` sweeps only pending records for the requested
StreamID, and disabling `SMMU_CR0.SMMUEN` clears the modeled stall table.

Ground truth came from the local Linux `arm-smmu-v3.h` field definitions for
`CMDQ_RESUME_0_RESP`, `CMDQ_RESUME_0_SID`, `CMDQ_RESUME_1_STAG`, `EVTQ_1_STAG`,
`EVTQ_1_STALL`, and `EVTQ_2_ADDR`, plus `sources/smmu/SPEC_REVIEW.md` H-05,
NEW-26, and NEW-30.

Verification is recorded in
`doc/verification/qbox-smmuv3-stag-resume-verification-2026-05-10.md`. The
component suite now covers nonzero STAG emission, StreamID+STAG resume matching,
unknown resume rejection, and stream-wide STALL_TERM behavior.

This remains a functional slice rather than full Arm SMMUv3 compliance.
Remaining blockers include endpoint transaction hold/reissue on the TLM data
path, byte-exact parity for the full EVENTQ field matrix, full stall
suppression/merge and early-retry semantics, precise PCIe PASID/PRI stall
behavior, and ordering against `CMD_SYNC`, MSI/GIC delivery, and upstream
`arm-smmu-v3` event-thread recovery.

## 2026-05-10 SMMU-COMP-050 negative replay matrix progress note

Implemented a follow-up functional slice for the negative fault replay suite.
The Apollo SMMUv3 TBU now has a write-negative replay control path so the same
stalled replay mechanism can record write permission failures with the
architected write attribute. The component suite adds
`NegativeFaultReplayMatrixRecordsArchitectedEvents`, which exercises bad
StreamID, bad STE, bad CD, access-flag, and write-permission faults through the
stalled EVENTQ path and checks the architected event number, StreamID, STAG,
STALL bit, IOVA word, syndrome detail class/stage, and write attribute where
applicable.

Verification is recorded in
`doc/verification/qbox-smmuv3-negative-replay-suite-verification-2026-05-10.md`.
This narrows the negative replay coverage gap, but does not claim full event
matrix parity: the complete Arm SMMUv3 event catalog, suppression/merge rules,
endpoint transaction hold/reissue, and upstream `arm-smmu-v3` event-thread
recovery remain open.

## 2026-05-10 SMMU-COMP-050 endpoint replay accounting progress note

Implemented a follow-up functional slice for endpoint-originated stalled replay
accounting. The Apollo SMMUv3 TBU now records data-path translation faults as
stalled EVENTQ records with nonzero STAG values, allocates an
`arch_endpoint_replay_record`, exposes `REG_ARCH_ENDPOINT_REPLAY_STATUS`, and
accounts pending, retry, success, and terminate outcomes. A matching
`CMD_RESUME(RETRY)` re-runs translation for the StreamID+STAG replay record, so
software can install a mapping and observe replay success through the component
status register and modeled ATS/page-walk state.

The component suite adds `EndpointTransactionReplayRetriesAfterCmdResume` for an
unmapped endpoint read, stalled EVENTQ emission, mapping installation, matching
`CMD_RESUME(RETRY)`, endpoint replay accounting, stall clearing, and successful
retry translation. The lane and compliance checker now gate this slice with
`tbu:endpoint-replay-accounting`.

Verification is recorded in
`doc/verification/qbox-smmuv3-endpoint-replay-verification-2026-05-10.md`. This
narrows the endpoint replay gap, but remains a functional accounting model: the
original TLM transaction is still not actually blocked and re-driven through a
SystemC scheduling path, and full Arm SMMUv3 event/stall replay parity remains
open.

## 2026-05-11 SMMU-COMP-050 endpoint replay redrive progress note

Implemented a follow-up functional slice for downstream endpoint payload
re-drive. The Apollo SMMUv3 TBU now captures write payload bytes in
`arch_endpoint_replay_record` when a data-path access stalls, and
`redrive_endpoint_replay()` re-walks the current mapping and issues downstream
TLM read/write payloads after a matching `CMD_RESUME(RETRY)`. Retry success is
now counted only after the downstream re-drive succeeds.

The component suite adds `EndpointTransactionReplayRedrivesWritePayload`, which
verifies an unmapped endpoint write stalls, records a nonzero STAG, leaves the
physical memory unchanged, accepts a later mapping, consumes a matching
`CMD_RESUME(RETRY)`, and observes the held payload written to downstream memory.
The lane and compliance checker now gate this with
`tbu:endpoint-replay-redrive`.

Verification is recorded in
`doc/verification/qbox-smmuv3-endpoint-redrive-verification-2026-05-11.md`.
This narrows the endpoint replay gap, but remains a functional slice: the
original caller-visible `b_transport()` is not suspended until resume, and full
Arm SMMUv3 event/stall replay parity remains open.

## 2026-05-11 SMMU-COMP-050 endpoint blocking replay progress note

Implemented a follow-up functional slice for caller-visible endpoint replay
blocking. The Apollo SMMUv3 TBU now has an opt-in
`ARCH_ENDPOINT_REPLAY_BLOCKING_ENABLE` mode exposed through
`REG_ARCH_ENDPOINT_REPLAY_CTRL`. In this mode, a data-path endpoint access that
stalls on translation records the STAG, stores the replay payload, waits on the
endpoint replay resume event, and returns the retry result to the original
`b_transport()` caller after matching `CMD_RESUME(RETRY)` re-drives the payload.

The component suite adds `EndpointTransactionReplayBlocksCallerUntilCmdResume`,
which spawns an endpoint writer, observes it blocked with a pending replay
record, installs a mapping, issues matching `CMD_RESUME(RETRY)`, and then
verifies the original caller returns `TLM_OK_RESPONSE` and the held payload is
written to downstream memory. The lane and compliance checker now gate this with
`tbu:endpoint-replay-blocking`.

Verification is recorded in
`doc/verification/qbox-smmuv3-endpoint-blocking-verification-2026-05-11.md`.
This narrows the endpoint replay gap, but remains a functional slice: full Arm
SMMUv3 event matrix parity, stall suppression/merge, early retry behavior, and
upstream Linux `arm-smmu-v3` event-thread recovery parity remain open.

## 2026-05-11 SMMU-COMP-050 stall suppression progress note

Implemented a follow-up functional slice for stalled-fault suppression and merge.
The Apollo SMMUv3 TBU now uses `find_stall_by_fault()` to detect an already
pending stall with the same StreamID, IOVA, and SSID-valid/SSID tuple. Duplicate
stalled faults reuse the pending STAG, increment `m_arch_stall_suppressed` and
`m_arch_stall_merged`, and skip the duplicate EVENTQ push. Distinct IOVA or SSID
faults still allocate independent STAG values and EVENTQ entries.

The component suite adds `StalledFaultsSuppressDuplicateEventRecords`, which
checks duplicate suppression, STAG reuse, `REG_ARCH_STALL_MERGE_STATUS`, EVENTQ
producer stability, and allocation of a new STAG for a distinct IOVA. The lane
and compliance checker now gate this with `tbu:stall-suppression-merge`.

Verification is recorded in
`doc/verification/qbox-smmuv3-stall-suppression-verification-2026-05-11.md`.
This narrows the stall replay gap, but remains a functional slice: full Arm
SMMUv3 event matrix parity, early retry behavior, MSI/GIC ordering, and upstream
Linux `arm-smmu-v3` event-thread recovery parity remain open.

## 2026-05-11 SMMU-COMP-050 endpoint early-retry progress note

Implemented a follow-up functional slice for permitted SMMUv3 stalled-transaction
early retry on the endpoint replay path. The Apollo SMMUv3 TBU now exposes
`ARCH_ENDPOINT_REPLAY_EARLY_RETRY` through `REG_ARCH_ENDPOINT_REPLAY_CTRL` and
accounts attempts/success/failure through `REG_ARCH_EARLY_RETRY_STATUS`.
`early_retry_endpoint_replays()` retries pending endpoint replay records using
the current translation state without emitting another EVENTQ record. A
successful early retry keeps the STAG/stall pending, so software must still
acknowledge the original stalled fault with a matching `CMD_RESUME` command;
that later acknowledgement does not issue a duplicate downstream replay.

The component suite adds
`EndpointEarlyRetryDoesNotDuplicateFaultAndRequiresResume`, which verifies a
failed early retry leaves the event producer stable and the stall pending, a
second early retry succeeds after a mapping is installed without pushing another
EVENTQ record, and the original STAG remains pending until `CMD_RESUME(RETRY)`
acknowledges it. The lane and compliance checker now gate this with
`tbu:stall-early-retry`.

Verification is recorded in
`doc/verification/qbox-smmuv3-early-retry-verification-2026-05-11.md`. This
narrows the stall replay gap, but remains a functional slice: full Arm SMMUv3
EVENTQ byte-exact matrix parity, optional pre-commit stale-event discard/commit
policy, MSI/GIC ordering, and upstream Linux `arm-smmu-v3` event-thread recovery
parity remain open.

## 2026-05-11 SMMU-COMP-050 endpoint early-retry stale-event discard progress note

Implemented a follow-up functional slice for the permitted SMMUv3 stale-event
policy when a stalled transaction successfully early-retries before its original
fault event is committed to the Event queue. The Apollo TBU now tracks whether a
pending stall's EVENTQ record has been committed, and
`discard_uncommitted_early_retry()` removes a buffered stale EVENTQ record when
early retry succeeds before the record is visible to software. The stale-event
case clears the modeled STAG and endpoint replay pending state because no
software-visible fault record remains to acknowledge.

The component suite adds `EndpointEarlyRetryDiscardsUncommittedStaleEvent`, which
fills the Event queue, forces an endpoint stalled fault into the internal stall
buffer, installs a mapping, triggers early retry, verifies the held payload is
written downstream, verifies the buffered event is discarded and pending counts
clear, and confirms advancing `EVENTQ_CONS` does not later redrive the stale
record. The lane and compliance checker now gate this with
`tbu:stall-early-retry-discard`.

Verification is recorded in
`doc/verification/qbox-smmuv3-early-retry-discard-verification-2026-05-11.md`.
This narrows the stall replay gap, but remains a functional slice: full Arm
SMMUv3 EVENTQ byte-exact matrix parity, the complete implementation-defined
stale-event policy matrix, MSI/GIC ordering, and upstream Linux `arm-smmu-v3`
event-thread recovery parity remain open.

## 2026-05-11 SMMU-COMP-050 EVENTQ access-attribute progress note

Implemented a follow-up functional slice for Arm SMMUv3 EVENTQ common access
attributes. The Apollo TBU now defines the Linux `arm-smmu-v3` word-1 positions
for `EVTQ_1_PnU`, `EVTQ_1_InD`, `EVTQ_1_RnW`, and `EVTQ_1_CLASS`, carries
modeled privilege/instruction attributes through the Apollo SMMU TLM extension,
and emits stalled translation EVENTQ records with modeled `PnU`, `InD`, `RnW`,
and `CLASS=IN` bits. The model keeps the architectural constraint that `InD` is
not set for write-class events.

Ground truth came from the local Linux `arm-smmu-v3.h` definitions for
`EVTQ_1_PnU`, `EVTQ_1_InD`, `EVTQ_1_RnW`, and `EVTQ_1_CLASS`, plus the local
Arm SMMUv3 reference text in `sources/smmu/wiki/concepts/event-queue.md` and
`sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
for the §7.3 common fields.

Verification is recorded in
`doc/verification/qbox-smmuv3-event-record-access-attrs-verification-2026-05-11.md`.
The component suite now includes
`ArchitectedEventRecordCommonAccessAttributesAreEncoded`, and the static checker
adds `tbu:event-record-common-access-attrs`. This remains a functional slice:
byte-exact layouts for every EVENTQ event type, fetch-address/event-specific
fields, Secure-state `NSIPA`, RME `GPCF`, and upstream Linux `arm-smmu-v3` event
thread recovery parity remain open.

## 2026-05-11 SMMU-COMP-050 EVENTQ stage-2 IPA progress note

Implemented a follow-up byte-layout slice for EVENTQ word 3. The Apollo TBU now
keeps private replay syndrome detail in `REG_ARCH_FAULT_DETAIL` instead of
serializing that private detail into EVENTQ word 3, adds `arch_event_record_word3()`,
and encodes modeled stage-2 fault IPA bits with the Linux `EVTQ_3_IPA` mask.
S1 stalled records now leave word 3 RES0 unless an event-specific field is
modeled, while stage-2 translation faults expose the modeled IPA in the
architected word-3 field.

Ground truth came from the local Linux `arm-smmu-v3.h` definitions for
`EVTQ_3_IPA` and `EVTQ_3_FETCH_ADDR`, plus the Arm SMMUv3 §7.3 common-field
and F_TRANSLATION text in `sources/smmu`. Component coverage adds
`ArchitectedEventRecordStage2IpaIsEncoded`; the checker adds
`tbu:event-record-stage2-ipa`.

This remains a functional slice: byte-exact word-3 fetch addresses for all fetch
faults, TTRnW/event-specific fields, Secure-state `NSIPA`, RME `GPCF`, and full
Linux `arm-smmu-v3` event-thread recovery remain open.

## 2026-05-11 SMMU-COMP-050 EVENTQ fetch-address progress note

Implemented a follow-up byte-layout slice for F_STE_FETCH and F_CD_FETCH
records. The Apollo TBU now tracks `m_arch_last_fetch_addr`, records fetch
addresses with `set_arch_fetch_fault()` on modeled STE/CD external-abort paths,
and emits the Linux/Arm `EVTQ_3_FETCH_ADDR` bits through
`arch_event_record_word3()` instead of reusing private syndrome detail.

Validation now covers `ArchitectedEventRecordFetchAddressIsEncoded`; the checker
adds `tbu:event-record-fetch-address`, and the lane script gates both the TBU
fetch-address state and component test. This remains a functional slice rather
than full EVENTQ parity: F_VMS_FETCH, F_WALK_EABT, GPCF/RME, NSIPA, and the full
architected event matrix remain open.

## 2026-05-11 SMMU-COMP-050 EVENTQ class-selector progress note

Implemented a follow-up common-field slice for EVENTQ `CLASS`. The Apollo TBU
now routes stalled translation-table faults through `arch_event_class_for_fault()`
and emits `CLASS=TT` for modeled `ARCH_FAULT_TABLE_INVALID` records instead of
forcing every stalled translation event to `CLASS=IN`.

Validation now covers `ArchitectedEventRecordClassDistinguishesTableFaults`; the
checker adds `tbu:event-record-class-selector`, and the lane script gates both
the class selector and component test. Full EVENTQ class parity remains open for
all Arm event types, CD-originated stage-2 faults, NSIPA, RME/GPCF, and
F_WALK_EABT/F_VMS_FETCH.

## 2026-05-11 SMMU-COMP-050 EVENTQ F_WALK_EABT progress note

Implemented a follow-up EVENTQ record slice for descriptor-fetch external
aborts. The Apollo TBU now maps failed translation descriptor memory reads to
`ARCH_FAULT_WALK_EABT`/`ARCH_EVENT_F_WALK_EABT`, preserves the descriptor
`FetchAddr` through `set_arch_fetch_fault()`, emits it through EVENTQ word 3,
and uses `CLASS=TT` for the modeled stalled event.

Validation now covers `ArchitectedEventRecordWalkEabtCarriesFetchAddress`; the
checker adds `tbu:event-record-walk-eabt`, and the lane script gates the event
number plus component test. Remaining blockers include synthetic CD-originated
stage-2 walk-abort class selection, F_VMS_FETCH, NSIPA, RME/GPCF, and full
Linux event-thread recovery parity.

## 2026-05-11 SMMU-COMP-050 EVENTQ stage-2 CD class progress note

Implemented a follow-up EVENTQ class slice for stage-2 translation faults that
originate from a CD fetch. The Apollo TBU now carries `m_arch_fault_event_class`
so modeled stage-2 translation events can select `CLASS=CD`, `CLASS=TT`, or
`CLASS=IN` rather than deriving every stage-2 event from the input-address
fallback. `ArchitectedEventRecordStage2CdFaultUsesClassCd` verifies that a
modeled CD-originated stage-2 fault records `CLASS=CD`, the input address in
word 2, and the CD IPA in EVENTQ word 3.

This is still a functional EVENTQ encoding slice. The follow-up progress note
below connects the linear nested CD-fetch path to the stage-2 walker, while
64K-L2/L1CD, TT-class nested walk faults, and Linux event-thread recovery parity
remain open.

## 2026-05-11 SMMU-COMP-030/040/050 nested CD fetch S2 progress note

Implemented a follow-up nested stream/context walk slice. When
`STE.Config=NESTED`, the Apollo TBU now treats the modeled CD address as an IPA,
translates it through the stage-2 descriptor walker before reading the CD, and
preserves `m_arch_fault_event_class = ARCH_EVENT_CLASS_CD` plus
`m_arch_last_ipa = cd_pa` if the CD-fetch stage-2 walk fails. After a successful
CD-fetch translation the event class returns to `CLASS=IN` so later transaction
IPA faults are not misclassified.

`ArchitectedWalkerStage2AndNestedMatrix` now stores nested CDs at the
stage-2-translated CD PA, and
`ArchitectedNestedCdFetchStage2FaultRecordsClassCd` verifies a stalled negative
replay record with `S2`, `CLASS=CD`, the original input address, and the CD IPA
in EVENTQ word 3. The checker adds `tbu:nested-cd-fetch-stage2-fault`, while
`SMMU-COMP-030`, `SMMU-COMP-040`, and `SMMU-COMP-050` classifications now call
out nested CD-fetch/S2 coverage.

Verification is recorded in
`doc/verification/qbox-smmuv3-nested-cd-fetch-s2-verification-2026-05-11.md`:
Apollo TBU component build and CTest passed, and the final static/checker/lane
pass reported `SUMMARY {"pass": 345}` with
`full_smmuv3_compliance=not_claimed`.

This remains a functional slice. Nested 64K-L2 L1CD fetch stage-2 translation,
full Arm EVENTQ matrix parity, Secure-state `NSIPA`, RME/GPCF, F_VMS_FETCH,
and upstream Linux event-thread recovery remain open. The follow-up nested TT
fetch note below covers stage-1 translation-table descriptor fetch S2 faults
with `CLASS=TT`.


## 2026-05-11 SMMU-COMP-030/040/050 nested TT fetch S2 progress note

Implemented a follow-up nested translation-table fetch slice. When
`STE.Config=NESTED`, the Apollo TBU now treats stage-1 translation-table
descriptor fetch addresses as IPAs, translates them through the active stage-2
walker before reading the descriptor, and preserves `ARCH_FAULT_STAGE_S2` plus
`ARCH_EVENT_CLASS_TT` if that descriptor-fetch translation fails.

`ArchitectedWalkerStage2AndNestedMatrix` now maps the nested stage-1 table pages
through stage 2 on the successful nested S1+S2 path. The new
`ArchitectedNestedTtFetchStage2FaultRecordsClassTt` negative replay vector
verifies a stalled EVENTQ record with `S2`, `CLASS=TT`, the original input
address in word 2, and the TT fetch IPA in word 3. The checker adds
`tbu:nested-tt-fetch-stage2-fault`, while `SMMU-COMP-030`, `SMMU-COMP-040`, and
`SMMU-COMP-050` classifications now call out nested CD/TT-fetch/S2 coverage.

Verification is recorded in
`doc/verification/qbox-smmuv3-nested-tt-fetch-s2-verification-2026-05-11.md`:
Apollo TBU component build and CTest passed, and the final static/checker/lane
pass reported `SUMMARY {"pass": 353}` with
`full_smmuv3_compliance=not_claimed`.

This remains a functional slice. Full Arm EVENTQ matrix parity, Secure-state
`NSIPA`, RME/GPCF, F_VMS_FETCH, and upstream Linux event-thread recovery remain
open. The follow-up nested L1CD fetch note below covers 64K-L2 L1CD fetch
stage-2 translation.


## 2026-05-11 SMMU-COMP-030/040/050 nested L1CD fetch S2 progress note

Implemented a follow-up nested 64K-L2 context-descriptor-table slice. When
`STE.Config=NESTED` and `STE.S1FMT=64K_L2`, the Apollo TBU now treats the L1CD
fetch address as an IPA, translates it through the active stage-2 walker before
reading the L1CD descriptor, and preserves `ARCH_FAULT_STAGE_S2` plus
`ARCH_EVENT_CLASS_CD` if that L1CD-fetch translation fails. The L1CD descriptor's
L2 pointer remains an IPA and is translated by the existing nested CD-fetch S2
path before the selected CD is read.

`ArchitectedNestedL1CdFetchStage2Walks` verifies the success path by placing the
L1CD and selected L2 CD at stage-2-translated PAs, while
`ArchitectedNestedL1CdFetchStage2FaultRecordsClassCd` verifies a stalled EVENTQ
record with `S2`, `CLASS=CD`, the original input address in word 2, and the L1CD
fetch IPA in word 3. The checker adds `tbu:nested-l1cd-fetch-stage2-fault`, and
`SMMU-COMP-030`, `SMMU-COMP-040`, and `SMMU-COMP-050` classifications now call
out nested CD/L1CD/TT-fetch/S2 coverage.

Verification is recorded in
`doc/verification/qbox-smmuv3-nested-l1cd-fetch-s2-verification-2026-05-11.md`:
Apollo TBU component build and CTest passed, and the final static/checker/lane
pass reported `SUMMARY {"pass": 362}` with
`full_smmuv3_compliance=not_claimed`.

This remains a functional slice. Full Arm EVENTQ matrix parity, Secure-state
`NSIPA`, RME/GPCF, F_VMS_FETCH, full upstream CD invalidation lifecycle parity,
and upstream Linux event-thread recovery remain open.

## 2026-05-11 SMMU-COMP-050 EVENTQ F_VMS_FETCH progress note

Implemented a narrow EVENTQ matrix slice for VMS fetch external-abort records.
The Apollo TBU now defines `ARCH_FAULT_VMS_FETCH`, maps it to architected event
number `ARCH_EVENT_F_VMS_FETCH = 0x25`, and emits the modeled VMS `FetchAddr`
through `arch_event_record_word3()`. Component coverage
`ArchitectedEventRecordVmsFetchCarriesFetchAddress` verifies event number,
SSV/SubstreamID, StreamID, fetch-address word3, and private fault detail reason.

This is still not full VMS/MPAM compliance. `STE.VMSPtr`, `STE.S1MPAM`,
`PARTID_MAP`, VMS caching/invalidation (`CMD_CFGI_VMS_PIDM`), exact VMS fetch
priority, Secure-state `NSIPA`, RME/GPCF, and full upstream Linux event-thread
recovery remain open. Evidence is recorded in
`doc/verification/qbox-smmuv3-event-record-vms-fetch-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-050 EVENTQ GPCF progress note

Implemented a narrow EVENTQ GPCF field-plumbing slice. The Apollo TBU now exposes
`ARCH_EVENT_GPCF_SHIFT`, tracks modeled `m_arch_fault_gpcf` state, accepts a GPCF
cause through `set_arch_fetch_fault(..., gpcf)`, and sets the EVENTQ bit for
fetch-event records (`F_STE_FETCH`, `F_CD_FETCH`, `F_VMS_FETCH`, `F_WALK_EABT`).
Component coverage `ArchitectedEventRecordFetchGpcfBitIsEncoded` verifies a
stalled `F_WALK_EABT` record with STALL, GPCF, and FetchAddr populated.

This is still not full RME/GPT/GPC compliance. Root/Realm controls, GPT walks,
SMMU-originated GPC checks, GPF/GPT fault registers, interrupt/observability
rules, Secure-state `NSIPA`, and full Linux event-thread recovery remain open.
Evidence is recorded in
`doc/verification/qbox-smmuv3-event-record-gpcf-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-050 EVENTQ NSIPA progress note

Implemented a narrow EVENTQ NSIPA field-plumbing slice. The Apollo TBU now
exposes `ARCH_EVENT_NSIPA_SHIFT`, tracks modeled `m_arch_fault_nsipa` state,
clears it across replay/probe/fault paths, and sets the EVENTQ bit for supplied
stalled stage-2 records while preserving S2, CLASS, InputAddr, and IPA word3
layout. Component coverage adds `ArchitectedEventRecordNsipaBitIsEncoded`.

This remains a modeled field-encoding slice rather than full Secure-state SMMUv3
support: Secure Event queue routing, Secure/Non-secure stream-table banking,
Secure `NSCFG` and `S2TTB` versus `S_S2TTB` routing, full event matrix parity,
full RME/GPT/GPC, and upstream Linux event-thread recovery remain open.

## 2026-05-11 SMMU-COMP-030/050 stream/substream EVENTQ progress note

Implemented a narrow stream/context-descriptor fault-to-EVENTQ slice. The Apollo
TBU now distinguishes modeled S1DSS stream-disabled faults from generic CD
invalid faults via `ARCH_FAULT_STREAM_DISABLED`, maps them to
`ARCH_EVENT_F_STREAM_DISABLED = 0x06`, and maps modeled bad SubstreamID policy or
range failures via `ARCH_FAULT_BAD_SUBSTREAMID` to
`ARCH_EVENT_C_BAD_SUBSTREAMID = 0x08`. `arch_cd_address()` now applies those
reasons for no-SSID `S1DSS=TERMINATE`, explicit SubstreamID while substreams are
disabled, SubstreamID 0 disabled by `S1DSS=SSID0`, out-of-range `S1CDMax`, and
invalid modeled 64K-L2 L1CD entries.

Component coverage adds `ArchitectedStreamDisabledAndBadSubstreamEvents`, which
verifies the two event numbers plus StreamID/SSID EVENTQ fields. Checklist and
lane guards now include this as a SMMU-COMP-030/050 functional slice.

This remains narrower than full Arm EVENTQ matrix parity. Config==0 no-event
behavior, all ATS/PASID variants, Secure event queue/security-state routing,
full RME/GPT/GPC behavior, and upstream Linux arm-smmu-v3 recovery parity remain
open.

## 2026-05-11 SMMU-COMP-050/060 ATS Translated F_TRANSL_FORBIDDEN progress note

Implemented a narrow ATS Translated transaction slice. The common Apollo SMMU
TLM extension now carries a default-off `translated` sideband for modeled AT=0b10
endpoint transactions. When `CR0.ATSCHK` is enabled, the Apollo TBU checks that
sideband against the modeled STE and records `ARCH_EVENT_F_TRANSL_FORBIDDEN`
through `ARCH_FAULT_TRANSL_FORBIDDEN` if the effective `STE.EATS` value forbids
Translated traffic. `AtsTranslatedTransactionForbiddenRecordsEvent` verifies the
forbidden `EATS=DISABLED` case and a permitted `EATS=FULL` control path.

This remains a functional slice only. Full split-stage EATS=0b10 behavior,
Secure-state routing, DPT/GPC checks, PASIDTT event priority, CXL attributes,
F_UUT no-event handling, and upstream Linux recovery parity remain open.

## 2026-05-11 SMMU-COMP-050 EVENTQ conflict events progress note

Implemented a narrow EVENTQ conflict event-number plumbing slice. The Apollo TBU
now defines modeled conflict reasons for TLB and configuration-cache conflict
reports, maps them to `ARCH_EVENT_F_TLB_CONFLICT = 0x20` and
`ARCH_EVENT_F_CFG_CONFLICT = 0x21`, and preserves those reason codes in the
private fault detail register. Component coverage
`ArchitectedConflictEventsAreMapped` verifies both records carry the expected
architected event number, StreamID, InputAddr, and implementation-defined
diagnostic word.

This remains event plumbing only. Actual detection of TLB multi-hit conflicts,
configuration-cache conflict discovery/recovery, broader implementation-specific
diagnostic coverage, full event priority ordering, Secure-state routing,
RME/GPT/GPC interactions, and upstream Linux event-thread recovery parity remain
open for this plumbing-only slice. Evidence is recorded in
`doc/verification/qbox-smmuv3-conflict-events-verification-2026-05-11.md`.

The follow-up conflict diagnostic payload slice moves the modeled TLB and
configuration-cache conflict reports beyond zero-filled diagnostics by assigning
implementation-defined word3 Reason constants
`ARCH_EVENT_CONFLICT_REASON_TLB_TAG_MISMATCH` and
`ARCH_EVENT_CONFLICT_REASON_CFG_STE_CONT`. Component coverage verifies both the
direct `ArchitectedConflictEventsAreMapped` path and the TLB/config-cache
conflict probe paths preserve those Reason payloads in the EVENTQ record.
Evidence is recorded in
`doc/verification/qbox-smmuv3-conflict-diagnostic-payload-verification-2026-05-11.md`.

The follow-up ATS/TLB cache-conflict recovery slice adds a modeled conflict
detector over the Apollo ATS cache tags. `ARCH_CTRL_TLB_CONFLICT` now stages a
stale same-StreamID/same-page entry, detects a conflicting ASID/VMID/SSID tuple,
records `F_TLB_CONFLICT`, and invalidates the stale page entries while counting
the recovery. Component coverage `AtsCacheConflictProbeRecordsAndRecovers`
verifies the event number, StreamID, SSID tagging, InputAddr, stale-entry
removal, and recovery counter. This narrows the TLB side of conflict recovery;
configuration-cache conflict recovery is handled by the follow-up slice below.

The follow-up configuration-cache conflict recovery slice adds a modeled STE
configuration cache. `ARCH_CTRL_CFG_CONFLICT` stages a stale same-security
overlapping STE span, detects a non-identical requested STE within that span,
records `F_CFG_CONFLICT`, invalidates stale configuration-cache entries, and
counts the recovery. Component coverage
`ConfigCacheConflictProbeRecordsAndRecovers` verifies event number, StreamID,
InputAddr, stale-entry recovery, and that a Secure stale entry does not conflict
with a Non-secure lookup. This narrows implementation-defined
configuration-cache conflict handling; broader implementation-specific
diagnostic matrix parity, Secure/Realm event routing, full real-hardware
configuration-cache geometry, RME/GPT/GPC interactions, and upstream Linux
recovery parity remain open.
Evidence is recorded in
`doc/verification/qbox-smmuv3-config-cache-conflict-recovery-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-030/050/060 STE.Config disabled no-event progress note

Implemented a narrow disabled-stream no-event slice. The Apollo TBU now treats a
valid `STE.Config==0b000` as an architected disabled stream rather than an
illegal STE encoding, keeps `ARCH_FAULT_STREAM_DISABLED` visible in private
status, and raises `m_arch_fault_record_suppressed` so probe/negative-replay
paths do not push EVENTQ records for this no-event case. ATS Translation Requests
against the same disabled stream now return modeled UR status without recording
an Event queue entry.

Component coverage adds `ArchitectedConfigDisabledSuppressesEvents` for normal
stream/context probes and `AtsConfigDisabledReturnsUrWithoutEvent` for ATS
Translation Requests. This closes the previously noted `Config==0` no-event
slice, but exact event priority ordering, MEV merging, Secure/Realm routing,
packet-level PCIe/CXL attributes, and upstream Linux event-thread recovery parity
remain open. Evidence is recorded in
`doc/verification/qbox-smmuv3-config-disabled-no-event-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-050 F_UUT EVENTQ progress note

Implemented a narrow unsupported-upstream transaction EVENTQ slice. The Apollo
TBU now exposes `ARCH_FAULT_UNSUPPORTED_UPSTREAM`, maps it to the architected
`ARCH_EVENT_F_UUT = 0x01`, and adds the private harness control
`ARCH_CTRL_RECORD_F_UUT` so tests can inject the event without pretending that
QBox has complete AMBA/PCIe illegal-transaction detection. The emitted F_UUT
record uses a zero implementation-defined Reason field, matching the pinned
software reference model, and can be recorded with `CR0.EVENTQEN` even when
`CR0.SMMUEN` is clear.

Component coverage adds `ArchitectedUnsupportedUpstreamEventCanBeInjected`,
which verifies the event number, StreamID, zero Reason/RES0 words, private fault
reason, and Event queue producer update. This remains an injection/plumbing slice
only: real unsupported upstream transaction classification, packet attribute
reason codes, ATS Translated F_UUT no-event matrices, Secure/Realm routing,
MEV/priority subtleties, and upstream Linux event-thread recovery parity remain
open. Evidence is recorded in
`doc/verification/qbox-smmuv3-f-uut-event-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-050 C_BAD_STREAMID RECINVSID progress note

Implemented a narrow normal-transaction `C_BAD_STREAMID` event-recording gate.
The Apollo TBU now preserves the private `ARCH_FAULT_BAD_STREAM_ID` status for
out-of-range StreamIDs, but suppresses the Event queue record unless
`SMMU_CR2.RECINVSID` permits invalid StreamID event recording. This mirrors the
pinned reference and the Arm CR2 `RECINVSID` definition for normal transactions,
while leaving the already-modeled ATS Translation Request `REC_CFG_ATS` plus
`RECINVSID` gate intact.

Component coverage adds `BadStreamIdHonorsCr2RecInvsidForEventRecording`, which
verifies no EVENTQ producer movement with `RECINVSID=0` and then verifies
`C_BAD_STREAMID` event number/StreamID recording once `RECINVSID=1`.

This remains a normal-probe slice only. Full translated-transaction event gates,
Secure/Realm CR2 banking, implementation-defined event merging, full event
priority validation, and upstream Linux event-thread recovery parity remain
open. Evidence is recorded in
`doc/verification/qbox-smmuv3-recinvsid-bad-streamid-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-050 configuration-event RES0 payload progress note

Implemented a narrow EVENTQ payload-layout correction for non-stall
configuration events. The Apollo TBU now treats `C_BAD_STREAMID`, `C_BAD_STE`,
`C_BAD_CD`, and `F_STREAM_DISABLED` as architected RES0-payload records for
non-stall Event queue entries, while preserving the existing stalled-fault
payload layout for replay/resume tests. `C_BAD_SUBSTREAMID` is intentionally not
included because its architected record carries an InputAddr field.

Component coverage now verifies the normal `C_BAD_STREAMID` `RECINVSID` path has
zero payload words and adds `ArchitectedConfigEventPayloadsAreRes0` for non-stall
`C_BAD_STE`, `C_BAD_CD`, and `F_STREAM_DISABLED` records.

This remains a payload-layout slice only. Full event-priority validation,
implementation-defined merge behavior, Secure/Realm Event queues, translated ATS
configuration-fault gates, and upstream Linux recovery parity remain open.
Evidence is recorded in
`doc/verification/qbox-smmuv3-config-event-res0-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-050/060 ATS Translated REC_CFG_ATS progress note

SMMU-COMP-050/060 now has a follow-up ATS Translated transaction slice for
configuration-fault reporting. The Apollo TBU checks invalid STE and invalid
StreamID conditions before accepting an ATS Translated transaction when
`CR0.ATSCHK` is enabled, suppresses the EVENTQ record while
`CR2.REC_CFG_ATS` is clear, and records the architected configuration event when
`CR2.REC_CFG_ATS` is set. The component test also verifies the architectural
rule that Translated-transaction `C_BAD_STREAMID` recording is not gated by
`CR2.RECINVSID`.

This remains a functional slice. Full ATS Translated parity still excludes
Secure/Realm routing, split-stage protocol-specific restrictions, DPT checks,
address-size behavior above implemented PA size, and full upstream Linux
recovery ordering.

## 2026-05-11 SMMU-COMP-050 C_BAD_SUBSTREAMID layout progress note

SMMU-COMP-050 now has an explicit `C_BAD_SUBSTREAMID` layout guard. The Apollo
TBU stream/substream component test verifies the event number, StreamID,
SubstreamID/SSV fields, and the architected `InputAddr` payload for the bad
SubstreamID record. This prevents the `C_BAD_SUBSTREAMID` record from being
accidentally folded into the RES0-payload handling used by other configuration
events such as `C_BAD_STREAMID`, `C_BAD_STE`, `C_BAD_CD`, and
`F_STREAM_DISABLED`.

This remains a functional slice. Full parity still requires the entire event
matrix, Secure/Realm event routing, and upstream recovery behavior.

## 2026-05-11 SMMU-COMP-050/060 ATS Translated SMMUEN/ATSCHK progress note

SMMU-COMP-050/060 now has an explicit ATS Translated transaction gate for the
architected `SMMUEN` and `ATSCHK` split. The Apollo TBU now checks every
Translated transaction before accepting it: with `CR0.SMMUEN==0` it aborts the
transaction and records modeled `F_TRANSL_FORBIDDEN` when `EVENTQEN` is set;
with `CR0.SMMUEN==1` and `CR0.ATSCHK==0` it accepts the Translated transaction
without walking the Stream table or checking configuration structures. This
matches the Arm rule that `ATSCHK==0` means configuration errors such as
`C_BAD_STREAMID` are not detected for Translated traffic.

Component coverage adds `AtsTranslatedTransactionsHonorSmmuenAndAtschk`, which
verifies the SMMU-disabled `F_TRANSL_FORBIDDEN` event and then proves an
out-of-range StreamID does not create a `C_BAD_STREAMID` event while `ATSCHK` is
clear. This remains a functional slice: address-size checks above implemented PA
size, split-stage `EATS==0b10` behavior, DPT, Secure/Realm routing, and full
upstream recovery ordering remain open.

## 2026-05-11 SMMU-COMP-050/060 ATS Translated priority progress note

Added a partial ATS Translated event-priority guard for the `ATSCHK==1` path.
The component test now verifies that configuration faults are detected before
`F_TRANSL_FORBIDDEN` from disabled effective `STE.EATS`: an out-of-range
StreamID records `C_BAD_STREAMID`, an invalid STE records `C_BAD_STE`, and only
a valid S1 STE with disabled EATS records `F_TRANSL_FORBIDDEN`.

This is deliberately narrow. It does not claim the complete priority list from
SMMUv3 section 3.9.1.3, Secure/Realm priority cases, `F_VMS_FETCH`, conflict
cases, split-stage/DPT ordering, GPC ordering, or implementation-defined merging
behavior. Evidence is recorded in
`doc/verification/qbox-smmuv3-ats-translated-priority-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-050/060 ATS Translated address-size progress note

Added a modeled ATS Translated address-size behavior slice. The Arm SMMUv3
architecture leaves Translated transactions whose address bits exceed the
implemented PA size implementation-defined: either abort with no Event/fault
record or truncate to the supported PA size. QBox now chooses the deterministic
no-event abort behavior for addresses above the model's 48-bit descriptor output
mask. This check runs even when `CR0.ATSCHK==0`, because ATSCHK bypasses
configuration lookup but not address-size checking.

Component coverage adds `AtsTranslatedAddressSizeAbortIsNoEvent`, which verifies
an oversized Translated address terminates with the private `ARCH_FAULT_ADDR_SIZE`
reason, leaves `m_fault_count` and the EVENTQ producer unchanged, and does not
walk the Stream table. This remains a functional slice: OAS field modeling,
truncate behavior, GPC/DPT follow-on checks, Secure/Realm routing, and complete
ATS packet semantics remain open.

## 2026-05-11 SMMU-COMP-050/060 ATS Translated split-stage progress note

Added an explicit implementation-defined split-stage ATS Translated guard. Arm
SMMUv3 permits an implementation to abort with `F_TRANSL_FORBIDDEN` when
`STE.EATS==0b10` split-stage ATS is inappropriate for the transaction protocol.
QBox does not yet model a bus protocol that carries Translated IPA traffic into
the TBU for a second-stage-only walk, so it now rejects such traffic
predictably instead of silently treating an IPA as a PA.

Component coverage adds `AtsTranslatedSplitStageUnsupportedRecordsForbidden`,
which verifies `CR0.ATSCHK==1` plus `STE.EATS==0b10` records
`F_TRANSL_FORBIDDEN`, preserves `m_arch_last_eats == ARCH_STE_EATS_SPLIT`, and
pushes one EVENTQ record. This remains a functional slice: true split-stage IPA
stage-2 translation, DPT checks, Secure/Realm routing, GPC ordering, and full
packet-level ATS protocol remain open.

## 2026-05-11 SMMU-COMP-050/060 ATS Translated STE.Config abort progress note

Added an ATS Translated `STE.Config==0b100` guard. The SMMUv3 ATS Translated
rules list this as a direct `F_TRANSL_FORBIDDEN` abort when `CR0.ATSCHK==1`,
not as a REC_CFG_ATS-gated configuration-fetch event. QBox now treats the
encoding as modeled for this path, records `F_TRANSL_FORBIDDEN`, and avoids
falling through to the generic `C_BAD_STE` handling used for illegal or
reserved STE encodings.

Component coverage adds `AtsTranslatedConfigAbortRecordsForbidden`, which
verifies `CR0.ATSCHK==1`, `STE.Config==0b100`, and `STE.EATS==Full ATS` produce
one `F_TRANSL_FORBIDDEN` EVENTQ record. This remains a functional slice: full
priority ordering, Secure/Realm variants, DPT, GPC, and upstream recovery parity
remain open.

## 2026-05-11 SMMU-COMP-050/060 ATS Translated DPT unsupported progress note

Added an ATS Translated `STE.EATS==0b11` DPT guard. QBox does not yet model
Device Permission Table lookup or `DPT_WALK_EN`, so the Apollo TBU now treats
DPT-selected Translated traffic as a failed DPT check and records
`F_TRANSL_FORBIDDEN` instead of permitting unchecked physical traffic.

Component coverage adds `AtsTranslatedDptUnsupportedRecordsForbidden`, which
verifies `CR0.ATSCHK==1` plus `STE.EATS==DPT` preserves the decoded EATS value
and pushes one `F_TRANSL_FORBIDDEN` EVENTQ record. This remains a functional
slice: real DPT tables, DPT-disabled register reporting, Secure/Realm DPT
variants, GPC ordering, and upstream recovery parity remain open.

## 2026-05-11 SMMU-COMP-050/060 ATS Translated PASIDTT progress note

Added ATS Translated PASID-prefix sanitization for the current `SMMU_IDR3.PASIDTT==0`
model. When an endpoint supplies SubstreamID/PnU/InD metadata on a Translated
transaction, QBox now clears those attributes before forming ATS Translated event
records, matching the architectural rule that Translated traffic is treated as
`SSV=0`, `PnU=0`, and `InD=0` unless PASIDTT support is advertised and a PASID
TLP prefix is present.

Component coverage adds `AtsTranslatedPasidttDisabledClearsPrefixAttrs`, which
injects translated traffic carrying a SubstreamID plus privileged/instruction
metadata and verifies the resulting `F_TRANSL_FORBIDDEN` EVENTQ record has SSV
clear and SSID zero. This remains a functional slice: advertising PASIDTT=1,
packet-level PASID prefix decoding, MPAM, and full PCIe PASID lifecycle remain
open.

## 2026-05-11 SMMU-COMP-050 EVENTQ fetch-fault word1 progress note

Implemented a follow-up EVENTQ byte-layout slice for non-stall fetch-fault
records. `F_STE_FETCH`, `F_CD_FETCH`, `F_WALK_EABT`, and `F_VMS_FETCH` now use
EVENTQ word1 for the implementation-defined Reason/GPCF field instead of
incorrectly reusing the transaction InputAddr. QBox keeps the implementation
Reason value at zero and preserves the modeled GPCF bit when a fetch fault is
injected with a granule-protection cause; FetchAddr remains encoded in EVENTQ
word3.

Component coverage extends `ArchitectedEventRecordFetchAddressIsEncoded` to
verify `F_STE_FETCH` word1 is zero and `F_CD_FETCH` word1 carries the modeled
GPCF bit while word3 continues to hold FetchAddr. This remains a functional
EVENTQ-layout slice: complete fetch-event Reason values, Secure/Realm routing,
RME/GPT/GPC causality, and upstream Linux event-thread recovery parity remain
open.

## 2026-05-11 SMMU-COMP-050/060 ATS Translated F_STE_FETCH priority progress note

Added an explicit ATS Translated event-priority guard for STE fetch aborts.
When `CR0.SMMUEN==1` and `CR0.ATSCHK==1`, QBox now has component coverage that
an STE memory fetch failure produces `F_STE_FETCH` before STE decode or any
`STE.EATS`-based `F_TRANSL_FORBIDDEN` decision. The same vector verifies the
architectural `CR2.REC_CFG_ATS` gate: without `REC_CFG_ATS` the private fault
status is preserved but no EVENTQ entry is produced, while with `REC_CFG_ATS`
the EVENTQ record contains event `F_STE_FETCH`, Reason word1 zero, and FetchAddr
in word3.

This remains a functional priority slice. Full priority parity still excludes
Secure/Realm cases, `F_VMS_FETCH` priority from actual VMS pointer walks,
configuration-cache conflict detection, DPT/GPC ordering, and upstream Linux
recovery behavior.

## 2026-05-11 SMMU-COMP-050/060 ATS Translated F_VMS_FETCH priority progress note

Implemented a narrow VMS fetch priority slice in the Apollo SMMUv3 TBU. The
model now advertises `FEATURE_ARCH_VMS_FETCH`, decodes a modeled STE.VMSPtr
word for valid nested STEs with S1MPAM set, performs a real memory-backed VMS
fetch, and maps a VMS access abort to `ARCH_FAULT_VMS_FETCH` /
`ARCH_EVENT_F_VMS_FETCH` with FetchAddr in EVENTQ word 3. ATS Translated
traffic checks this modeled VMS fetch before falling through to
`F_TRANSL_FORBIDDEN`, and EVENTQ recording is gated by `SMMU_CR2.REC_CFG_ATS`.
Component coverage is `AtsTranslatedVmsFetchRecordsBeforeForbidden`; durable
verification is recorded in
`doc/verification/qbox-smmuv3-ats-translated-vms-fetch-priority-verification-2026-05-11.md`.

This remains a functional slice, not full SMMUv3 VMS/MPAM compliance: full multi-entry VMS cache
maintenance, full MPAM PARTID_MAP semantics, Secure/Realm
VMS behavior, and upstream Linux recovery parity are still open.

## 2026-05-11 SMMU-COMP-020 CMD_CFGI_VMS_PIDM progress note

Implemented a narrow command-queue maintenance slice for VMS/PARTID_MAP state.
The Apollo SMMUv3 TBU now advertises `FEATURE_ARCH_CFGI_VMS_PIDM`, accepts the
architected `CMD_CFGI_VMS_PIDM` opcode (`0x07`), decodes the VMID operand, and
invalidates the currently modeled VMID-indexed VMS/PARTID_MAP cache state when
the command VMID matches the last fetched VMS state. The existing CFGI_STE and
CFGI_ALL paths also clear the modeled VMS state for the relevant stream/all
scope so stream-indexed VMS data is not left stale.

Component coverage is `CmdqCfgiVmsPidmInvalidatesModeledVmsState`, which proves
that a non-matching VMID leaves the modeled VMS state intact while a matching
VMID clears it and records a CMDQ invalidation without flushing ATS/TLB entries.
This is still a functional cache-maintenance slice: there is not yet a real
multi-entry PARTID_MAP cache, MPAM PARTID remapping, Secure/Realm VMS state, or
upstream Linux command-lifecycle parity.

## 2026-05-11 SMMU-COMP-050 VMS PARTID_MAP progress note

Extended the modeled VMS fetch from a single probe word to a full 64-byte
PARTID_MAP cache-fill. `arch_fetch_vms_if_enabled()` now reads all eight
64-bit words reachable from `STE.VMSPtr`, stores them in
`m_arch_last_vms_partid_map`, and reports `F_VMS_FETCH` at the exact VMS word
address if any memory-backed VMS access aborts. The existing ATS Translated
priority path continues to check VMS fetches before `F_TRANSL_FORBIDDEN`.

Component coverage is `VmsFetchCachesFullPartidMap`, which stages eight VMS
PARTID_MAP words and verifies the TBU cached each word after the modeled VMS
fetch. This is still not full MPAM compliance: virtual-to-physical PARTID
remapping, PMG behavior, multi-VM cache replacement, Secure/Realm state, and
Linux command lifecycle parity remain open.

## 2026-05-11 SMMU-COMP-020/050 MPAM/VMS discovery progress note

Aligned the modeled VMS path with architectural discovery. The Apollo SMMUv3
TBU now sets `SMMU_IDR3.MPAM` while keeping `SMMU_IDR3.DPT` clear, exposes
`SMMU_MPAMIDR` at offset `0x130`, and reports `PARTID_MAX=31` so the modeled
32-entry VMS `PARTID_MAP` has a non-zero Non-secure PARTID space. The Linux
probe's expected `IDR3` value was updated to `0x00000080` so guest-visible ID
register checks remain coherent with the VMS functional slice.

Component coverage is `MpamDiscoveryAdvertisesVmsPrerequisites`, which verifies
`IDR3.MPAM`, `IDR3.DPT==0`, `MPAMIDR.PARTID_MAX`, and the modeled VMS feature
bits. This remains a discovery/coherence slice only: SMMU-originated MPAM
attributes, GMPAM/GBPMPAM programming behavior, physical PARTID remapping into
transactions, Secure/Realm MPAMIDR, and PMG behavior remain open.

## 2026-05-11 SMMU-COMP-020/050 MPAM PARTID_MAP remap progress note

Implemented a follow-up MPAM/VMS functional slice grounded in the local
`sources/smmu` reference material: nested `STE.S1MPAM==1` traffic now decodes
`CD.PARTID`/`CD.PMG`, treats `CD.PARTID[4:0]` as a virtual PARTID for nested
translation, resolves it through the fetched 32-entry `VMS.PARTID_MAP`, and
propagates the resolved physical PARTID plus PMG on the Apollo SMMU TLM
extension during the downstream memory access. The Apollo TBU also exposes
private MPAM status/detail registers for component verification and masks
`STE.S1MPAM` out of the compatibility CD-base decode so the modeled word1 CD
pointer can coexist with the architectural S1MPAM bit.

Validation evidence is recorded in
`doc/verification/qbox-smmuv3-mpam-partid-remap-verification-2026-05-11.md`.
This remains a functional slice rather than full MPAM compliance: STE-sourced
PARTID/PMG assignment, GBPMPAM/GMPAM programming/update semantics,
Secure/Realm MPAM_NS/SP handling, PMG range/UNKNOWN behavior, PMCG filtering,
and full SMMU-originated MPAM attributes remain open.

## 2026-05-11 SMMU-COMP-020/050 STE-sourced MPAM progress note

Implemented the next MPAM functional slice from the local `sources/smmu`
reference material: when `STE.S1MPAM==0`, the Apollo TBU now decodes
`STE.PARTID` from STE word 4 and `STE.PMG` from STE word 5, records the
assignment in the private MPAM status/detail registers, and propagates the
resolved PARTID/PMG on the Apollo SMMU TLM extension for the downstream client
transaction. This covers the architectural fallback path for stage-1 and nested
traffic where stage 1 does not control MPAM.

Validation evidence is recorded in
`doc/verification/qbox-smmuv3-ste-mpam-attrs-verification-2026-05-11.md`.
This remains a functional slice rather than full MPAM compliance: global
bypass `GBPMPAM`, SMMU-originated `GMPAM`, Secure/Realm MPAM_NS/SP selection,
full PMG/UNKNOWN behavior, PMCG filtering, and full MPAM handling for ATS
Translated/PASID cases remain open.

## 2026-05-11 SMMU-COMP-020/050 MPAM range-to-UNKNOWN progress note

Implemented a follow-up MPAM functional slice for architected range handling.
The Apollo TBU now advertises `SMMU_MPAMIDR.PMG_MAX=7`, checks resolved
PARTID and PMG values against the modeled `SMMU_MPAMIDR` limits, and marks
unsupported values as modeled UNKNOWN downstream attributes (`PARTID=0xffff`,
`PMG=0xff`) while keeping the transaction path observable through the existing
MPAM status bits.

Validation evidence is recorded in
`doc/verification/qbox-smmuv3-mpam-range-unknown-verification-2026-05-11.md`.
This remains a functional slice rather than full MPAM compliance: global bypass
`GBPMPAM`, SMMU-originated `GMPAM`, Secure/Realm MPAM_NS/SP selection, PMCG
filtering, and full ATS Translated/PASID MPAM rules remain open.

## 2026-05-11 SMMU-COMP-020/050 GBPMPAM global-bypass progress note

Implemented a follow-up MPAM functional slice for global-bypass client
transactions. The Apollo TBU now exposes `SMMU_GMPAM` and `SMMU_GBPMPAM` at
the architected Non-secure offsets, accepts the `Update` write handshake
synchronously for the modeled PARTID/PMG fields, and assigns
`SMMU_GBPMPAM.GBP_PARTID/GBP_PMG` to downstream client transactions while
`SMMU_CR0.SMMUEN==0`.

Validation evidence is recorded in
`doc/verification/qbox-smmuv3-mpam-gbpmpam-verification-2026-05-11.md`. This
remains a functional slice rather than full MPAM compliance: SMMU-originated
`GMPAM` propagation to queue/STE/MSI/VMS fetches, Secure/Realm MPAM_NS/SP
selection, PMCG filtering, and full ATS Translated/PASID MPAM rules remain
open.

## 2026-05-11 SMMU-COMP-020/050 GMPAM originated-write progress note

Implemented a follow-up MPAM functional slice for modeled SMMU-originated
writes. The Apollo TBU now converts the accepted Non-secure `SMMU_GMPAM`
PARTID/PMG fields into Apollo SMMU TLM MPAM attributes when writing output
queue records (`write_downstream_u64()`) and MSI payloads (`write_downstream_u32()`).
`populate_arch_mpam_extension()` reuses the modeled MPAMIDR range checks so
unsupported PARTID/PMG values continue to become UNKNOWN attributes.

Validation evidence is recorded in
`doc/verification/qbox-smmuv3-mpam-gmpam-verification-2026-05-11.md`. This
remains a functional slice rather than full MPAM compliance: descriptor-fetch
MPAM attribution for STE/CD/VMS reads, Secure/Realm MPAM_NS/SP selection, PMCG
filtering, and full ATS Translated/PASID MPAM rules remain open.

## 2026-05-11 SMMU-COMP-020/050 GMPAM originated-fetch progress note

Implemented the read-side follow-up for modeled SMMU-originated GMPAM
attributes. `read_downstream_u64()` now has an explicit `apply_gmpam` selector,
and the TBU enables it for command-queue entry fetches, two-level stream-table
L1STD fetches, STE fetches, and VMS PARTID_MAP fetches. The selector avoids
blanket-tagging all descriptor reads because the local `sources/smmu` reference
assigns L1CD/CD fetches to STE-sourced MPAM and stage-1/stage-2 translation
table descriptor fetches to client-derived MPAM.

Validation evidence is recorded in
`doc/verification/qbox-smmuv3-mpam-gmpam-fetch-verification-2026-05-11.md`.
This remains a functional slice rather than full MPAM compliance: STE-sourced
MPAM on L1CD/CD fetches, client-derived MPAM on translation-table descriptor
fetches, Secure/Realm MPAM_NS/SP selection, PMCG filtering, and full ATS
Translated/PASID MPAM rules remain open.

## 2026-05-11 SMMU-COMP-020/050 STE-sourced CD fetch progress note

Implemented a follow-up descriptor-fetch MPAM slice for the non-S1MPAM path.
After `record_arch_mpam_from_ste()` resolves `STE.PARTID/STE.PMG`, the TBU can
reuse that resolved state through `populate_arch_mpam_extension_from_state()` on
modeled L1CD/CD fetch reads. The CD fetch path opts in with
`apply_current_mpam` rather than blanket-tagging all descriptor reads, preserving
separate future handling for client-derived translation-table descriptor
fetches.

Validation evidence is recorded in
`doc/verification/qbox-smmuv3-mpam-ste-cd-fetch-verification-2026-05-11.md`.
This remains a functional slice rather than full MPAM compliance: STE-sourced
CD fetch attribution while `STE.S1MPAM==1`, client-derived MPAM on stage-1 and
stage-2 translation-table descriptor fetches, Secure/Realm MPAM_NS/SP
selection, PMCG filtering, and full ATS Translated/PASID MPAM rules remain
open.

## 2026-05-11 SMMU-COMP-020/050 client-derived TT fetch progress note

Implemented a follow-up MPAM descriptor-fetch slice for translation-table
walks. `arch_descriptor_walk()` now opts descriptor reads into
`apply_current_mpam`, causing modeled stage-1 and stage-2 TT descriptor fetches
to carry the currently resolved client MPAM state via the Apollo SMMU TLM
extension. This complements the previous GMPAM and STE/CD fetch slices while
keeping the MPAM source explicit per access class.

Validation evidence is recorded in
`doc/verification/qbox-smmuv3-mpam-tt-fetch-verification-2026-05-11.md`.
This remains a functional slice rather than full MPAM compliance: nested
`STE.S1MPAM==1` CD/VMS-remapped state across all stage-2 helper walks,
Secure/Realm MPAM_NS/SP selection, PMCG filtering, and full ATS
Translated/PASID MPAM rules remain open.

## 2026-05-11 SMMU-COMP-020/050 S1MPAM helper-walk MPAM progress note

Implemented a follow-up MPAM descriptor-fetch slice for `STE.S1MPAM==1` flows.
The TBU now records STE-derived MPAM state before S2-only/S1/nested descriptor
processing, so L1CD/CD fetches and their nested stage-2 helper walks carry
`STE.PARTID/STE.PMG` even when the final client transaction will later use
CD/VMS-derived MPAM. After CD.PARTID/CD.PMG and VMS.PARTID_MAP are available,
`record_arch_mpam_from_cd()` still overrides the current client state so later
translation-table descriptor fetches and final client traffic carry the
CD/VMS-remapped PARTID/PMG.

Validation evidence is recorded in
`doc/verification/qbox-smmuv3-mpam-s1mpam-helper-verification-2026-05-11.md`.
This remains a functional slice rather than full MPAM compliance: Secure/Realm
MPAM_NS/SP selection, PMCG filtering, full ATS Translated/PASID MPAM rules, and
full event/security/RME/GPC/upstream parity remain open.

## 2026-05-11 SMMU-COMP-020/050/060 ATS Translated MPAM progress note

Implemented a narrow ATS Translated MPAM functional slice. The TBU now preserves
the MPAM decision made during `allow_arch_translated_transaction()` across the
subsequent dynamic-map routing step, so downstream Translated payloads can carry
modeled MPAM attributes. `ATSCHK==0` Translated traffic now receives GBPMPAM
PARTID/PMG, and `ATSCHK==1` STE-sourced Translated traffic receives
STE.PARTID/STE.PMG.

Validation evidence is recorded in
`doc/verification/qbox-smmuv3-mpam-ats-translated-verification-2026-05-11.md`.
This remains a functional slice rather than full ATS Translated MPAM compliance:
CD/PASIDTT-dependent MPAM resolution, Secure/Realm MPAM_NS/SP selection, PMCG
filtering, full ATS/PRI protocol parity, and full event/security/RME/GPC/upstream
parity remain open.

## 2026-05-11 SMMU-COMP-020/050/060 ATS Translated CD MPAM progress note

Extended the ATS Translated MPAM slice to cover the modeled stage-1
`STE.S1MPAM==1` path. The TBU now records STE MPAM first so the CD MPAM-word
fetch is attributed to `STE.PARTID/STE.PMG`, then overrides the current
Translated payload MPAM state with `CD.PARTID/CD.PMG` before routing the
downstream payload.

Validation evidence is recorded in the refreshed
`doc/verification/qbox-smmuv3-mpam-ats-translated-verification-2026-05-11.md`.
This remains a functional slice rather than full ATS Translated MPAM compliance:
nested VMS/PASIDTT-dependent MPAM resolution, Secure/Realm MPAM_NS/SP selection,
PMCG filtering, full ATS/PRI protocol parity, and full event/security/RME/GPC/upstream
parity remain open.

## 2026-05-11 SMMU-COMP-020/050 MPAM PARTID-space progress note

Implemented a follow-up MPAM functional slice that explicitly carries the
modeled PARTID-space with MPAM attributes. The Apollo SMMU TLM extension now
includes `mpam_partid_space`, and the TBU records the current QBox
Non-secure-only MPAM state as `ARCH_MPAM_SPACE_NONSECURE` for GBPMPAM, GMPAM,
STE, CD/VMS, TT-fetch, helper-walk, and ATS Translated paths that use the
existing MPAM propagation helpers. `REG_ARCH_MPAM_STATUS` now exposes the last
resolved PARTID-space in bits `[7:6]` so verification can distinguish deliberate
Non-secure modeling from missing security-state data.

Validation evidence is recorded in
`doc/verification/qbox-smmuv3-mpam-partid-space-verification-2026-05-11.md`.
This remains a functional slice rather than full MPAM/security-state
compliance: Secure/Realm execution-state plumbing, MPAM_NS/SP selection, PMCG
filtering, PASIDTT-dependent MPAM resolution, and full event/security/RME/GPC/upstream
parity remain open.

## 2026-05-11 SMMU-COMP-030/050 security-state gate progress note

Implemented a defensive security-state slice for endpoint TLM traffic. The
Apollo SMMU TLM extension now carries `security_state`, and the TBU records the
last observed value through `REG_ARCH_SECURITY_STATUS`. At the time of this slice, the QBox
platform modeled only Non-secure SMMUv3 state, so `arch_security_state_supported()`
accepted `ARCH_SECURITY_NONSECURE` and rejected Secure/Realm/Root-tagged endpoint
transactions before stream-table lookup, dynamic-map lookup, ATS fill, or
downstream data movement. This policy was superseded for Secure endpoint traffic
by the later Secure endpoint acceptance slice below; Realm/Root remain gated. Unsupported security states now produce an
`ARCH_FAULT_UNSUPPORTED_UPSTREAM`/`F_UUT` event instead of being silently treated
as Non-secure traffic. The original component coverage included a Secure/Realm/Root
negative matrix; later endpoint slices keep invalid-state rejection while adding Secure, Realm,
and Root read/debug-read acceptance on the mapped translation path.

Validation evidence is recorded in
`doc/verification/qbox-smmuv3-security-state-gate-verification-2026-05-11.md`.
This remains a functional slice rather than full security-state/RME compliance:
Secure and Realm stream-table banks, Secure/Realm command/event queues,
Root/Realm RME/GPC routing, Secure/Realm MPAM_NS/SP selection, IDE/SEC_SID
packet decoding, and upstream Linux recovery parity remain open.

## 2026-05-11 SMMU-COMP-070 DMA async IRQ signal progress note

Implemented a DMA async IRQ signal slice for the Apollo Hexagon DMA model. The
DMA component now exposes `irq_out`, asserts it when any queue bit is pending in
`REG_IRQ_STATUS`, retains the assertion while another queue remains pending, and
deasserts only after software acknowledges the last pending bit through
`REG_IRQ_ACK`. The Buildroot QBox platform binds the primary and auxiliary DMA
outputs to the Linux-visible doorbell SPIs (`gic_0.spi_in_564` and
`gic_0.spi_in_566`), matching the DTS doorbell interrupt numbers.

Validation evidence is recorded in
`doc/verification/qbox-smmuv3-dma-async-irq-signal-verification-2026-05-11.md`.
This remains a functional slice: the follow-up Linux driver slice now consumes
the doorbell IRQ, but full GIC ordering assertions, MSI lifecycle parity, and
upstream `arm-smmu-v3` interrupt recovery remain open.

## 2026-05-11 SMMU-COMP-070 Linux DMA async IRQ wait progress note

Implemented the guest Linux side of the Apollo Hexagon DMA async fence
doorbell. `apollo-hexagon-test.c` now resolves the named `doorbell` IRQ from the
DTS binding, requests it through `devm_request_irq()`, caches pending IRQ status, acknowledges the level doorbell in the IRQ handler,
completes a reusable `struct completion`, and reinitializes/clears the
per-queue fence before
starting each CNN or SG-DMA job. The wait path now first waits on
`wait_for_completion_timeout()` and only falls back to the prior register-polling
loop on timeout or absent IRQ, preserving compatibility with reduced DTS
fixtures while making the normal QBox path interrupt-driven.

Validation evidence is recorded in
`doc/verification/qbox-smmuv3-linux-dma-irq-wait-verification-2026-05-11.md`.
This remains a functional slice: the QBox guest smoke now captures the new
`async fence irq wait` marker for both SG-DMA and CNN queues, while formal GIC
ordering/coalescing assertions, MSI lifecycle parity, and upstream
`arm-smmu-v3` interrupt recovery remain open.

## 2026-05-11 SMMU-COMP-050 security-state EVENTQ routing progress note

Implemented a narrow security-state EVENTQ routing/accounting slice. The Apollo
TBU now tags each committed modeled EVENTQ record with the current endpoint
security state, exposes the last routed EVENTQ security state through
`REG_ARCH_SECURITY_STATUS`, and accounts Non-secure, Secure, Realm, and Root
EVENTQ records separately. The then-current Secure/Realm/Root unsupported upstream
transaction coverage verified that each rejected `F_UUT` EVENTQ record was
accounted against the matching security-state route. The later Secure endpoint
acceptance slice keeps Realm/Root rejected-event accounting and moves Secure
endpoint traffic onto the mapped translation/fault path.

This narrows the Secure/Realm event routing blocker but remains a functional
slice rather than full security-state banking: separate Secure/Non-secure event
queue memories, secure stream-table banks, `NSCFG`/`S_S2TTB` selection, RME/GPT
routing, and upstream Linux recovery parity remain open. Evidence is recorded in
`doc/verification/qbox-smmuv3-security-eventq-routing-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-050 security-state stalled EVENTQ buffer route progress note

Implemented a narrow stalled EVENTQ redrive correctness slice. Buffered stalled
EVENTQ records now retain the event's original modeled security state alongside
the record words. When software advances EVENTQ_CONS and the record is redriven,
route accounting uses the buffered security state rather than whichever endpoint
security state happens to be current at redrive time. The component test covers a
Realm-tagged buffered stalled fault followed by a Non-secure current-state change
before redrive.

This narrows the Secure/Realm event routing blocker but remains a functional
slice: separate Secure/Non-secure event queue memories, secure stream-table
banks, NSCFG/S_S2TTB selection, full RME/GPT routing, and upstream arm-smmu-v3
recovery parity remain open. Evidence is recorded in
`doc/verification/qbox-smmuv3-security-stall-event-buffer-route-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-050 security-state EVENTQ bank mirror progress note

Implemented a narrow per-security-state EVENTQ bank mirror slice. The Apollo TBU
now snapshots each committed modeled EVENTQ record into a logical bank keyed by
Non-secure, Secure, Realm, or Root security state, including record words, guest
record address, producer/consumer snapshot, and per-bank record count. Existing historical
Secure/Realm/Root `F_UUT` rejected-event coverage and the stalled EVENTQ redrive
coverage verified that the mirrored bank followed the event security state rather
than ambient current state. The later Secure endpoint acceptance slice preserves
Realm/Root `F_UUT` coverage and uses Secure translation faults for Secure-bank
routing coverage.

This narrows the Secure/Realm event-routing blocker but remains a functional
slice: true separate Secure/Non-secure EVENTQ memory banks, secure stream-table
banks, NSCFG/S_S2TTB selection, full RME/GPT routing, complete event matrix
parity, and upstream arm-smmu-v3 recovery parity remain open. Evidence is
recorded in
`doc/verification/qbox-smmuv3-security-eventq-bank-mirror-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-050 configured Secure EVENTQ bank route progress note

Implemented a follow-up security-state EVENTQ routing slice. The Apollo TBU now
lets the model configure a per-security-state EVENTQ bank, selects that queue for
Secure/Realm/Root event routes when configured, and preserves the previous
Non-secure EVENTQ fallback when no separate bank exists. Component coverage
`SecureEventsUseConfiguredEventqBank` now verifies a Secure translation fault
emits `F_TRANSLATION` into the configured Secure queue bank, leaves the
Non-secure `m_eventq` producer unchanged, and marks the bank as routed
separately. Earlier revisions of this slice used Secure `F_UUT` rejection; that
was superseded once modeled Secure endpoint traffic became accepted.

This narrows the previous logical-bank-only gap, but is still not full Secure
SMMUv3/RME support. Guest-visible Secure queue register banking,
Secure/Non-secure stream-table banking, `NSCFG` and `S2TTB` versus `S_S2TTB`
selection, full RME/GPT/GPC behavior, full event matrix parity, and upstream
Linux event-thread recovery remain open. Evidence is recorded in
`doc/verification/qbox-smmuv3-secure-eventq-bank-route-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-030 Secure STRTAB bank selection progress note

Implemented a modeled Secure stream-table banking slice. The Apollo TBU now has
a per-security-state STRTAB bank record and can select a configured Secure
`STRTAB_BASE/STRTAB_BASE_CFG` pair when the active modeled security state is
Secure. Component coverage `SecureStreamTableBankSelectsSecureSte` verifies a
Secure probe reads the Secure STE/CD path while a Non-secure probe still reads
the existing Non-secure STRTAB path.

This narrows Secure/Non-secure stream-table banking from a missing feature to a
modeled component slice only. Guest-visible Secure register banking, Secure
endpoint acceptance policy, `NSCFG` and `S2TTB` versus `S_S2TTB` selection, full
RME/GPT/GPC behavior, complete event matrix priority, and upstream Linux
`arm-smmu-v3` lifecycle parity remain open. Evidence is recorded in
`doc/verification/qbox-smmuv3-secure-strtab-bank-verification-2026-05-11.md`.


## 2026-05-11 SMMU-COMP-030/040 Secure S2TTB/NSCFG selection progress note

Implemented a focused Secure stage-2 table selection slice. The Apollo TBU now
models `STE.NSCFG` for Secure stage-2-only and S1DSS-bypass paths and selects
`STE.S_S2TTB` when the modeled Secure stream resolves the input as Secure IPA,
while preserving `STE.S2TTB` selection for Non-secure IPA. Component coverage
`SecureStage2OnlyUsesSS2TtbWhenNscfgSecure` verifies both table-base choices for
a configured Secure stream-table probe.

This narrows the `NSCFG`/`S_S2TTB` blocker to a modeled component slice only.
Guest-visible Secure register banking, stage-1-derived Secure IPA-space
selection, full complete RME/GPT/GPC endpoint policy, RME/GPT/GPC behavior,
complete event matrix priority, and upstream Linux `arm-smmu-v3` lifecycle parity
remain open. Evidence is recorded in
`doc/verification/qbox-smmuv3-secure-s2ttb-nscfg-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-030/040 Secure stage-1-derived NSIPA selection progress note

Implemented a focused Secure nested stage-1-derived IPA-space selection slice.
The Apollo TBU now models `CD.NSCFG0`, stage-1 table descriptor `NSTable`, and
leaf descriptor `NS` as inputs to the Secure stage-1 output NS attribute, then
uses that derived IPA space to choose `STE.S_S2TTB` for Secure IPA or `STE.S2TTB`
for Non-secure IPA on the final nested stage-2 translation. Component coverage
`SecureNestedStage1OutputNsSelectsS2Ttb` verifies Secure leaf `NS=0`, leaf
`NS=1`, and `CD.NSCFG0=1` cases against distinct Secure/Non-secure stage-2 table
roots.

This narrows the previous stage-1-derived Secure IPA-space blocker to a modeled
component slice. Guest-visible Secure register banking, full Secure endpoint
acceptance policy, stage-1 translation-table fetch Secure IPA-space table
selection, full RME/GPT/GPC behavior, complete event matrix priority/parity, and
upstream Linux `arm-smmu-v3` lifecycle parity remain open. Evidence is recorded
in `doc/verification/qbox-smmuv3-secure-stage1-nsipa-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-030/040 Secure stage-1 TT-fetch table selection progress note

Implemented a follow-up Secure nested stage-1 translation-table descriptor fetch
slice. The Apollo TBU now reads `STE.S_S2TTB` for Secure nested S1+S2 streams
whose current stage-1 table-walk IPA space is Secure, records the last TT-fetch
IPA-space/table-root choice, and selects normal `STE.S2TTB` once `CD.NSCFG0` or
`NSTable` makes the stage-1 table walk Non-secure. Component coverage extends
`SecureNestedStage1OutputNsSelectsS2Ttb` to assert Secure TT fetches use
`S_S2TTB` and `CD.NSCFG0=1` TT fetches use `S2TTB`.

This closes the previous modeled stage-1 TT-fetch Secure IPA-space table
selection blocker, but still does not claim full SMMUv3 compliance. Guest-visible
Secure register banking, full complete RME/GPT/GPC endpoint policy,
RME/GPT/GPC behavior, complete event matrix priority/parity, full Arm reference
vector coverage, and upstream Linux `arm-smmu-v3` lifecycle parity remain open.
Evidence is recorded in
`doc/verification/qbox-smmuv3-secure-stage1-ttfetch-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-020/030 Secure register bank progress note

Implemented a guest-visible Secure programming-interface register-bank slice.
The Apollo TBU SMMUv3 aperture now includes the architected SMMU_S_* page at
PAGE_0 + `0x8000`, advertises `SMMU_S_IDR1.SECURE_IMPL` and `SEL2`, and routes
`SMMU_S_STRTAB_BASE{,_CFG}`, `SMMU_S_CMDQ_*`, and `SMMU_S_EVENTQ_*` accesses to
independent Secure STRTAB/CMDQ/EVENTQ bank state. The QBox Buildroot platform
TBU MMIO windows are expanded to `0x10000` so the Secure page is no longer only
a helper-only component path.

Component coverage `SecureRegisterBankConfiguresStrtabCmdqAndEventq`,
`SecureStreamTableBankSelectsSecureSte`, and `SecureEventsUseConfiguredEventqBank`
proves guest-visible Secure STRTAB/EVENTQ programming and Non-secure register
isolation. This closes the previous guest-visible Secure register-banking
blocker for the modeled slice, but full Secure command-queue lifecycle, full
complete RME/GPT/GPC endpoint policy, RME/GPT/GPC, complete event-matrix
parity, full Arm reference-vector coverage, and upstream `arm-smmu-v3` lifecycle
parity remain open. Evidence is recorded in
`doc/verification/qbox-smmuv3-secure-register-bank-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-020 Secure CMDQ progress note

Implemented a memory-backed Secure command-queue consumption slice for the
SMMU_S_* programming interface. `SMMU_S_CMDQ_PROD` now fetches and consumes
Secure queue entries when `SMMU_S_CR0.SMMUEN|CMDQEN` is acknowledged, keeps
Secure CMDQ consumer/error state separate from the Non-secure CMDQ, and reuses
modeled handlers for selected commands such as `CMD_SYNC` and `CMD_ATC_INV`.

Component coverage `SecureCmdqProducerConsumesMemoryBackedCommands` verifies
Secure CR0 gating, memory-backed command consumption, ATS invalidation from a
Secure `CMD_ATC_INV`, and Non-secure CMDQ state isolation. This narrows the
previous Secure CMDQ blocker to a selected-command lifecycle slice only.
Complete Secure command lifecycle parity, SSec/security-state command
parameters, Secure queue-error recovery ordering, complete RME/GPT/GPC endpoint
policy, RME/GPT/GPC, complete event-matrix parity, full Arm reference-vector
coverage, and upstream `arm-smmu-v3` lifecycle parity remain open. Evidence is
recorded in `doc/verification/qbox-smmuv3-secure-cmdq-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-020 Secure CMDQ error-recovery progress note

Extended the Secure command-queue slice with modeled ATC invalidation completion
error ordering. Secure `CMD_ATC_INV` completion failures now coalesce and report
`S_CMDQ_CONS.CERROR_ATC_INV_SYNC` on the following Secure `CMD_SYNC`, leave
`S_CMDQ_CONS.RD` at the failing sync, pause further Secure command consumption
while the error is live, and resume only after software advances `S_CMDQ_CONS`.
Component coverage `SecureCmdqAtcInvSyncCerrorPausesAndRecovers` verifies the
pause/skip/recovery ordering and Non-secure CMDQ consumer isolation.

This narrows the Secure command lifecycle blocker for ATC_INV_SYNC error
ordering only. Remaining Secure command encodings, SSec/security-state command
parameters, broader Secure queue-error recovery, Secure IRQ/MSI ordering, full
complete RME/GPT/GPC endpoint policy, RME/GPT/GPC, full event matrix/reference
vectors, and upstream `arm-smmu-v3` lifecycle parity remain open. Evidence is
recorded in `doc/verification/qbox-smmuv3-secure-cmdq-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-020 Secure CMD_SYNC MSI progress note

Extended the Secure command-queue slice with modeled `CMD_SYNC CS=IRQ` MSI
ordering. Secure `CMD_SYNC` now follows the Non-secure command-queue MSI order
for the covered path: zero MSI addresses are ignored, successful downstream
writes are recorded as `ARCH_IRQ_CMDQ_SYNC`, failed writes increment MSI abort
accounting and raise `S_GERROR.MSI_CMDQ_ABORT`, `S_GERRORN` acknowledges the
active Secure GERROR bit, and Non-secure GERROR remains isolated. Component
coverage `SecureCmdSyncMsiWriteAndAbortAreReported` verifies successful MSI
writes, failed MSI aborts, Secure GERROR acknowledgement, shared modeled IRQ
status, and Non-secure GERROR isolation.

This narrows the Secure IRQ/MSI blocker for Secure `CMD_SYNC CS=IRQ` only.
Remaining Secure command encodings, SSec/security-state command parameters,
broader Secure queue-error recovery, Secure IRQ/MSI ordering beyond the modeled
CMD_SYNC MSI path, full complete RME/GPT/GPC endpoint policy, RME/GPT/GPC, full
event matrix/reference vectors, and upstream `arm-smmu-v3` lifecycle parity
remain open. Evidence is recorded in
`doc/verification/qbox-smmuv3-secure-cmdq-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-070 Secure EVENTQ MSI progress note

Implemented a narrow Secure EVENTQ IRQ/MSI routing slice. Secure EVENTQ records
that use a configured `SMMU_S_EVENTQ_*` bank now select Secure IRQ state,
programmed `SMMU_S_EVENTQ_IRQ_CFG{0,1,2}` MSI payloads, and `S_GERROR` for
failed Secure EVENTQ MSI writes. Component coverage is provided by
`SecureEventqMsiAndAbortUseSecureBank`, which also verifies Non-secure
EVENTQ/GERROR isolation and `S_GERRORN` acknowledgement.

This remains a functional slice rather than full IRQ/MSI compliance: full
wired/MSI ordering, coalescing, Secure/Realm interrupt bank parity, PCIe/GIC MSI
routing, and upstream `arm-smmu-v3` lifecycle parity remain open.

## 2026-05-11 SMMU-COMP-070 Secure GERROR MSI progress note

Implemented a narrow Secure GERROR IRQ/MSI routing slice. Secure GERROR sources
now use `SMMU_S_GERROR_IRQ_CFG{0,1,2}` for MSI delivery when the Secure GERROR
IRQ bank is enabled, and failed Secure GERROR MSI writes set
`S_GERROR.MSI_GERROR_ABORT` without mutating the Non-secure GERROR bank.
Component coverage is provided by `SecureGerrorMsiAndAbortUseSecureBank`, which
also verifies Secure `S_GERRORN` acknowledgement and Non-secure GERROR isolation.

This remains a functional slice rather than full IRQ/MSI compliance: full
wired/MSI ordering, coalescing, Secure/Realm interrupt bank parity, PCIe/GIC MSI
routing, and upstream `arm-smmu-v3` lifecycle parity remain open.

## 2026-05-11 SMMU-COMP-070 Secure CMD_SYNC IRQ bank progress note

Implemented a narrow Secure `S_CMD_SYNC` wired IRQ visibility slice. Secure
command-sync completion now records Secure IRQ-bank state and uses
`SMMU_S_IRQ_CTRL/SMMU_S_IRQ_CTRLACK` to expose the modeled `CMDQ_SYNC` line,
rather than letting Non-secure `SMMU_IRQ_CTRL` expose Secure command completion.
Component coverage is provided by `SecureCmdSyncIrqUsesSecureCtrlBank`.

This remains a functional slice rather than full IRQ/MSI compliance: full
wired/MSI ordering, coalescing, Secure/Realm interrupt bank parity, PCIe/GIC MSI
routing, and upstream `arm-smmu-v3` lifecycle parity remain open.

## 2026-05-11 SMMU-COMP-070 Secure PRIQ MSI progress note

Implemented a narrow Secure PRIQ IRQ/MSI routing slice. Secure PRIQ records can
now target `SMMU_S_PRIQ_*` state, use `SMMU_S_IRQ_CTRL` and
`SMMU_S_PRIQ_IRQ_CFG{0,1,2}` for MSI delivery, and report failed Secure PRIQ MSI
writes through `S_GERROR.MSI_PRIQ_ABORT` without mutating Non-secure PRIQ/GERROR
state. Component coverage is provided by `SecurePriqMsiAndAbortUseSecureBank`.

This remains a functional slice rather than full IRQ/MSI or PRI compliance: full
wired/MSI ordering, coalescing, Secure/Realm interrupt bank parity, byte-exact
PCIe PRI packet semantics, PCIe/GIC MSI routing, and upstream `arm-smmu-v3`
lifecycle parity remain open.

## 2026-05-11 SMMU-COMP-020 Secure CMDQ SSec CFGI progress note

Implemented a focused Secure command-parameter slice. The Apollo TBU now decodes
an architected `SSec` bit for modeled command-queue entries, routes Secure CMDQ
CFGI invalidation to Secure configuration-cache state when `SSec=1`, routes it
to Non-secure state when `SSec=0`, and reports `CMDQ_CONS.CERROR_ILL` if the
Non-secure CMDQ attempts a CFGI command with `SSec=1`. Component coverage is
provided by `SecureCmdqSsecCfgiTargetsSelectedSecurityState` and
`NonSecureCmdqSsecCfgiIsIllegal`.

This narrows the Secure command security-state-parameter blocker for CFGI only.
Remaining Secure command encodings and SSec/security-state parameters, exact
range/leaf/reference-vector parity, full complete RME/GPT/GPC endpoint policy,
RME/GPT/GPC behavior, complete event-matrix parity, and upstream `arm-smmu-v3`
lifecycle parity remain open. Evidence is recorded in
`doc/verification/qbox-smmuv3-secure-cmdq-ssec-cfgi-verification-2026-05-11.md`.

### 2026-05-11 SMMU-COMP-020 Secure CMDQ SSec TLBI/ATC progress note

- Extended the modeled SSec command-parameter slice beyond CFGI by tagging
  Apollo TBU ATS/TLB cache entries with a security state and filtering modeled
  `TLBI_NH_*`/`ATC_INV` invalidation by the Secure CMDQ `SSec` selector.
- Added Non-secure CMDQ misuse coverage for `TLBI_NH_*` and `ATC_INV` with
  `SSec=1`, preserving Secure ATS/TLB state and reporting `CERROR_ILL` without
  consuming the failing command.
- Verification evidence is recorded in
  `doc/verification/qbox-smmuv3-secure-cmdq-ssec-tlbi-atc-verification-2026-05-11.md`.
- Remaining blocker: this is still not full SMMUv3 command compliance; unmodeled
  command encodings, exact Arm range/leaf/reference-vector parity, Secure/Realm
  endpoint acceptance, complete event matrix, RME/GPT/GPC, and upstream
  `arm-smmu-v3` lifecycle parity remain open.


### 2026-05-11 SMMU-COMP-020/040 TLBI range progress note

- Implemented a focused address-based TLBI range invalidation slice in the
  Apollo TBU. Modeled `TLBI_NH_VA` and `TLBI_NH_VAA` commands now decode
  `NUM`, `SCALE`, and `TG` into byte ranges and invalidate ASID/VMID- or
  VMID-qualified ATS/TLB cache entries across the selected span rather than
  only the base page.
- Added component coverage with `CmdqTlbiRangeInvalidatesModeledAtsSpan`,
  including preservation of out-of-range entries and non-matching VMID entries.
- Verification evidence is recorded in
  `doc/verification/qbox-smmuv3-tlbi-range-verification-2026-05-11.md`.
- Remaining blocker: this is still a modeled range slice, not full SMMUv3 TLBI
  parity. Leaf/TTL/RIL and reserved-field behavior, additional TLBI encodings,
  complete Arm reference-vector parity, complete RME/GPT/GPC endpoint policy, the
  complete event matrix, RME/GPT/GPC, and upstream `arm-smmu-v3` lifecycle
  parity remain open.


### 2026-05-11 SMMU-COMP-020/040 TLBI range reserved-encoding progress note

- Implemented the architected reserved-encoding guard for modeled address-based
  TLBI range commands: `TG != 0`, `NUM == 0`, and `SCALE == 0` now raises
  `CERROR_ILL` instead of being treated as a one-page range.
- Covered both Non-secure and Secure command queues with
  `CmdqTlbiRangeReservedEncodingIsIllegal`, preserving ATS/TLB entries and
  leaving the queue at the failing command.
- Verification evidence is recorded in
  `doc/verification/qbox-smmuv3-tlbi-range-reserved-verification-2026-05-11.md`.
- Remaining blocker: TTL/Leaf/RIL interactions, additional TLBI opcodes, full
  Arm reference-vector parity, complete RME/GPT/GPC endpoint policy, complete event
  matrix, RME/GPT/GPC, and upstream `arm-smmu-v3` lifecycle parity remain open.


### 2026-05-11 SMMU-COMP-020/040 TLBI TTL/Leaf progress note

- Implemented modeled address-based TLBI `TTL` and `Leaf` hint decoding in the
  Apollo TBU, alongside the existing `NUM`/`SCALE`/`TG` range decoder.
- Added `CmdqTlbiTtlLeafHintsFollowRangeTg` coverage for both a ranged TLBI
  with `TG=4K`, `TTL!=0`, `Leaf=1` and a `TG=0` single-page TLBI where the
  effective TTL hint is suppressed while the Leaf hint remains observable.
- Verification evidence is recorded in
  `doc/verification/qbox-smmuv3-tlbi-ttl-leaf-verification-2026-05-11.md`.
- Follow-up note below supersedes the hint-accounting-only limitation with a
  modeled level-aware TTL/TG invalidation slice. RIL advertisement with Linux
  range-command stress, additional TLBI opcodes, full Arm reference-vector
  parity, complete RME/GPT/GPC endpoint policy, complete event matrix, RME/GPT/GPC,
  and upstream `arm-smmu-v3` lifecycle parity remain open.

### 2026-05-11 SMMU-COMP-020/040 TLBI TTL/Leaf level-aware progress note

- Extended the modeled ATS/TLB cache entries with leaf-level and translation
  granule metadata so address-based TLBI commands can use the decoded `TTL` and
  `TG` hints as an invalidation filter instead of only recording them.
- `TLBI_NH_VA`/`TLBI_NH_VAA` now preserve matching ASID/VMID entries whose
  cached leaf level does not match a non-zero effective TTL, while `TG == 0`
  continues to suppress TTL filtering and invalidates the addressed page.
- Added modeled `Leaf == 0` table-walk cache invalidation accounting via
  `m_arch_last_cmd_table_invalidated`/`m_arch_cmd_table_invalidations`, keeping
  the leaf translation invalidation count separate from table-descriptor cache
  effects.
- Strengthened `CmdqTlbiTtlLeafHintsFollowRangeTg` to cover level-mismatch
  preservation, `TG == 0` TTL suppression, and `Leaf == 0` table-cache
  accounting. Evidence is recorded in
  `doc/verification/qbox-smmuv3-tlbi-level-verification-2026-05-11.md`.
- Remaining blocker at this point was RIL advertisement with Linux
  range-command stress plus additional TLBI opcodes/security-state encodings,
  byte-exact Arm reference vectors for all TTL/Leaf combinations, Secure/Realm
  endpoint acceptance, complete event matrix, RME/GPT/GPC, and upstream
  `arm-smmu-v3` lifecycle parity. The follow-up RIL note below supersedes the
  RIL-advertisement/Linux-stress portion only.

### 2026-05-11 SMMU-COMP-020/040/080 IDR3.RIL Linux range-command progress note

- Advertised modeled range invalidation support through `SMMU_IDR3.RIL` bit 10
  while retaining the existing MPAM discovery bit and leaving `IDR3.DPT` clear.
- Updated the Linux Apollo Hexagon probe expectation to `IDR3=0x00000480` and
  added a guest-driven `CMD_TLBI_NH_VA` RIL command in the >64KB SG DMA stress
  path.  The command uses `TG=4K`, `NUM=31`, and `Leaf=1`, then validates CMDQ
  consumption, last opcode, and a non-zero modeled invalidation count.
- The QBox Hexagon guest smoke now requires the Linux marker
  `SMMUv3 RIL TLBI_NH_VA range selftest ok`; the verified run invalidated 32
  modeled ATS/TLB entries after SG DMA cache population and still produced the
  expected IREE tiny-CNN tensor output.
- Evidence is recorded in
  `doc/verification/qbox-smmuv3-ril-range-verification-2026-05-11.md`.
- Remaining blocker: this closes the prior RIL-advertisement/Linux-stress gap,
  but does not claim byte-exact Arm TLBI parity. Additional TLBI opcodes
  were completed by the follow-up note below; security-state encodings, full
  TTL/Leaf/RIL reference-vector matrices,
  complete RME/GPT/GPC endpoint policy, complete event-matrix coverage, RME/GPT/GPC,
  and upstream `arm-smmu-v3` lifecycle parity remain open.


### 2026-05-11 SMMU-COMP-020/040 additional TLBI opcode progress note

- Added modeled command-queue support for the remaining Non-secure/Common TLBI
  command forms covered by the local SMMUv3 reference: `CMD_TLBI_EL3_ALL`,
  `CMD_TLBI_EL3_VA`, `CMD_TLBI_EL2_ALL`, `CMD_TLBI_EL2_ASID`,
  `CMD_TLBI_EL2_VA`, `CMD_TLBI_EL2_VAA`, `CMD_TLBI_S12_VMALL`,
  `CMD_TLBI_S2_IPA`, and `CMD_TLBI_NSNH_ALL`.
- Added `cmdq_opcode_is_address_tlbi()` so range reserved-field validation and
  range invalidation cover the expanded address-based TLBI set instead of only
  `TLBI_NH_VA`/`TLBI_NH_VAA`.
- Added `CmdqAdditionalTlbiOpcodesInvalidateModeledAts` component coverage for
  representative NSNH all-scope, S12 VMID, S2 IPA range, EL2 ASID, and EL2 VAA
  range invalidation side effects.
- Evidence is recorded in
  `doc/verification/qbox-smmuv3-additional-tlbi-opcodes-verification-2026-05-11.md`.
- Remaining blocker: this closes the modeled additional-TLBI-opcode gap, but it
  does not claim byte-exact Arm TLBI parity. Security-state encodings for the
  remaining Secure/Realm command variants, full TTL/Leaf/RIL reference-vector
  matrices, complete RME/GPT/GPC endpoint policy, complete event-matrix coverage,
  RME/GPT/GPC, and upstream `arm-smmu-v3` lifecycle parity remain open.

### 2026-05-11 SMMU-COMP-020/040 Secure-only TLBI opcode progress note

- Added modeled command-queue support for Secure-only TLBI command forms from the
  local SMMUv3 reference: `CMD_TLBI_S_EL2_ALL`, `CMD_TLBI_S_EL2_ASID`,
  `CMD_TLBI_S_EL2_VA`, `CMD_TLBI_S_EL2_VAA`, `CMD_TLBI_S_S12_VMALL`,
  `CMD_TLBI_S_S2_IPA`, and `CMD_TLBI_SNH_ALL`.
- Added `cmdq_opcode_is_secure_tlbi()` so Secure-only TLBI commands are rejected
  with `CERROR_ILL` on the Non-secure CMDQ and are forced to Secure-state
  targeting on the Secure CMDQ instead of depending on the shared-command `SSec`
  bit.
- Added `SecureOnlyTlbiOpcodesRequireSecureCmdqAndTargetSecureState` coverage for
  Non-secure rejection plus Secure ASID, Secure S2 IPA range, and Secure NH
  all-scope invalidation side effects.
- Evidence is recorded in
  `doc/verification/qbox-smmuv3-secure-tlbi-opcodes-verification-2026-05-11.md`.
- Remaining blocker: this closes the modeled Secure-only TLBI opcode gap, but it
  does not claim full security-state/RME parity. Realm/RME command encodings,
  GPT/GPC behavior, full TLBI TTL/Leaf/RIL reference-vector matrices,
  complete RME/GPT/GPC endpoint policy, complete event-matrix coverage, and upstream
  `arm-smmu-v3` lifecycle parity remain open.

### 2026-05-11 SMMU-COMP-030/050 Secure/Realm/Root endpoint acceptance progress note

- Changed the endpoint security-state gate so `ARCH_SECURITY_SECURE`,
  `ARCH_SECURITY_REALM`, and `ARCH_SECURITY_ROOT` are accepted on the existing
  mapped translation path alongside Non-secure traffic.
- Invalid security-state endpoint traffic remains rejected before translation
  with the existing unsupported-upstream/F_UUT event route.
- Updated component coverage from the earlier all-non-Non-secure rejection test
  to `SecureRealmRootEndpointAcceptedInvalidRejectedBeforeTranslation`, which
  verifies Secure/Realm/Root read/debug-read success and invalid-state
  event-record rejection.
- Evidence is recorded in
  `doc/verification/qbox-smmuv3-secure-endpoint-acceptance-verification-2026-05-11.md`.
- Remaining blocker: this closes modeled four-state endpoint acceptance, but
  complete Realm/Root GPT walks/checks, GPC fault causality, complete event
  matrix coverage, and upstream `arm-smmu-v3` lifecycle parity remain open.

### 2026-05-11 SMMU-COMP-020/050 MPAM security PARTID-space progress note

Implemented a focused MPAM security-state slice in `apollo_smmu_tbu`:

- Added `arch_mpam_partid_space_for_security_state()` so modeled MPAM
  attributes derive PARTID-space from endpoint security state instead of always
  using Non-secure.
- Applied the derived PARTID-space to GBPMPAM, STE-derived MPAM,
  CD/VMS-remapped MPAM, and GMPAM-originated attribute propagation.
- Added `MpamAttributesCarrySecurityPartidSpace`, which verifies downstream TLM
  extension propagation and `REG_ARCH_MPAM_STATUS` reporting for Non-secure,
  Secure, Realm, and Root endpoint transactions.
- Verification is recorded in
  `doc/verification/qbox-smmuv3-mpam-security-partid-space-verification-2026-05-11.md`
  with build, focused gTest/CTest, static checker, lane, and final closure logs.

Remaining blocker: this closes the modeled Non-secure-only MPAM PARTID-space
slice, but it is not full MPAM/RME/GPT/GPC compliance. Complete Realm/Root
GPT/GPC policy, Secure/Realm MPAMIDR banking, packet-level ATS/PRI parity, and
upstream `arm-smmu-v3` lifecycle parity remain open.

### 2026-05-11 SMMU-COMP-020/050 Secure MPAM register-bank progress note

Implemented a focused Secure MPAM register-bank slice in `apollo_smmu_tbu`:

- Added `arch_gbpmpam_for_security_state()` so modeled Secure endpoint client
  traffic uses `SMMU_S_GBPMPAM`, while the current Non-secure/Realm/Root
  fallback path continues to use `SMMU_GBPMPAM` until the full RME bank model is
  implemented.
- Added `arch_gmpam_for_security_state()` so modeled Secure SMMU-originated
  descriptor/queue/MSI attributes use `SMMU_S_GMPAM`.
- Added `SecureMpamRegisterBanksDriveAttributes`, verifying Secure GBPMPAM and
  GMPAM attributes are propagated into downstream TLM extensions with Secure
  PARTID-space tagging.
- Verification is recorded in
  `doc/verification/qbox-smmuv3-secure-mpam-register-bank-verification-2026-05-11.md`
  with build, focused gTest/CTest, static checker, lane, and final closure logs.

Remaining blocker: Realm/Root MPAMIDR/GPT/GPC banking, full SMMU-originated
transaction ordering, packet-level ATS/PRI parity, and upstream `arm-smmu-v3`
lifecycle parity remain open.

### 2026-05-11 SMMU-COMP-020/040 TLBI_NSNH_ALL scope progress note

Implemented a focused TLBI reference-vector parity slice for modeled
`CMD_TLBI_NSNH_ALL` invalidation scope:

- Added modeled ATS cache TLBI-regime tags (`ARCH_TLBI_REGIME_NSNH` and
  `ARCH_TLBI_REGIME_EL2`) so tests can distinguish Non-secure Non-Hyp cache
  entries from EL2-regime entries.
- Routed `CMD_TLBI_NSNH_ALL` through `clear_ats_cache_nsnh()` instead of the
  blanket `clear_ats_cache()` helper, preserving explicitly tagged EL2-regime
  entries.
- Added `CmdqTlbiNsnhAllPreservesEl2RegimeEntries`, verifying one NSNH entry is
  invalidated while an EL2-regime entry with the same ASID/VMID remains valid.
- Verification is recorded in
  `doc/verification/qbox-smmuv3-tlbi-nsnh-scope-verification-2026-05-11.md`
  with build, focused gTest/CTest, static checker, and lane logs.

Remaining blocker: this is a modeled command-scope slice, not full TLBI or
stream-world compliance. Real stream-world derivation from STE/CD/security state,
full TTL/Leaf/RIL reference-vector matrices, Realm/RME command encodings,
GPT/GPC behavior, and upstream `arm-smmu-v3` lifecycle parity remain open.

### 2026-05-11 SMMU-COMP-030/050 STE.S2R/S2S stage-2 fault-policy progress note

Implemented a focused reference-backed stage-2 fault record/stall policy slice
based on the pinned `sources/smmu/bugs/newBugs24Mar2026_7pm.md` BUG-QA-12 and
BUG-QA-13 findings:

- Added modeled `ARCH_STE_S2R` and `ARCH_STE_S2S` bits to STE word 1.
- Added `apply_arch_stage2_fault_policy()` so stage-2 faults suppress EVENTQ
  records when `S2R=0 && S2S=0`, record non-stall faults when `S2R=1`, and
  record stalled faults when `S2S=1`.
- Routed stage-2-only and nested CD/L1CD/TT-fetch/final S2 failure paths through
  the policy before probe or negative-replay event emission.
- Added `Stage2SteS2rS2sControlsRecordAndStall` and kept existing nested
  stage-2 negative replay vectors explicit by setting STE.S2S where those tests
  expect stalled records.
- Verification is recorded in
  `doc/verification/qbox-smmuv3-ste-s2r-s2s-verification-2026-05-11.md` with
  build, focused gTest/CTest, static checker, lane, final closure, and
  checkpoint logs.

Remaining blocker: this closes only the modeled STE.S2R/S2S record/stall slice.
STALL_MODEL validation, complete event-record parity across all stage-2 causes,
full RME/GPT/GPC policy, packet-level ATS/PRI behavior, and upstream
`arm-smmu-v3` lifecycle parity remain open.

### 2026-05-11 SMMU-COMP-030/050 STE.S2S terminate-only STALL_MODEL progress note

Implemented a focused reference-backed follow-up to the prior STE.S2R/S2S
stage-2 record/stall slice based on `sources/smmu/bugs/newBugs24Mar2026_7pm.md`
BUG-QA-12 and the reference tests in
`sources/smmu/cpp/tests/unit/test_bugs_qa_11_12_13_14.cpp`:

- Added a modeled `ARCH_STALL_MODEL_TERMINATE_ONLY` control and default
  stall-capable model to preserve existing STE.S2S stall behavior.
- Added `arch_ste_stage2_enabled()` and
  `arch_stall_model_terminates_stage2_stalls()` so validation is restricted to
  stage-2-enabled STE configurations.
- Rejected `STALL_MODEL==terminate-only && STE.S2S==1` as
  `ARCH_FAULT_STE_INVALID` / `C_BAD_STE` before stage-2 walks.
- Added `SteS2sRejectedWhenStallModelTerminateOnly`, which also proves the
  stage-2 guard by accepting a non-stage-2 STE that carries the S2S bit.
- Verification is recorded in
  `doc/verification/qbox-smmuv3-ste-s2s-stall-model-verification-2026-05-11.md`
  with build, focused gTest/CTest, static checker, lane, and closure evidence.

Remaining blocker: this closes only the modeled STE.S2S terminate-only
STALL_MODEL validation slice. Complete event-record parity, full RME/GPT/GPC
policy, packet-level ATS/PRI behavior, PCIe PASID/CD invalidation lifecycle, and
upstream `arm-smmu-v3` lifecycle parity remain open.

### 2026-05-11 SMMU-COMP-030/080 STE bypass output-attribute progress note

Implemented a focused reference-backed BUG-QA-11 slice from
`sources/smmu/bugs/newBugs24Mar2026_7pm.md`:

- Added modeled STE output-attribute decoders for `MTCFG`, `MEMATTR`, `SHCFG`,
  `ALLOCCFG`, `PRIVCFG`, `INSTCFG`, and existing `NSCFG`.
- Added output-attribute fields to the Apollo SMMU TLM extension.
- Applied `record_arch_ste_output_attrs()` on QBox's context-descriptor bypass
  path and propagated the result to downstream TLM payloads.
- Added `SteBypassOutputAttributesPropagateOnContextBypass`, covering
  `MTCFG/MemAttr`, `SHCFG`, `ALLOCCFG`, `INSTCFG`, `PRIVCFG`, `NSCFG`, and the
  `MTCFG=0 => memType=0` rule.
- Verification is recorded in
  `doc/verification/qbox-smmuv3-ste-bypass-output-attrs-verification-2026-05-11.md`.

Remaining blocker: this closes only modeled context-bypass output attributes.
The direct STE.Config all-bypass follow-up is covered in the note below.
Stage-1/stage-2/nested and ATS Translated follow-ups are covered in later notes.
GATOS/ATOS return-path output attributes, PCIe packet-level attribute
semantics, and upstream `arm-smmu-v3` lifecycle parity remain open.

### 2026-05-11 SMMU-COMP-030/080 STE.Config all-bypass output-attribute progress note

Implemented a BUG-QA-11 follow-up slice for direct `STE.Config==0b100`
all-bypass output attributes in `apollo_smmu_tbu`:

- Added the modeled `ARCH_STE_CFG_BYPASS` name and `arch_ste_all_bypass()` path.
- `arch_stream_context_walk()` now returns identity PA for the direct all-bypass
  path and applies `record_arch_ste_output_attrs(..., "ste-config-bypass")`
  before downstream TLM transport.
- Added `SteConfigBypassOutputAttributesPropagate`, covering identity access,
  `MTCFG/MemAttr`, `SHCFG`, `ALLOCCFG`, `INSTCFG`, `PRIVCFG`, `NSCFG`, and the
  device/nC OSH shareability override.
- Added checker/lane/checklist/report evidence in
  `doc/verification/qbox-smmuv3-ste-config-bypass-output-attrs-verification-2026-05-11.md`.

Remaining blocker: the ATS Translated follow-up is covered in the note below.
GATOS/ATOS return-path output attributes and packet-level PCIe attribute parity
remain outside this modeled QBox TLM slice.

### 2026-05-11 SMMU-COMP-030/080 ATS Translated output-attribute progress note

Implemented a follow-up output-attribute propagation slice using the pinned
`sources/smmu` reference behavior that applies STE output attributes to normal
translation results as well as bypass results:

- `translate_segment()` can now preserve output-attribute state across the ATS
  Translated configuration check and the later downstream TLM payload routing.
- `allow_arch_translated_transaction()` clears stale output-attribute state and
  records STE output attributes with an `ats-translated` path marker on
  successful ATS Translated checks.
- `arch_stream_context_walk()` records STE output attributes for successful
  stage-1, stage-2, and nested translation results before downstream transport.
- Added `AtsTranslatedSteOutputAttributesPropagateWhenAtschkEnabled`, covering
  downstream TLM propagation of `MTCFG/MemAttr`, `SHCFG`, `ALLOCCFG`,
  `INSTCFG`, `PRIVCFG`, and `NSCFG` on an ATS Translated payload.
- Added checker/lane/checklist/report evidence in
  `doc/verification/qbox-smmuv3-ats-translated-output-attrs-verification-2026-05-11.md`.

Remaining blocker: the bounded GATOS_PAR follow-up is covered in the note
below. Full architected ATOS/VATOS register parity and packet-level PCIe
attribute parity remain outside this modeled QBox TLM slice.


### 2026-05-11 SMMU-COMP-030/080 GATOS_PAR output-attribute progress note

Implemented a bounded GATOS/ATOS-style register return-path slice using the
pinned `sources/smmu/cpp/src/smmu/smmu.cpp` `gatosTranslate()` behavior as
reference:

- Added `ARCH_CTRL_GATOS_TRANSLATE` plus `REG_ARCH_PAR_LO/HI` to the Apollo
  TBU compatibility register surface.
- Reused the architectural stream/context descriptor walk to populate
  `m_arch_last_par` on successful stage-1/stage-2/nested translations.
- Encoded successful PAR `ATTR[63:56]` and `SH[9:8]` from the modeled STE
  output-attribute state, including the existing device/nC OSH override.
- Encoded fault PAR values with `FAULT`, `FAULTCODE`, stage-2 `REASON`, and
  stage-2 `FADDR` fields from the modeled QBox fault state where available.
- Added `GatosParReportsSteOutputAttributes` and
  `GatosParFaultCodeForUnmappedPage` component vectors.
- Added checker/lane/checklist/report evidence in
  `doc/verification/qbox-smmuv3-gatos-par-output-attrs-verification-2026-05-11.md`.

Remaining blocker: this is still a bounded QBox compatibility-register
GATOS_PAR model. Full architected ATOS/VATOS register files, complete
packet-level PCIe attribute semantics, Root/Realm RME/GPT/GPC policy, and
upstream `arm-smmu-v3` lifecycle parity remain open.

### 2026-05-11 SMMU-COMP-020/030/080 architected SMMU_GATOS register progress note

Implemented the non-secure architectural ATOS/GATOS register-group slice using
`sources/smmu/wiki/concepts/atos.md` and
`sources/smmu/wiki/synthesis/smmu-register-map.md` as local reference notes:

- Added PAGE_0 `SMMUV3_GATOS_CTRL`, `SMMUV3_GATOS_SID`,
  `SMMUV3_GATOS_ADDR`, and `SMMUV3_GATOS_PAR` register offsets.
- Added `ARCH_GATOS_CTRL_RUN` and register-backed GATOS SID/ADDR/PAR state.
- Added `run_arch_gatos_register_translate()` so writing RUN performs a bounded
  architectural stream/context/table walk, writes PAR, and clears RUN.
- The register path suppresses normal EVENTQ/PRI protocol side effects on
  faults, matching the ATOS behavior that reports through PAR instead of fault
  queues.
- Added `Smmuv3GatosRegistersRunAndClear` and
  `Smmuv3GatosFaultDoesNotRecordEvent` component vectors.
- Added checker/lane/checklist/report evidence in
  `doc/verification/qbox-smmuv3-architected-gatos-registers-verification-2026-05-11.md`.

Remaining blocker: this closes only the non-secure `SMMU_GATOS` RUN/PAR path.
Secure `SMMU_S_GATOS`, VATOS/S_VATOS, complete ATOS_ADDR field/type matrix,
packet-level PCIe attribute semantics, Root/Realm RME/GPT/GPC policy, and
upstream `arm-smmu-v3` lifecycle parity remain open.

### 2026-05-11 SMMU-COMP-020/030/080 Secure SMMU_S_GATOS progress note

Implemented the Secure ATOS/GATOS register-group follow-up:

- Added Secure GATOS CTRL/SID/ADDR/PAR state and routed the existing GATOS
  offsets through the `SMMU_S_*` Secure register page.
- Added security-state-aware SMMUEN gating so Secure GATOS uses Secure CR0.
- Reused the Secure STRTAB bank when `SMMU_S_GATOS_CTRL.RUN` is written.
- Added `SecureSmmuv3GatosRegistersUseSecureBank` and
  `SecureSmmuv3GatosFaultDoesNotRecordEvent` component vectors.
- Added checker/lane/checklist/report evidence in
  `doc/verification/qbox-smmuv3-secure-gatos-registers-verification-2026-05-11.md`.

Remaining blocker: this closes Secure `SMMU_S_GATOS` RUN/PAR banking only.
VATOS/S_VATOS, complete ATOS_ADDR field/type matrix, packet-level PCIe
attribute semantics, Root/Realm RME/GPT/GPC policy, and upstream `arm-smmu-v3`
lifecycle parity remain open.

### 2026-05-11 SMMU-COMP-030/080 ATOS_ADDR.TYPE progress note

Implemented a bounded ATOS register-address matrix for `SMMU_GATOS` and the
shared `SMMU_S_GATOS` execution path:

- Added architected `ATOS_ADDR.TYPE` and `RnW` decode for register-initiated
  GATOS translations.
- Reserved `TYPE=0b00` now returns `GATOS_PAR.FAULTCODE=INV_REQ` (`0xff`).
- Requests for a translation stage that is not configured in the selected STE
  now return `INV_STAGE` (`0xfe`).
- Nested streams now support stage-1-only, stage-2-only, and stage-1+stage-2
  GATOS register requests with separate component tests.
- Existing GATOS/S_GATOS register tests now encode explicit stage-1 requests in
  `ATOS_ADDR` instead of relying on a raw IOVA lower field.

Validation evidence:

- Build: `build/verification/smmu-atos-addr-type-build-20260511.log`
- Focused gTest: `build/verification/smmu-atos-addr-type-gtest-20260511.log`
- CTest: `build/verification/smmu-atos-addr-type-ctest-20260511.log`
- Report: `doc/verification/qbox-smmuv3-atos-addr-type-verification-2026-05-11.md`

Remaining blocker: this closes only the bounded `ATOS_ADDR.TYPE`/`RnW` slice for
GATOS register-initiated translations. VATOS/S_VATOS, Secure SSEC non-secure
stream selection, HTTU details, remaining ATOS_ADDR fields, packet-level PCIe
ATS/PRI attributes, RME/GPT/GPC behavior, and upstream lifecycle parity remain
open.

### 2026-05-11 SMMU-COMP-030/080 S_GATOS.SSEC progress note

Attempt 94 closes a bounded Secure ATOS stream-selection gap: `SMMU_S_GATOS_SID.SSEC`
now selects Secure versus Non-secure StreamID lookup for the Secure GATOS register
interface, and SSEC-clear Non-secure lookups require both Secure and Non-secure
SMMUEN gates before returning a Secure `SMMU_S_GATOS_PAR` result. Verification is
tracked in `doc/verification/qbox-smmuv3-secure-gatos-ssec-verification-2026-05-11.md`.
This does not claim full ATOS/VATOS compliance; VATOS/S_VATOS optional pages and
remaining ATOS_ADDR fields remain open.

### 2026-05-11 SMMU-COMP-030/080 ATOS_ADDR access-field progress note

Attempt 95 narrows the remaining ATOS_ADDR field gap using
`sources/smmu/wiki/concepts/atos.md` as local ground truth. The architected
`SMMU_GATOS` / shared `SMMU_S_GATOS` execution path now decodes
`ATOS_ADDR.PnU`, `ATOS_ADDR.InD`, and `ATOS_ADDR.RnW`, records those access
properties in the register-translation diagnostics, and treats STE output
attribute overrides as ignored for architected ATOS_PAR success `ATTR`/`SH`.
The older QBox compatibility `REG_ARCH_CTRL=ARCH_CTRL_GATOS_TRANSLATE` path is
left unchanged so its modeled STE-output-attribute return-path test remains a
compatibility slice rather than an architectural ATOS claim.

Validation is tracked in
`doc/verification/qbox-smmuv3-atos-access-fields-verification-2026-05-11.md`.
Remaining blockers are VATOS/S_VATOS optional pages and VMID scoping, complete
ATOS_ADDR field/attribute parity beyond the bounded PnU/InD/RnW slice,
Root/Realm RME/GPT/GPC behavior, packet-level PCIe ATS/PRI attributes, and
upstream lifecycle parity.

### 2026-05-11 SMMU-COMP-020/030/080 internal VATOS progress note

Attempt 96 adds a bounded internal VATOS/S_VATOS model to the Apollo TBU while
preserving the current no-overclaiming contract:

- Added component-visible `SMMUV3_VATOS_PAGE` and `SMMUV3_S_VATOS_PAGE`
  register-page offsets plus `SMMU_VATOS_{CTRL,SID,ADDR,PAR}` offsets.
- Added `ARCH_IDR0_VATOS` bit documentation and kept `ARCH_IDR0` clear of the
  bit because the current platform cannot expose the optional page without
  colliding with existing Hexagon MMIO windows.
- Added independent non-secure GATOS, VATOS, Secure GATOS, and S_VATOS PAR
  state so register groups do not overwrite one another's PAR readback.
- Added `run_arch_vatos_register_translate()` with `m_arch_atos_virtual_interface
  = true`, reusing the existing ATOS walker to permit stage-1-only VATOS and
  return `INV_REQ` for stage-2 or stage-1+stage-2 VATOS requests.
- Added `Smmuv3VatosStage1OnlyRegisterPath`, which proves nested stage-1-only
  VATOS returns the IPA, rejects a stage-1+stage-2 VATOS request, suppresses
  fault/event queue side effects, and preserves the previous GATOS PAR.

Verification is recorded in
`doc/verification/qbox-smmuv3-internal-vatos-verification-2026-05-11.md`.
Remaining blocker: the optional VATOS/S_VATOS page is not yet guest-visible or
advertised through `SMMU_IDR0.VATOS`; full VATOS/S_VATOS compliance requires a
collision-free platform MMIO layout, BA_VATOS/S_VATOS selector plumbing, and
Linux/upstream-driver-visible validation.

### 2026-05-11 SMMU-COMP-020/030/080 VATOS VMID-scope progress note

Attempt 97 narrows the VATOS/S_VATOS optional-page gap without changing the
no-overclaiming advertisement state. The Apollo TBU now decodes `STE.S2VMID`
from STE word 2 bits `[63:48]`, carries that VMID through the modeled stage-2
and nested walker state, and validates internal VATOS requests against the
active `SMMU_(S_)VATOS_SEL` VMID. A matching VMID permits the existing
stage-1-only VATOS path to return the IPA; a foreign VMID or non-stage-2-tagged
STE rejects the request with `ATOS_PAR.FAULTCODE=INV_REQ` and does not emit
EVENTQ/PRIQ side effects.

Validation is tracked in
`doc/verification/qbox-smmuv3-vatos-vmid-scope-verification-2026-05-11.md`.
Remaining blockers are unchanged for full VATOS compliance: the optional
VATOS/S_VATOS pages are still not guest-visible or advertised through
`SMMU_IDR0.VATOS`, BA_VATOS/S_VATOS platform placement remains unresolved, and
packet-level PCIe ATS/PRI behavior, Root/Realm RME/GPT/GPC behavior, and
upstream lifecycle parity remain open.

## 2026-05-11 SMMU-COMP-060 PRI PPR/Stop Marker progress note

Implemented a narrow PRI Page Request Packet metadata slice.  The Apollo TBU now
has modeled PPR helpers for SSV, Last, Read, Write, Execute, Privileged,
PRGIndex, and SubstreamID/PASID fields in memory-backed PRIQ records.  It also
recognizes PRI Stop PASID Markers (`SSV==1`, `LWR==0b100`) and suppresses PRG
responses for them, and it suppresses automatic responses for non-last PPRs
that are discarded when PRIQ overflow is active.

Evidence is tracked in
`doc/verification/qbox-smmuv3-pri-ppr-stop-marker-verification-2026-05-11.md`.
This does not claim full PCIe ATS/PRI compliance: packet transport, Root
Complex signaling, DPT/GPC interactions, complete automatic response PASID
selection, and upstream `arm-smmu-v3` lifecycle parity remain open.

## 2026-05-11 SMMU-COMP-060 PRI overflow auto-response progress note

Implemented a narrow no-PASID overflow auto-response correction.  The Apollo TBU
now maps a discarded Last PPR without SSV/PASID during PRIQ overflow to an
automatic PRI Success response, while retaining Response Failure for disabled
PRIQ and active PRIQ_ABT_ERR.  PASID-prefixed overflow response selection remains
conservative and still requires modeled `SMMU_IDR3.PPS` plus `STE.PPAR` lookup.

Evidence is tracked in
`doc/verification/qbox-smmuv3-pri-overflow-auto-response-verification-2026-05-11.md`.
This remains a functional slice; full PCIe packet transport, DPT/GPC, and
upstream `arm-smmu-v3` lifecycle parity remain open.


## 2026-05-11 SMMU-COMP-060 PRI STE.PPAR auto-response progress note

Implemented a narrow PASID-prefixed PRI overflow auto-response slice.  When a
Last PPR with SSV/PASID is discarded because PRIQ overflow is active and
`SMMU_IDR3.PPS==0`, the Apollo TBU now performs an associated STE lookup,
checks `STE.PPAR`, returns Success with a modeled PASID prefix when PPAR is set,
returns Success without a PASID prefix when PPAR is clear, and returns Failure
when the STE lookup is invalid/inaccessible.  The existing no-PASID Success,
PRIQ-disabled Failure, active-PRIQ_ABT_ERR Failure, Stop PASID Marker, and
non-last discard behaviors remain covered.

Verification plan/evidence is recorded in
`doc/verification/qbox-smmuv3-pri-ppar-auto-response-verification-2026-05-11.md`.
This still does not claim full SMMUv3 ATS/PRI compliance because packet-level
PCIe transport, complete invalidation/retry protocol parity, and upstream driver
lifecycle parity remain open.


## 2026-05-11 SMMU-COMP-060 PRI Secure-stream auto-failure progress note

Implemented a narrow PRI miscellaneous-rule slice for protocol PPRs received
from a Secure stream.  `push_pri_protocol_record()` now detects the Secure
security state, records a Response Failure auto-response with reason
`secure-stream-pri`, clears the pending PRG, and avoids enqueueing the PPR in
PRIQ.  This intentionally leaves the older Secure PRIQ bank compatibility helper
untouched so Secure queue/MSI plumbing can still be tested independently.

Verification plan/evidence is recorded in
`doc/verification/qbox-smmuv3-pri-secure-stream-auto-failure-verification-2026-05-11.md`.
This is still a functional slice rather than full ATS/PRI compliance.


## 2026-05-11 SMMU-COMP-060 PRI STE.PPAR lookup-event progress note

Implemented a narrow PRI overflow STE.PPAR lookup event-recording slice.  When
PASID-prefixed overflow auto-response selection cannot check a valid STE, the
Apollo TBU now applies the ATS configuration recording gates used by the
architecture: bad StreamID requires `CR2.REC_CFG_ATS && CR2.RECINVSID`, while
STE/VMS/config lookup faults require `CR2.REC_CFG_ATS`; otherwise the failure
response is still returned but the EVENTQ record is suppressed.  Component
coverage exercises the modeled `C_BAD_STE` REC_CFG_ATS on/off cases.

Verification plan/evidence is recorded in
`doc/verification/qbox-smmuv3-pri-ppar-lookup-event-verification-2026-05-11.md`.
This remains a functional protocol slice rather than full ATS/PRI compliance.

## 2026-05-11 SMMU-COMP-060 PRI STE.PPAR bad StreamID RECINVSID progress note

Implemented the next bounded PRI overflow auto-response verification slice for
PASID-prefixed PPRs whose STE.PPAR lookup fails before an STE can be fetched.
The Apollo TBU already routes `ARCH_FAULT_BAD_STREAM_ID` through
`record_pri_ppar_lookup_fault()` and the ATS Translation Request recording
helper `arch_record_bad_streamid_ats_treq()`, so this pass adds explicit
component and checklist coverage for the architected `CR2.REC_CFG_ATS &&
CR2.RECINVSID` event-recording gate.

Component coverage adds `PriProtocolPparBadStreamIdHonorsRecInvsid`, which
forces PRIQ overflow with an out-of-range StreamID. With `REC_CFG_ATS=1` and
`RECINVSID=0`, the model suppresses EVENTQ recording and returns PRI Response
Failure while clearing the pending PRG. With both bits set, the model records a
`C_BAD_STREAMID` EVENTQ entry carrying the failing StreamID and still returns
Response Failure. This narrows SMMU-COMP-060 PRI/ATS event semantics without
claiming full packet-level ATS/PRI transport compliance.

## 2026-05-11 SMMU-COMP-060 PRI response head-order progress note

Reworked the earlier `CMD_PRI_RESP` exact-PRG slice against the local
`sources/smmu` reference notes for PRIQ/CMD_PRI_RESP ordering. `complete_prg()`
now treats the pending PRI table as an ordered queue: a response can retire only
the head pending PRG, and a command naming a later PRG is reported as an
unknown/non-retiring response with `last_pri_response_order_mismatch` and
`last_pri_response_head_prg` diagnostics. The response path still records the
last completed PRI response StreamID, response code, original ATS status, and
StreamID/PASID qualifier mismatch state in the architected fault/replay state.

Component coverage now uses `CmdPriRespRequiresHeadPrgOrdering`, which allocates
two pending PRGs, proves a response for the second PRG cannot clear it before the
head, then completes the head and finally completes the second PRG. This narrows
SMMU-COMP-060 PRI response recovery semantics while retaining the explicit
no-overclaim boundary: full packet-level ATS/PRI transport, complete ATC
recovery, upstream driver parity, and RME/GPT/GPC policy remain open.

## 2026-05-11 SMMU-COMP-060 PRI response unknown-PRG progress note

Added explicit unknown-PRG diagnostic coverage for `CMD_PRI_RESP`. The existing
unknown response accounting now also verifies `last_pri_response_unknown`, keeps
`last_pri_response_valid` false, preserves the command response code, and clears
StreamID/ATS-status metadata when no pending PRG matched. This prepares the PRI
response path for stricter driver-recovery parity audits without claiming full
packet-level ATS/PRI behavior or upstream lifecycle compliance.

## 2026-05-11 SMMU-COMP-060 PRI response StreamID qualifier progress note

Added a modeled StreamID qualifier for `CMD_PRI_RESP`. Non-zero
`cmdq_stream_id(word0)` values are now passed into `complete_prg()`, which only
clears a pending PRG when both PRG and StreamID match. The mismatch path leaves
the PRG pending and records `last_pri_response_stream_mismatch` plus the command
StreamID for recovery diagnostics. Component coverage adds
`CmdPriRespHonorsStreamIdQualifier`, proving a wrong StreamID does not clear the
pending request and a subsequent correct StreamID response does.

This narrows PRI response command-field parity while preserving legacy zero-SID
compatibility and retaining the no-overclaim boundary around packet-level
ATS/PRI transport, complete ATC recovery, upstream lifecycle parity, and
RME/GPT/GPC policy.

## 2026-05-11 SMMU-COMP-060 PRI response SSID qualifier progress note

Implemented a bounded `CMD_PRI_RESP` PASID/SSID qualifier slice. Pending PRI
requests now retain modeled SSID metadata, and both Non-secure and Secure CMDQ
`ARCH_CMD_PRI_RESP` handlers pass command SSV/SSID fields into `complete_prg()`.
A response with a matching PRG but a mismatched PASID/SSID is now rejected as an
unknown/mismatch diagnostic without clearing the pending request; a subsequent
response with the correct PASID/SSID clears the PRG and records completion
metadata.

This narrows packet-level PRI parity but remains a functional slice rather than
full SMMUv3 compliance. Real PCIe PRI/PASID packets, endpoint ATC completion and
recovery ordering, full Secure/Realm/RME/GPT/GPC policy, and upstream Linux
`arm-smmu-v3` lifecycle parity remain open.

## 2026-05-11 SMMU-COMP-060 PRI response reserved-code progress note

Implemented a bounded `CMD_PRI_RESP` response-code validation slice. The Apollo
TBU now accepts only the modeled PRG response codes Success, Invalid Request,
and Response Failure; other response encodings set `CMDQ_CONS.CERROR_ILL` (or
Secure `S_CMDQ_CONS.CERROR_ILL`) before any pending PRG is cleared. Component
coverage verifies the Non-secure CMDQ error path leaves `CONS.RD` on the bad
command, raises the command-abort GERROR bit, preserves the pending PRG, and
does not increment normal PRI response accounting.

This narrows command-queue PRI semantics but remains a functional slice rather
than full SMMUv3 compliance. Remaining blockers include packet-level PCIe
ATS/PRI transport, endpoint ATC recovery ordering, full Secure/Realm/RME/GPT/GPC
policy, and upstream Linux `arm-smmu-v3` lifecycle parity.

## 2026-05-11 SMMU-COMP-060 Secure PRI response reserved-code progress note

Extended the bounded `CMD_PRI_RESP` reserved response-code validation to the
Secure command queue path. Secure `ARCH_CMD_PRI_RESP` now checks the modeled PRG
response code before clearing a pending PRG; reserved encodings report
`S_CMDQ_CONS.CERROR_ILL`, leave `S_CMDQ_CONS.RD` at the offending command, raise
Secure `S_GERROR.CMDQ_ABORT`, and preserve normal PRI response accounting.

This narrows Secure command lifecycle parity for the modeled slice but remains
short of full SMMUv3 compliance. Open blockers remain packet-level PCIe ATS/PRI
transport, endpoint ATC recovery ordering, broader Secure/Realm/RME/GPT/GPC
policy, and upstream Linux `arm-smmu-v3` lifecycle parity.

## 2026-05-11 SMMU-COMP-060 Secure PRI response Non-secure StreamID progress note

Implemented a bounded Secure command-queue `CMD_PRI_RESP` StreamID ownership
slice. Accepted Secure `ARCH_CMD_PRI_RESP` commands are now decoded through
`secure_cmdq_command_security_state()`, which records `CMD_PRI_RESP` as a
Non-secure StreamID operation regardless of the RES0 `ARCH_CMDQ_SSEC` bit.
Component coverage adds `SecureCmdPriRespIgnoresSsecAndTargetsNonSecure`,
proving the Secure CMDQ command consumes a matching Non-secure pending PRG,
advances `S_CMDQ_CONS.RD`, and does not raise Secure command-abort state.

This narrows Secure PRI command parity but remains short of full SMMUv3
compliance. Open blockers remain packet-level PCIe ATS/PRI transport, endpoint
ATC recovery ordering, broader Secure/Realm/RME/GPT/GPC policy, and upstream
Linux `arm-smmu-v3` lifecycle parity.

## 2026-05-11 SMMU-COMP-020/060 IDR0 ATS/PRI advertisement progress note

Aligned the modeled Apollo TBU feature advertisement with the ATS/PRI command
support already implemented in the functional slice. `SMMU_IDR0` now advertises
ATS and PRI through explicit `ARCH_IDR0_ATS` and `ARCH_IDR0_PRI` constants, the
modeled command handlers keep explicit unsupported-command `CERROR_ILL` reasons,
and the Apollo Linux selftest expectation moved to `IDR0=0x0181a705`.
Component coverage adds `ArchitectedIdr0AdvertisesAtsPri` to prove the
architected register surface exposes both feature bits.

This narrows register/ATS/PRI command parity but remains short of full SMMUv3
compliance. Open blockers remain packet-level PCIe ATS/PRI transport, endpoint
ATC recovery ordering, broader Secure/Realm/RME/GPT/GPC policy, and upstream
Linux `arm-smmu-v3` lifecycle parity.


## 2026-05-11 SMMU-COMP-060 PRI PPR ATSCHK/EATS independence progress note

Implemented a bounded PRI Page Request protocol independence slice. The Apollo
TBU PRIQ enqueue path now explicitly documents that incoming PPRs are not gated
by `SMMU_CR0.ATSCHK` or `STE.EATS`; those fields remain ATS Translation
Request/Translated transaction controls. `STE.PPAR` lookup remains limited to
the overflow auto-response path. Component coverage adds
`PriProtocolPprIgnoresAtschkAndSteEats`, proving PPR records are queued with
`ATSCHK==0` and also with `ATSCHK==1` while `STE.EATS==0b00`, without generating
a PRI auto-response or consulting STE.PPAR.

This narrows PRI protocol parity but remains short of full SMMUv3 compliance.
Open blockers remain packet-level PCIe ATS/PRI transport, endpoint ATC recovery
ordering, broader Secure/Realm/RME/GPT/GPC policy, and upstream Linux
`arm-smmu-v3` lifecycle parity.


## 2026-05-11 SMMU-COMP-060 PRI PRGIndex 9-bit progress note

Implemented a bounded PRI PRGIndex field-width slice. The Apollo TBU now defines
`ARCH_PRIQ_PPR_PRG_MASK = 0x1ff`, masks PRGIndex values when encoding PRIQ PPR
word3 and decoding `CMD_PRI_RESP`, and makes `allocate_prg()` wrap through the
nonzero 9-bit PRGIndex space while avoiding duplicate pending PRGs. Component
coverage adds `PriProtocolPrgIndexIsNineBitsAndWraps`, proving allocation at
`0x1ff` wraps through zero to `0x001`, and proving a `CMD_PRI_RESP` carrying a
set bit 9 still matches the masked 9-bit head pending PRG.

This narrows PRI command/queue field parity but remains short of full SMMUv3
compliance. Open blockers remain packet-level PCIe ATS/PRI transport, endpoint
ATC recovery ordering, broader Secure/Realm/RME/GPT/GPC policy, and upstream
Linux `arm-smmu-v3` lifecycle parity.

## 2026-05-11 SMMU-COMP-060 PRI response PRIQ_CONS progress note

Implemented a follow-up PRI queue lifecycle slice for successful head
`CMD_PRI_RESP` handling. The Apollo TBU now records the security bank on pending
PRI requests and calls `advance_priq_cons_after_response()` when a head PRG is
retired, advancing the modeled `SMMU_PRIQ_CONS` index and clearing the PRIQ IRQ
when the queue becomes empty. Component coverage adds
`CmdPriRespAdvancesPriqConsForHeadRequest`, proving a memory-backed PPR advances
`SMMU_PRIQ_CONS` only after a successful head response.

This narrows the SMMU-COMP-060 PRIQ lifecycle gap while preserving the
no-overclaim boundary. Remaining work includes byte-exact packet transport,
endpoint ATC recovery ordering, broader Secure/Realm/RME policy, and upstream
Linux `arm-smmu-v3` lifecycle parity.

## 2026-05-11 SMMU-COMP-060 PRI response SMMUEN-disabled progress note

Added explicit regression coverage for the architected `CMD_PRI_RESP` no-op rule
while `SMMU_CR0.SMMUEN` is clear. The existing QBox command queue gate already
requires `SMMUEN|CMDQEN`; this pass adds `CmdPriRespIgnoredWhenSmmuenDisabled`
to prove a submitted response does not consume the pending PRG, does not advance
`SMMU_PRIQ_CONS`, and does not raise CERROR while disabled. The same command is
then processed normally after SMMUEN is restored.

This closes another bounded SMMU-COMP-060 PRI command lifecycle gap, but it does
not claim full ATS/PRI packet compliance, endpoint ATC recovery ordering, RME/GPT
policy, or upstream Linux `arm-smmu-v3` lifecycle parity.

## 2026-05-11 SMMU-COMP-050/060 ATS Translated split-stage stage-2-only progress note

The ATS Translated split-stage model now includes a bounded stage-2-only slice:
`STE.EATS==0b10` with `STE.Config==S2_TRANS` is allowed to validate the incoming
Translated address as an IPA through the existing stage-2 page-table walker.
`AtsTranslatedSplitStageStage2OnlyWalksIpa` proves the downstream payload,
`m_arch_last_stage`, `m_arch_s2ttb`, and `m_arch_last_pa` come from that stage-2
walk.  Non-stage2-only/nested split-stage ATS Translated traffic remains rejected
with `F_TRANSL_FORBIDDEN` until the endpoint path can bypass stage-1 for
AT=Translated packets.

## 2026-05-11 SMMU-COMP-050/060 ATS Translated nested split-stage progress note

Added the architected Nested STE split-stage ATS Translated slice.  The pinned
`sources/smmu` reference describes `STE.EATS==0b10` split-stage ATS Translated
traffic as carrying an IPA, with the SMMU applying stage 2 to produce the PA.
QBox now latches allowed EATS_SPLIT Translated requests and, for
`STE.Config==Nested`, bypasses the stage-1/CD walk so the incoming IPA is
validated by the existing stage-2 descriptor walker only.  The earlier
stage-2-only stream case remains as a compatibility slice, while non-stage2 and
non-nested split-stage Translated traffic still records `F_TRANSL_FORBIDDEN`.

Verification evidence is recorded in
`doc/verification/qbox-smmuv3-ats-translated-split-stage-nested-verification-2026-05-11.md`
and the logs under
`build/verification/smmu-ats-translated-split-stage-nested-*20260511.*`.  The
static checker continues to classify full SMMUv3 compliance as `not_claimed`
until packet-level ATS/PRI, DPT, complete upstream Linux lifecycle parity, and
RME/GPT/GPC policy are implemented and verified.

## 2026-05-11 SMMU-COMP-060 ATS Translation Request nested split-stage progress note

Extended the split-stage ATS stage-2-only behavior from AT=Translated data
traffic to ATS Translation Requests.  For `STE.Config==Nested` and
`STE.EATS==0b10`, QBox now treats the ATS Translation Request address as an IPA,
bypasses the nested stage-1/CD walk, and returns the result of the stage-2 walk.
This follows the pinned `sources/smmu` reference notes for split-stage ATS
IPA-to-PA handling.  Verification evidence is recorded in
`doc/verification/qbox-smmuv3-ats-treq-split-stage-nested-verification-2026-05-11.md`
and `build/verification/smmu-ats-treq-split-stage-nested-*20260511.*`.

The no-overclaim boundary is unchanged: full ARM SMMUv3 compliance remains
`not_claimed` until packet-level ATS/PRI ordering, DPT, upstream driver lifecycle
parity, and complete RME/GPT/GPC policy are implemented and verified.

## 2026-05-11 SMMU-COMP-050/060 ATS Translated split-stage access-override progress note

Added a bounded access-override slice for `STE.EATS==0b10` ATS Translated
traffic on the modeled Nested STE stage-2-only path.  The pinned `sources/smmu`
reference calls out BUG-13.7: `STE.INSTCFG` and `STE.PRIVCFG` effective access
overrides are applied before the split-stage stage-2-only translation.  QBox now
computes those effective attributes in the ATS Translated gate and carries them
on the downstream TLM payload while preserving the caller's extension after the
transaction completes.

`AtsTranslatedSplitStageNestedAppliesAccessOverrides` verifies that incoming
unprivileged/data Translated traffic with `INSTCFG=Instruction` and
`PRIVCFG=Privileged` reaches the stage-2 translated payload as privileged
instruction access, while the raw STE output attributes remain visible.
Verification evidence is recorded in
`doc/verification/qbox-smmuv3-ats-translated-split-stage-access-overrides-verification-2026-05-11.md`
and `build/verification/smmu-ats-translated-split-stage-access-overrides-*20260511.*`.

The no-overclaim boundary remains unchanged: full ARM SMMUv3 compliance remains
`not_claimed` until packet-level ATS/PRI ordering, DPT, upstream driver
lifecycle parity, and complete RME/GPT/GPC policy are implemented and verified.

## 2026-05-11 SMMU-COMP-020/030/080 GBPA global-bypass progress note

Added a bounded `SMMU_GBPA` disabled-SMMU behavior slice.  The pinned
`sources/smmu` reference requires ordinary traffic with `SMMUEN==0` to bypass
using `SMMU_GBPA` attributes when `GBPA.ABORT==0`, and to abort without EVENTQ
recording when `GBPA.ABORT==1`.  QBox now decodes modeled GBPA output fields,
applies those attributes on the existing disabled-SMMU data path, and suppresses
fault-event recording for the GBPA abort path.

`GlobalBypassUsesGbpaOutputAttributes` verifies MTCFG/MemAttr, Device/nC to OSH
shareability normalization, ALLOCCFG override semantics, and INSTCFG/PRIVCFG
propagation on a disabled-SMMU payload.  `GlobalBypassGbpaAbortSuppressesEvent`
verifies no downstream access and no EVENTQ production when `GBPA.ABORT` is set.
Verification evidence is recorded in
`doc/verification/qbox-smmuv3-gbpa-global-bypass-verification-2026-05-11.md`
and `build/verification/smmu-gbpa-global-bypass-*20260511.*`.

The no-overclaim boundary remains unchanged: full ARM SMMUv3 compliance remains
`not_claimed` until full packet-level ATS/PRI ordering, DPT, complete
Realm/Root/GBPA/AGBPA policy, upstream driver lifecycle parity, and RME/GPT/GPC
policy are implemented and verified.

## 2026-05-11 SMMU-COMP-020/030/080 AGBPA unsupported-RES0 progress note

Added an explicit `SMMU_AGBPA`/`SMMU_S_AGBPA` register-policy slice.  The Arm
SMMUv3 reference defines AGBPA as an implementation-defined alternate global
bypass attribute/tag register and permits unsupported implementations to expose
it as RES0.  QBox now allocates the architected Page 0 slot at `0x0048`, returns
zero for Non-secure and Secure AGBPA reads, and ignores writes while preserving
ordinary `SMMU_GBPA`/`SMMU_S_GBPA` behavior.

`AgbpaUnsupportedRegistersAreRes0` verifies Non-secure and Secure AGBPA
write-ignore/read-zero behavior and confirms adjacent GBPA remains writable.
Verification evidence is recorded in
`doc/verification/qbox-smmuv3-agbpa-res0-verification-2026-05-11.md` and
`build/verification/smmu-agbpa-res0-*20260511.*`.

The no-overclaim boundary remains unchanged: this is an explicit unsupported
implementation-defined AGBPA policy, not a full alternate tag implementation or
complete Realm/RME/GPT/GPC/PCIe ATS/PRI compliance claim.

## 2026-05-11 SMMU-COMP-020/050/060 DPT register RES0 progress note

Added an explicit unsupported-register slice for Device Permission Table
registers.  QBox already advertises `SMMU_IDR3.DPT==0` and rejects DPTI commands;
this pass closes the adjacent register aperture ambiguity by assigning
`SMMU_DPT_BASE`, `SMMU_DPT_BASE_CFG`, and `SMMU_DPT_CFG_FAR` offsets and exposing
those registers as RES0/write-ignored while DPT remains unsupported.

`DptUnsupportedRegistersAreRes0` verifies DPT discovery is clear and that both
Non-secure and Secure-page probes of the DPT register offsets read zero after
writes.  Verification evidence is recorded in
`doc/verification/qbox-smmuv3-dpt-register-res0-verification-2026-05-11.md` and
`build/verification/smmu-dpt-register-res0-*20260511.*`.

The no-overclaim boundary remains unchanged: this does not implement the DPT
descriptor walker/cache/fault machinery, packet-level ATS/PRI ordering, upstream
Linux `arm-smmu-v3` lifecycle parity, or complete Realm/RME/GPT/GPC policy.

## 2026-05-11 SMMU-COMP-020/060 ECMDQ unsupported-register RES0 progress note

Added an explicit unsupported-register slice for Enhanced Command Queue (ECMDQ)
discovery.  The pinned Arm SMMUv3 reference states that when
`SMMU_IDR1.ECMDQ==0`, `SMMU_IDR6` and `SMMU_CMDQ_CONTROL_PAGE_*` discovery
registers are RES0; the Secure interface mirrors this through
`SMMU_S_IDR0.ECMDQ==0`/`SMMU_S_IDR6`.  QBox continues not to advertise ECMDQ,
and now explicitly exposes `SMMU_IDR6`, `SMMU_S_IDR6`, and the first Non-secure
and Secure ECMDQ control-page aperture as read-zero/write-ignored.

`EcmdqUnsupportedRegistersAreRes0` verifies Non-secure and Secure ECMDQ
advertisement bits remain clear, IDR6/S_IDR6 remain zero after writes, and the
first ECMDQ control-page BASE/CFG/STATUS registers remain RES0/WI.  Verification
evidence is recorded in
`doc/verification/qbox-smmuv3-ecmdq-register-res0-verification-2026-05-11.md`
and `build/verification/smmu-ecmdq-register-res0-*20260511.*`.

The no-overclaim boundary remains unchanged: this is not ECMDQ implementation.
Full ECMDQ compliance still requires IDR6-advertised control page counts,
per-queue ECMDQ registers, EN/ENACK state machines, error toggle/recovery,
CMDQP_ERR/MSI abort reporting, and command-ordering validation.

## 2026-05-11 SMMU-COMP-020 IIDR/AIDR register-slot progress note

Corrected the Page 0 implementation/architecture ID register slots to match the
Arm SMMUv3 register map.  QBox now exposes `SMMU_IIDR` at offset `0x0018` and
`SMMU_AIDR` at offset `0x001C`; previously the model aliased the AIDR value at
the IIDR slot.

`ArchitectedRegisterMmioSurface` now verifies `SMMUV3_IIDR` reads the modeled
implementation-defined IIDR value, `SMMUV3_AIDR` reads the architecture ID value,
and the two slots are not accidentally aliased.  Verification evidence is
recorded in
`doc/verification/qbox-smmuv3-iidr-aidr-register-slots-verification-2026-05-11.md`
and `build/verification/smmu-iidr-aidr-register-slots-*20260511.*`.

The no-overclaim boundary remains unchanged: this is a register-map correction,
not a new architecture-version or full SMMUv3 protocol compliance claim.

## 2026-05-11 SMMU-COMP-020/040/050 IDR5 granule/OAS progress note

Aligned `SMMU_IDR5` discovery with the bounded walker and output-address model.
QBox now advertises the modeled 4K, 16K, and 64K granules plus 48-bit OAS.  The
48-bit OAS value matches `ARCH_DESC_OUTPUT_MASK` and the existing Translated
address-size abort boundary.

`ArchitectedRegisterMmioSurface` verifies the IDR5 OAS/granule bits,
`ArchitectedWalkerGranuleBlockAndFaultMatrix` continues to cover selected
4K/16K/64K walker vectors, and `AtsTranslatedAddressSizeAbortIsNoEvent` verifies
the 48-bit boundary no-event abort behavior.  Verification evidence is recorded
in `doc/verification/qbox-smmuv3-idr5-granule-oas-verification-2026-05-11.md`
and `build/verification/smmu-idr5-granule-oas-*20260511.*`.

The no-overclaim boundary remains unchanged: no 52-bit/56-bit, DS, VAX, D128,
complete descriptor matrix, DPT, RME/GPT/GPC, or packet-level ATS/PRI/ECMDQ
protocol compliance is claimed by this discovery alignment.

## 2026-05-11 SMMU-COMP-020/030/050/060 IDR1 discovery/limits progress note

Aligned the bounded discovery fields that software uses to size StreamID,
SubstreamID, and architected queues with the modeled Apollo TBU behavior.  QBox
now advertises `SMMU_IDR1.SIDSIZE==8`, `SSIDSIZE==20`, and 32 Ki-entry
Command/Event/PRI queue maxima (`CMDQS/EVENTQS/PRIQS==15`) because the model
already carries 8-bit-plus test StreamIDs, 20-bit PASID/SSID tags, and queue
base encodings up to log2 entries 15.  `ATTR_TYPES_OVR` and `ATTR_PERMS_OVR` are
also advertised to match the existing GBPA/STE access and memory-attribute
override model.

Because the Arm SMMUv3 reference requires `SMMU_IDR0.ST_LEVEL!=0` when
`SMMU_IDR1.SIDSIZE>=7`, this slice also advertises the already-modeled 2-level
Stream Table support through `SMMU_IDR0.ST_LEVEL==0b01`.  The Apollo Linux probe
constants were moved to `IDR0=0x098db70b` and `IDR1=0x0def7d08` so guest-visible
selftests validate the same discovery surface as the component model.

`ArchitectedRegisterMmioSurface` verifies the Non-secure IDR0/IDR1 fields, and
`SecureRegisterBankConfiguresStrtabCmdqAndEventq` verifies that Secure
`SMMU_S_IDR1` exposes only `SECURE_IMPL`, `SEL2`, and `S_SIDSIZE`, keeping
bits[28:6] RES0 rather than mirroring Non-secure queue and override fields.
Verification evidence is recorded in
`doc/verification/qbox-smmuv3-idr1-discovery-limits-verification-2026-05-11.md`
and `build/verification/smmu-idr1-discovery-limits-*20260511.*`.

The no-overclaim boundary remains unchanged: this discovery alignment does not
add full upstream `arm-smmu-v3` driver integration, complete PCIe PASID/ATS/PRI
packet protocol parity, ECMDQ implementation, all StreamID/SSID out-of-range
fault combinations, or complete queue size stress beyond the modeled log2<=15
queue machinery.

## 2026-05-11 SMMU-COMP-020/030/040 IDR0 stage/TTF/CD2L progress note

Aligned the `SMMU_IDR0` discovery fields with the modeled Apollo TBU translation
pipeline.  QBox now advertises both stage 1 and stage 2 translation support,
AArch64/VMSAv8-64 translation-table format support, two-level Stream Tables, and
two-level Context Descriptor tables.  This also removes the previous mismatch
where Secure `SMMU_S_IDR1.SECURE_IMPL`/`SEL2` were advertised while Non-secure
`SMMU_IDR0.S1P` was still clear.

The Apollo Linux selftest expectation is now `IDR0=0x098db70b`, preserving the
previous ATS/PRI/MSI/ATOS/terminate-only discovery bits while adding `S1P`,
AArch64 `TTF`, `CD2L`, and the already-modeled two-level STRTAB advertisement.
`ArchitectedRegisterMmioSurface` verifies the new `S1P`, `S2P`, `TTF`, `CD2L`,
and `ST_LEVEL` fields.  Verification evidence is recorded in
`doc/verification/qbox-smmuv3-idr0-stage-ttf-cd2l-verification-2026-05-11.md`
and `build/verification/smmu-idr0-stage-ttf-cd2l-*20260511.*`.

The no-overclaim boundary remains unchanged: the model still does not claim full
VMSAv8-32 parity, every descriptor/reserved-bit combination, full upstream
`arm-smmu-v3` lifecycle parity, ECMDQ, DPT, or complete RME/GPT/GPC coverage.

## 2026-05-11 SMMU-COMP-020/040/060 IDR0 ASID16/VMID16 progress note

Aligned ASID/VMID discovery with the modeled tag widths.  QBox already stores
16-bit ASIDs in context descriptors/TLBI commands and 16-bit VMIDs in STE/TLBI
state (`ARCH_CD_ASID_MASK` and `ARCH_STE_S2VMID_MASK` are both 16-bit fields),
so this slice advertises `SMMU_IDR0.ASID16` and `SMMU_IDR0.VMID16` and updates
the Apollo Linux selftest expectation to `IDR0=0x098db70b`.

`CmdqTaggedInvalidationHonorsAsidVmidAndSsid` now uses high-bit ASID/VMID values
(`0x9234` and `0xd678`) so the component test proves the invalidation model
retains and matches the upper byte instead of truncating to 8-bit tags.
`ArchitectedRegisterMmioSurface` also checks the IDR0 `ASID16` and `VMID16`
discovery bits.  Verification evidence is recorded in
`doc/verification/qbox-smmuv3-idr0-asid16-vmid16-verification-2026-05-11.md`
and `build/verification/smmu-idr0-asid16-vmid16-*20260511.*`.

The no-overclaim boundary remains unchanged: this does not claim complete ASID/
VMID invalidation parity across every command/security-state/regime encoding,
full upstream `arm-smmu-v3` lifecycle parity, or complete ATS/PRI packet-level
ordering.

## 2026-05-11 SMMU-COMP-020/060 Secure IDR3 SAMS/RES0 progress note

Corrected Secure `SMMU_S_IDR3` discovery so the Secure page no longer mirrors
Non-secure `SMMU_IDR3.MPAM/RIL/DPT` bits.  The Arm SMMUv3 reference defines
`SMMU_S_IDR3` as a Secure ATS Maintenance Support (`SAMS`) field at bit 6 with
all other bits RES0.  QBox models Secure `CMD_ATC_INV` and `CMD_PRI_RESP` support
rather than the SAMS-restricted behavior, so `SMMU_S_IDR3.SAMS==0` and the
register now reads zero.

`SecureRegisterBankConfiguresStrtabCmdqAndEventq` verifies that Secure IDR3 is
`ARCH_S_IDR3`, that MPAM/RIL/DPT and SAMS bits are clear in the Secure bank, and
that the Non-secure IDR3 value remains distinct.  Verification evidence is
recorded in
`doc/verification/qbox-smmuv3-secure-idr3-sams-res0-verification-2026-05-11.md`
and `build/verification/smmu-secure-idr3-sams-res0-*20260511.*`.

The no-overclaim boundary remains unchanged: this is a Secure discovery/register
bank correction, not full Secure command lifecycle parity or complete Secure ATS
maintenance ordering coverage.

## 2026-05-11 SMMU-COMP-020 IDR4 implementation-defined zero progress note

Made the implementation-defined `SMMU_IDR4` register slot explicit in both the
Non-secure and Secure Apollo TBU register banks.  QBox now assigns
`SMMUV3_IDR4=0x010`, returns zero-valued `ARCH_IDR4` and `ARCH_S_IDR4`, and keeps
IDR4 read-only/no-advertisement for implementation-defined capabilities.

`ArchitectedRegisterMmioSurface` verifies the Non-secure `SMMU_IDR4` value, and
`SecureRegisterBankConfiguresStrtabCmdqAndEventq` verifies Secure `SMMU_S_IDR4`.
Verification evidence is recorded in
`doc/verification/qbox-smmuv3-idr4-implementation-defined-zero-verification-2026-05-11.md`
and `build/verification/smmu-idr4-implementation-defined-zero-*20260511.*`.

The no-overclaim boundary remains unchanged: this is a Page 0 register-map and
implementation-defined discovery-policy correction, not full Secure/Non-secure
command lifecycle parity, upstream `arm-smmu-v3` lifecycle parity, ECMDQ, DPT, or
complete ATS/PRI/RME coverage.

## 2026-05-11 SMMU-COMP-020/070 Secure IDR0 MSI/stall/RES0 progress note

Corrected Secure `SMMU_S_IDR0` discovery so the Secure page no longer mirrors
Non-secure `SMMU_IDR0` stage/ATS/PRI/TTF/ST_LEVEL bits.  The Arm SMMUv3
reference defines `SMMU_S_IDR0` as a Secure programming-interface feature
register with only ECMDQ bit 31, STALL_MODEL bits [25:24], MSI bit 13, and all
other bits RES0.

QBox now exposes `ARCH_S_IDR0` with Secure MSI advertised for the existing
Secure EVENTQ/GERROR MSI bank, terminate-only stall-model discovery matching the
current advertised model, and ECMDQ clear because Secure ECMDQ remains
unsupported.  `SecureRegisterBankConfiguresStrtabCmdqAndEventq` verifies Secure
IDR0, ECMDQ clear, RES0 masking, and that it is distinct from Non-secure IDR0.
Verification evidence is recorded in
`doc/verification/qbox-smmuv3-secure-idr0-msi-stall-res0-verification-2026-05-11.md`
and `build/verification/smmu-secure-idr0-msi-stall-res0-*20260511.*`.

The no-overclaim boundary remains unchanged: this is a Secure discovery/register
bank correction, not ECMDQ implementation, a new stall model, complete Secure
command lifecycle parity, or full GIC/MSI ordering parity.

## 2026-05-11 SMMU-COMP-020/040/060 AIDR v3.3 and IDR3 mandatory discovery progress note

Aligned `SMMU_AIDR` and `SMMU_IDR3` discovery with the bounded feature set that
QBox already advertises.  The previous `AIDR=0x00000001` identified SMMUv3.1
while the model exposed v3.2/v3.3-era features such as `SMMU_S_IDR1.SEL2`,
`IDR3.RIL`, `IDR3.MPAM`, and `IDR0.ATSRECERR`.  QBox now reports
`ARCH_AIDR=0x00000003` and updates the Apollo Linux selftest constants to
`IDR3=0x00004f80` and `AIDR=0x00000003`.

The IDR3 surface now includes `FWB`, `STT`, `RIL`, `BBML==Level 1`, `E0PD`, and
`PTWNNC` while retaining `MPAM` and keeping `DPT` clear.  Component tests verify
these fields through `ArchitectedRegisterMmioSurface` and
`MpamDiscoveryAdvertisesVmsPrerequisites`.  Verification evidence is recorded in
`doc/verification/qbox-smmuv3-aidr-v33-idr3-mandatory-verification-2026-05-11.md`
and `build/verification/smmu-aidr-v33-idr3-mandatory-*20260511.*`.

The no-overclaim boundary remains unchanged: this is discovery alignment for the
already-modeled functional slices, not complete SMMUv3.3 E0PD/PTWNNC behavioral
parity, ECMDQ, DPT, RME/GPT/GPC, or upstream `arm-smmu-v3` lifecycle parity.

## 2026-05-11 SMMU-COMP-040/050/060 E0PD/PTWNNC behavior progress note

Added bounded behavior behind the SMMUv3.3 `IDR3.E0PD` and `IDR3.PTWNNC`
discovery bits.  QBox now decodes `CD.E0PD0`/`CD.E0PD1`, permits those fields in
context descriptors, rejects unprivileged stage-1 accesses before the descriptor
walk when the selected TTB half is E0PD-disabled, and records the resulting
stage-1 translation fault path.  Nested stage-1 CD/TT descriptor fetches that are
stage-2-translated through Device-mapped stage-2 descriptors are detected and
marked as PTWNNC Normal-Non-cacheable normalization instead of being rejected.

`CdE0pdBlocksUnprivilegedTtb0Access` verifies the E0PD fault and privileged
success path; `PtwnncNormalizesNestedStage1FetchDeviceMemory` verifies nested
stage-1 descriptor-fetch PTWNNC normalization.  Verification evidence is recorded
in `doc/verification/qbox-smmuv3-e0pd-ptwnnc-behavior-verification-2026-05-11.md`
and `build/verification/smmu-e0pd-ptwnnc-behavior-*20260511.*`.

The no-overclaim boundary remains unchanged: this is a bounded behavioral slice,
not complete TTB1 table selection, `STE.S2PTW` permission-fault behavior, DPT,
ECMDQ, RME/GPT/GPC, or upstream `arm-smmu-v3` lifecycle parity.

## 2026-05-11 SMMU-COMP-020/040/050/060 IDR3 HAD/XNX/BBML2 progress note

Closed a bounded discovery/behavior gap created by the SMMUv3.3 AIDR surface.
QBox now reports mandatory `SMMU_IDR3.HAD`, `SMMU_IDR3.XNX`, and
`BBML==Level 2`, updates the Apollo Linux probe expected IDR3 value to
`0x00005794`, accepts `CD.HAD0`/`CD.HAD1`, component-tests `CD.HAD0` disabling
stage-1 table-descriptor hierarchical APTable enforcement for an unprivileged
TTB0 access, and component-tests `IDR3.XNX` stage-2 unprivileged execute-never
permission faults for instruction transactions.

Evidence is recorded in
`doc/verification/qbox-smmuv3-idr3-had-xnx-bbml2-verification-2026-05-11.md`
and `build/verification/smmu-idr3-had-xnx-bbml2-*20260511.*`.  The slice is
still bounded: full hierarchical-attribute parity across all regimes, HTTU,
complete BBML reference-vector parity, DPT, ECMDQ, RME/GPT/GPC, and upstream
`arm-smmu-v3` lifecycle parity remain open.

## 2026-05-11 SMMU-COMP-040/050 BBML level-2 nT progress note

Implemented a bounded BBML level-2 block-descriptor `nT` slice.  The Apollo
SMMU architected core now tags block-leaf descriptor steps with `block_nt`, the
TBU names `ARCH_DESC_NT`, records `m_arch_last_bbml2_nt_ignored`, and logs that
`IDR3.BBML level-2` ignores a block descriptor `nT` bit.  The component test
`Idr3Bbml2IgnoresBlockNt` verifies that a 4K-granule block descriptor with
`nT==1` translates through the advertised BBML level-2 surface, does not report
`F_TLB_CONFLICT`, and returns the PA computed without treating bit 16 as output
address.

This narrows the BBML gap but remains a functional slice rather than full BBM
compliance.  Complete transition/reference-vector parity, full TLB multi-hit
resolution geometry, HTTU, DPT, ECMDQ, RME/GPT/GPC, and upstream Linux
`arm-smmu-v3` lifecycle parity remain open.  Evidence is recorded in
`doc/verification/qbox-smmuv3-bbml2-nt-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-040/050/060 HTTU AF/Dirty progress note

Implemented a bounded hardware translation table update slice.  QBox now names
`IDR0.HTTU`, `CD.HA`/`CD.HD`, `STE.S2HA`/`STE.S2HD`, and leaf descriptor `DBM`,
originally advertised the non-secure IDR0 AF/Dirty capability as `0x098db78b`
(the HAFT follow-up below supersedes discovery to `0x098db7cb`), and updates
stage-1 or stage-2 leaf descriptors in memory before the walker would otherwise
raise `F_ACCESS` or `F_PERMISSION`.  Component tests cover stage-1 CD-controlled
AF and dirty updates and stage-2 STE-controlled AF and dirty updates, while the
existing access/permission negative checks remain in
`ArchitectedWalkerGranuleBlockAndFaultMatrix` when HTTU is not enabled.

The slice remains bounded: table-descriptor AF/HAFT updates, full atomic update
ordering and TLB/coherency side effects, DPT, ECMDQ, RME/GPT/GPC, and upstream
Linux `arm-smmu-v3` lifecycle parity remain open.  Evidence is recorded in
`doc/verification/qbox-smmuv3-httu-af-dirty-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-040/050/060 HTTU HAFT progress note

Implemented the HAFT follow-up to the bounded HTTU AF/Dirty slice.  QBox now
advertises `IDR0.HTTU == 0b11` (`IDR0=0x098db7cb`) and models the architectural
HAFT controls `CD.HAFT` bit `[67]` and `STE.S2HAFT` bit `[187]`.  The descriptor
walker updates table-descriptor Access flags in memory before descriptor-step
evaluation when stage-1 `CD.HA && CD.HAFT` or stage-2 `STE.S2HA && STE.S2HAFT`
is enabled.  Component tests cover stage-1 and stage-2 table-descriptor AF
updates alongside the existing leaf AF/Dirty tests.

The slice remains bounded: full atomic/coherency ordering, full ATS/PRI HTTU
interaction coverage, DPT, ECMDQ, RME/GPT/GPC, and upstream Linux
`arm-smmu-v3` lifecycle parity remain open.  Evidence is recorded in
`doc/verification/qbox-smmuv3-httu-haft-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-040/050/060 STE.S2PTW Device fetch progress note

Implemented a bounded `STE.S2PTW` nested-fetch permission slice.  QBox now names
`ARCH_STE_S2PTW`, preserves VMID derivation by masking the bit out of the compact
modeled VMID helper, tracks the active S2PTW state, and rejects Device-mapped
stage-2 backing pages for nested context-descriptor and stage-1 translation-table
fetches as stage-2 Permission faults.  The existing PTWNNC behavior is retained
for the non-S2PTW path.

`S2ptwBlocksNestedCdFetchDeviceMemory` verifies Device-mapped CD fetch rejection,
`S2ptwBlocksNestedTtFetchDeviceMemory` verifies Device-mapped stage-1 table-fetch
rejection while the CD fetch is Normal NC, and
`PtwnncNormalizesNestedStage1FetchDeviceMemory` remains in the focused regression
set for the allowed normalization path.

The slice remains bounded: full DPT behavior, ECMDQ, RME/GPT/GPC security state
parity, complete upstream Linux `arm-smmu-v3` lifecycle parity, and broader
architected ordering/coherency interactions remain open.  Evidence is recorded in
`doc/verification/qbox-smmuv3-s2ptw-device-fetch-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-050/060 ATS DPT unsupported-as-disabled progress note

Corrected the bounded ATS handling for `STE.EATS==0b11` while `SMMU_IDR3.DPT`
remains clear.  The earlier QBox slice treated this as a synthetic failed DPT
check; the model now follows the architecture by folding the DPT EATS encoding to
`EATS disabled` when DPT is not implemented.  ATS Translated traffic still
terminates through the existing EATS-disabled `F_TRANSL_FORBIDDEN` path, and ATS
Translation Requests still return the existing unsupported-request response, but
neither path claims a real DPT lookup failure.

`AtsTranslatedDptUnsupportedActsAsDisabled` covers Translated traffic, and
`AtsTranslationRequestHonorsCr0AtschkAndSteEats` now also covers the ATS
Translation Request side.  Full DPT support remains open: DPT table walks,
`DPT_WALK_EN`, DPT TLB entries, `DPT_CFG_FAR`, Secure/Realm DPT separation,
maintenance completion semantics, and GPT/GPC ordering are not implemented.
Evidence is recorded in
`doc/verification/qbox-smmuv3-ats-dpt-unsupported-as-disabled-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-050/060 ATS Translation Request translation-fault progress note

Implemented a bounded ATS Translation Request response-semantics slice.  QBox now
recognizes translation-process Address Size, Access, Permission, table-invalid,
and page-invalid faults reached by `ARCH_CTRL_ATS_TRANSLATION_REQUEST` and
returns a modeled ATS Success completion with no access permissions (`R==W==0`)
while suppressing SMMU fault/EVENTQ recording.  Configuration, fetch, and
protocol errors remain on the existing UR/CA and `REC_CFG_ATS`-controlled event
paths.

`AtsTranslationRequestTranslationFaultReturnsSuccessNoEvent` verifies an AF-clear
page Access fault produces Success, no UR/CA, no EVENTQ entry, no fault-count
increment, no ATC fill, and a zero returned PA.  This narrows ATS §3.9.1.2
response parity but remains bounded: the full ATS completion permission matrix,
NW/write dirty-state permission reporting, DPT, ECMDQ, RME/GPT/GPC, and upstream
`arm-smmu-v3` lifecycle parity remain open.  Evidence is recorded in
`doc/verification/qbox-smmuv3-ats-treq-translation-fault-success-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-050/060 ATS Translation Request config-response progress note

Implemented a bounded ATS Translation Request response-code slice.  QBox now uses
an ATS-Translation-Request-specific response helper so configuration lookup
faults such as `C_BAD_STREAMID` return Completer Abort, while protocol/config
abort cases that raise `F_BAD_ATS_TREQ` continue to return Unsupported Request.
`STE.Config==0b100` is rejected on the ATS Translation Request path before the
normal bypass translation path can consume it.

`AtsTranslationRequestConfigFaultsUseArchitectedResponses` verifies
`C_BAD_STREAMID -> CA` with EVENTQ recording under `REC_CFG_ATS|RECINVSID`, and
`STE.Config==0b100 -> UR/F_BAD_ATS_TREQ`.  This narrows ATS §3.9.1.2 response
parity but remains bounded: complete ATS completion permission entries, PCIe
T/XT/CXL metadata, DPT, ECMDQ, RME/GPT/GPC, and upstream `arm-smmu-v3` lifecycle
parity remain open.  Evidence is recorded in
`doc/verification/qbox-smmuv3-ats-treq-config-response-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-040/050/060 ATS TR HTTU write-intent progress note

Implemented a bounded ATS Translation Request write-intent (`NW==0`) control path for
HTTU flag updates. The Apollo TBU now feeds ATS TR write intent through the existing
walker, so CD.HA/CD.HD leaf handling can set AF and mark DBM writable-clean pages
writable-dirty before a success response. The component test also covers the HA-only
case where dirty state is not enabled and the request stays on the modeled
success-with-no-write-permission path without EVENTQ recording.

Verification artifact: `doc/verification/qbox-smmuv3-ats-treq-httu-write-intent-verification-2026-05-11.md`.

## 2026-05-11 SMMU-COMP-050/060 ATS TR substream CA progress note

Implemented a bounded ATS Translation Request configuration-error matrix update for
substream faults. `C_BAD_SUBSTREAMID` and S1DSS-derived `F_STREAM_DISABLED` now
return Completer Abort (`CA`) and record EVENTQ entries when `REC_CFG_ATS` is set,
while the earlier `STE.Config==0` disabled-stream case remains UR/no-event.

Verification artifact: `doc/verification/qbox-smmuv3-ats-treq-substream-ca-verification-2026-05-11.md`.
