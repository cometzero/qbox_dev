# QBox SMMUv3 compliance checklist

- Date: 2026-05-10
- Scope: `/build/qbox_dev`
- Source plan: `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`
- Checker: `scripts/check_qbox_smmuv3_compliance.py`

This checklist is the SMMU-COMP-000 gate for the reviewed QBox SMMUv3
compliance plan. It is intentionally conservative: runtime smoke can prove the
Apollo/QBox compatibility slice, but it must not be treated as full ARM SMMUv3
compliance without passing model/unit, platform/DTS/IRQ, and runtime evidence.

## Status vocabulary

| Status | Meaning |
| --- | --- |
| `implemented` | The row's own deliverable is present and machine-checkable in this repository. |
| `functional-slice` | A useful QBox integration slice exists, but the architected SMMUv3 behavior is incomplete. |
| `reference-only` | Ground-truth/reference material exists; QBox has not implemented the behavior. |
| `missing` | The feature is not implemented in QBox beyond adjacent wiring or plans. |
| `blocked` | The feature is intentionally blocked by a named prerequisite. |

## Human-readable summary

| ID | Status | Owner | Summary |
| --- | --- | --- | --- |
| SMMU-COMP-000 | implemented | superproject docs/scripts | Checklist/checker and no-overclaiming gate are present. |
| SMMU-COMP-010 | functional-slice | QBox Apollo TBU | Apollo TBU now owns a small architected core ownership object while preserving the compatibility adapter, with CMDQ/EVENTQ/PRIQ, stream/context selector, walker, fault/replay scalar state, STAG stall-record table storage, endpoint replay payload record storage, allocation/retirement transitions, redrive payload/status transitions, downstream replay transaction request/result wrapping, a swappable adapter descriptor/replay I/O executor interface, descriptor-walk validation/fetch planning/step classification, descriptor-fetch lifecycle/fault capture, descriptor memory-read request/result wrapping, plus queue, walker geometry, STE/CD descriptor decode, EVENTQ fault-record layout, replay/status packing, stall-record lookup, and endpoint replay lookup/reset helpers moved behind that core boundary; the default executor still performs physical descriptor memory reads and endpoint replay downstream b_transport I/O in the adapter, and QEMU-bridge extraction remains future work. |
| SMMU-COMP-020 | functional-slice | QBox Apollo TBU + Linux probe | Apollo TBU now exposes a guest-visible, compatibility-preserving SMMUv3 register/queue aperture including architected IIDR/AIDR Page 0 slots, IDR5 4K/16K/64K plus 48-bit OAS discovery, and the non-secure SMMU_GATOS RUN/PAR register path with ATOS_ADDR.PnU/InD/RnW decode and architected ATOS_PAR STE-output-override suppression plus a non-advertised internal VATOS/S_VATOS stage-1-only model with independent GATOS/VATOS PAR state, STE.S2VMID-derived walker tagging, SMMU_VATOS_SEL VMID-scope rejection, and IDR0.VATOS kept clear, plus Secure SMMU_S_GATOS RUN/PAR banking including S_GATOS_SID.SSEC Secure-vs-Non-secure stream selection and SMMU_S_* Secure page with independent Secure STRTAB/CMDQ/EVENTQ/PRIQ bank state, memory-backed Secure CMDQ fetch/consume for selected commands plus modeled CFGI/TLBI/ATC SSec security-state routing, Non-secure SSec CERROR_ILL, Secure ATC_INV_SYNC CERROR pause/skip/recovery plus Secure CMD_SYNC MSI success/abort/GERRORN acknowledgement plus Secure CMD_SYNC S_IRQ_CTRL visibility plus Secure EVENTQ/PRIQ/GERROR MSI bank routing/abort reporting, and component-tested CFGI/TLBI/ATC invalidation, including ASID/VMID/SSID-tagged cache targeting, modeled TLBI_NH_VA/TLBI_NH_VAA range invalidation plus reserved NUM/SCALE/TG CERROR_ILL rejection, IDR0.ATS/PRI advertisement for modeled ATC/PRI command support, IDR3.RIL advertisement with Linux >64KB SG-DMA TLBI_NH_VA range-command stress, modeled additional TLBI opcode coverage for NSNH/EL2/EL3/S12/S2 with scoped TLBI_NSNH_ALL invalidation preserving modeled EL2-regime entries, Secure-only S-EL2/S-S12/S-S2/SNH TLBI opcode coverage, TTL/Leaf hint accounting, modeled TTL/TG leaf-level filtering, and Leaf=0 table-walk cache invalidation accounting, IDR3.MPAM/MPAMIDR VMS discovery, CD.PARTID/PMG VMS PARTID_MAP remap plus STE.PARTID/PMG fallback assignment into downstream TLM MPAM attributes with MPAMIDR range-to-UNKNOWN handling and GBPA disabled-SMMU output attributes plus abort policy, unsupported AGBPA RES0/WI policy, and GBPMPAM global-bypass assignment plus GMPAM queue/MSI write, CMDQ/STE/VMS fetch attributes, STE-sourced CD fetch attributes, client-derived TT fetch attributes, and security-state-derived MPAM PARTID-space tagging plus Secure GBPMPAM/GMPAM register-bank attribute selection, CMD_CFGI_VMS_PIDM modeled VMS/PARTID_MAP invalidation, Linux guest-driven ATC_INV/TLBI_NH_ALL and RIL TLBI_NH_VA range-command stress plus component-tested additional and Secure-only TLBI opcode coverage, spec-position CR0 CMDQ/EVENTQ/PRIQ enable gates, EVENTQ/PRIQ OVFLG/OVACKFLG overflow flags, architected EVENTQ_ABT_ERR/PRIQ_ABT_ERR queue-write abort bits, IDR1.ECMDQ/S_IDR0.ECMDQ=0 IDR6/S_IDR6 and ECMDQ control-page RES0/WI policy, IDR3.DPT=0 DPT register RES0/WI policy plus DPTI command rejection with CMDQ_CONS.CERROR_ILL, unconfigured CMDQ abort reporting with CMDQ_CONS.CERROR_ABT, and modeled failed CMD_ATC_INV completion reporting with CMDQ_CONS.CERROR_ATC_INV_SYNC on CMD_SYNC, including multi-outstanding coalescing plus queue pause/skip/recovery coverage; full command/event/PRI semantics remain open, including remaining Realm/RME command encodings and security-state parameters beyond modeled Secure CFGI/TLBI/ATC SSec/Secure-only TLBI slices and remaining Secure IRQ/MSI ordering parity beyond the modeled CMD_SYNC/EVENTQ/PRIQ/GERROR paths. |
| SMMU-COMP-030 | functional-slice | QBox Apollo TBU + Linux probe | Bounded linear/2-level STRTAB StreamID selection, S1CDMax-bounded linear/64K-L2 CD-table SSID indexing, nested CD/L1CD and stage-1 TT descriptor-fetch IPA stage-2 translation, modeled S1DSS/substream descriptor faults to F_STREAM_DISABLED/C_BAD_SUBSTREAMID, STE.Config==0 no-event termination, no-substream S1DSS terminate/bypass including nested S2 after bypass, modeled STE output-attribute propagation on context-bypass, STE.Config all-bypass, stage-1/stage-2/nested translation, ATS Translated payload paths, the bounded GATOS_PAR return path, the architected non-secure SMMU_GATOS register group RUN/PAR/no-event ATOS path, the Secure SMMU_S_GATOS RUN/PAR/no-event ATOS path with S_GATOS_SID.SSEC Secure-vs-Non-secure stream selection, bounded ATOS_ADDR.TYPE reserved/INV_STAGE/nested stage-selection coverage, ATOS_ADDR.PnU/InD access-field decode with STE output-override suppression on architected ATOS_PAR success, and a non-advertised internal VATOS/S_VATOS stage-1-only model with GATOS/VATOS PAR isolation plus SMMU_VATOS_SEL-to-STE.S2VMID rejection, endpoint PASID/SSID TLM propagation, modeled STE/CD reserved/illegal encoding faults, configured Secure stream-table bank selection through guest-visible SMMU_S_STRTAB_BASE registers, Secure stage-2-only NSCFG/S_S2TTB selection, Secure nested stage-1-derived NSIPA-to-S2TTB/S_S2TTB selection, and Secure nested stage-1 TT-fetch S2TTB/S_S2TTB selection and STE.S2R/S2S stage-2 fault record/stall policy plus terminate-only STALL_MODEL validation are covered; full PCIe PASID/CD invalidation parity, guest-visible complete VATOS/S_VATOS, remaining ATOS_ADDR fields beyond TYPE/RnW/PnU/InD and full attribute parity, and partial ATOS register parity beyond the modeled non-secure/Secure GATOS slices, remaining Secure command lifecycle parity beyond the modeled memory-backed S_CMDQ fetch/sync/invalidation/error-recovery/MSI slice, complete Root/Realm RME/GPT/GPC policy, full Arm reserved-matrix parity, and true upstream arm-smmu-v3 CD invalidation lifecycle remain open. |
| SMMU-COMP-040 | functional-slice | QBox Apollo TBU | Selected 4K/16K/64K granule, command TLBI range invalidation, IDR3.RIL Linux range-command stress, modeled additional NSNH/EL2/EL3/S12/S2 plus scoped TLBI_NSNH_ALL invalidation and Secure-only S-EL2/S-S12/S-S2/SNH TLBI opcode coverage, reserved range encoding rejection, TTL/TG leaf-level filtering, and Leaf=0 table-walk cache invalidation accounting, block/page, AF/permission, stage-2, nested CD/L1CD/TT-fetch/S2, nested S1+S2 including Secure stage-1-derived IPA-space and Secure stage-1 TT-fetch S2TTB/S_S2TTB selection, and nested S1DSS-bypass/S2 walker vectors are component-tested; full reference-vector parity remains open. |
| SMMU-COMP-050 | functional-slice | QBox Apollo TBU + Linux probe | Architected common EVENTQ event numbers/substream fields including modeled F_STREAM_DISABLED/C_BAD_SUBSTREAMID for S1DSS/substream faults with C_BAD_SUBSTREAMID InputAddr payload validation, F_TRANSL_FORBIDDEN for SMMUEN/ATSCHK/EATS rejected Translated transactions, ATS Translated address-size no-event abort behavior, stage-2-only and architected nested split-stage ATS Translated IPA walks plus modeled STE.PRIVCFG/INSTCFG effective access overrides before the nested stage-2-only walk plus implementation-defined rejection for unsupported non-stage2/non-nested split-stage traffic, STE.Config==0b100 F_TRANSL_FORBIDDEN aborts, DPT register RES0/WI policy plus DPT EATS unsupported F_TRANSL_FORBIDDEN aborts, PASIDTT-disabled SSV/PnU/InD clearing, ATSCHK==0 Translated configuration-lookup bypass, partial ATS Translated event-priority validation for C_BAD_STREAMID/F_STE_FETCH/C_BAD_STE/F_VMS_FETCH before F_TRANSL_FORBIDDEN, CR2.REC_CFG_ATS-gated ATS Translated configuration-fault records, and modeled F_TLB_CONFLICT/F_CFG_CONFLICT event-number plus implementation-defined word3 Reason payload plumbing for conflict reports plus component-tested ATS/TLB cache-conflict detection/recovery and STE configuration-cache conflict detection/recovery, modeled F_UUT unsupported-upstream event-number plus zero-Reason injection, unsupported security-state rejection, and EVENTQ security-state route accounting plus per-state logical bank mirrors and configured Secure-bank routing for modeled Secure fault events plus invalid-state events routed by masked Root event-state accounting, C_BAD_STREAMID CR2.RECINVSID event-recording suppression for normal probes, non-stall C_BAD_STREAMID/C_BAD_STE/C_BAD_CD/F_STREAM_DISABLED RES0 payload encoding, suppresses EVENTQ records for valid STE.Config==0 disabled-stream aborts, STE.S2R/S2S-controlled stage-2 fault record/stall behavior including terminate-only STALL_MODEL invalid-STE validation, syndrome detail via private status, modeled PnU/InD/RnW plus CLASS=IN/TT/CD access class attributes for stalled translation faults, stage-2 IPA word3 layout including nested CD/L1CD and TT fetch translation failures, modeled NSIPA bit plumbing for supplied stalled stage-2 records, modeled STE/CD/F_WALK_EABT/F_VMS_FETCH fetch-address word3 layout plus actual STE.VMSPtr-triggered F_VMS_FETCH recording, IDR3.MPAM/MPAMIDR VMS discovery, full 64-byte VMS PARTID_MAP fetch/cache fill, CD.PARTID/PMG VMS PARTID_MAP remap plus STE.PARTID/PMG fallback assignment into downstream TLM MPAM attributes with MPAMIDR range-to-UNKNOWN handling and GBPMPAM global-bypass assignment plus security-state-derived MPAM PARTID-space tagging plus Secure GBPMPAM/GMPAM register-bank attribute selection, modeled GPCF bit plumbing for fetch-event records, stall-pending state, STAG/STALL bits, StreamID+STAG matched CMD_RESUME, stream-wide CMD_STALL_TERM, duplicate stalled-fault suppression/merge, endpoint early retry without duplicate EVENTQ records while preserving CMD_RESUME acknowledgement plus stale uncommitted EVENTQ discard, negative replay matrix coverage, endpoint replay accounting, downstream replay transaction wrapping plus payload re-drive, and opt-in caller blocking until CMD_RESUME retry, overflow retention, CR0.EVENTQEN gating, EVENTQ OVFLG/OVACKFLG overflow acknowledgement, EVENTQ_ABT_ERR queue-write abort reporting, and full-queue stall-event buffering/redrive preserves the original security-state route when records are buffered before redrive; bounded CD.E0PD unprivileged translation-fault behavior and PTWNNC nested descriptor-fetch normalization are component-tested; full event matrix parity, full Secure event-queue/security-state routing beyond SMMU_S_EVENTQ bank routing, full RME/GPT/GPC, broader real-hardware configuration-cache geometry parity, and upstream arm-smmu-v3 recovery parity remain open. |
| SMMU-COMP-060 | functional-slice | QBox Apollo TBU + Linux probe | ATS success/UR/CA outcomes including STE.Config==0 UR without EVENTQ recording, PRG-tagged PRI pending, CMD_PRI_RESP head-ordered exact-PRG/StreamID/PASID clear/reject/unknown plus SMMUEN-disabled no-op, PRIQ_CONS advancement, and reserved-code CERROR_ILL handling, Secure CMDQ CMD_PRI_RESP Non-secure StreamID handling, IDR0.ATS/PRI advertisement plus explicit unsupported-command guards, PRIQ OVFLG/OVACKFLG overflow acknowledgement, PRIQ_ABT_ERR queue-write abort reporting, automatic PRI success response for no-PASID Last PPR overflow, STE.PPAR-driven PASID-prefixed overflow response selection with REC_CFG_ATS/RECINVSID-gated lookup-fault recording, plus failure responses for Secure-stream, invalid STE.PPAR lookup, disabled, and abort-active cases, modeled PRI PPR SSV/Last/R/W/X/Priv metadata, PRI PRGIndex 9-bit allocation/encoding/head-ordered response matching plus PRIQ_CONS advancement, Stop PASID Marker no-response handling, non-last overflow discard without auto-response, and incoming PPR enqueue independence from CR0.ATSCHK/STE.EATS, CR0.ATSCHK plus STE.EATS ATS Translation Request gates including architected nested split-stage IPA walks, ATS Translation Request translation faults returned as Success with R==W==0 and no SMMU event, ATS Translation Request configuration lookup faults returned as Completer Abort and STE.Config abort returned as Unsupported Request with F_BAD_ATS_TREQ, ATS Translation Request write intent (NW==0) drives HTTU dirty updates for writable-clean DBM pages and HA-only write intent returns modeled W==0/no-event, modeled ATS Translated rejection with F_TRANSL_FORBIDDEN plus address-size no-event abort behavior, stage-2-only and architected nested split-stage ATS Translated IPA walks plus modeled STE.PRIVCFG/INSTCFG effective access overrides before the nested stage-2-only walk plus implementation-defined rejection for unsupported non-stage2/non-nested split-stage traffic, STE.Config==0b100 F_TRANSL_FORBIDDEN aborts, DPT register RES0/WI policy plus DPT EATS unsupported F_TRANSL_FORBIDDEN aborts, PASIDTT-disabled SSV/PnU/InD clearing, and ATSCHK==0 configuration-lookup bypass, CR2.REC_CFG_ATS-gated ATS Translated configuration-fault recording, partial Translated event-priority validation including F_VMS_FETCH from a modeled STE.VMSPtr path, and CR2.REC_CFG_ATS/RECINVSID recording gates are component/Linux-probed; bounded E0PD/PTWNNC behavior is covered for the advertised SMMUv3.3 surface; full packet protocol and ECMDQ protocol remain open. |
| SMMU-COMP-070 | functional-slice | QBox platform + Apollo TBU + Linux probe | Apollo TBU now has signal-level EVENTQ/PRIQ/CMDQ_SYNC/GERROR IRQ outputs, masks unsupported IRQ_CTRL bits into IRQ_CTRLACK, exposes raw GERROR toggle state, models GERROR/GERRORN active-bit toggle acknowledgement, reports architected EVENTQ_ABT_ERR/PRIQ_ABT_ERR queue-abort bits, component-tests MSI IRQ_CFG registers, CMD_SYNC MSI writes, MSI abort GERROR bits, Secure CMD_SYNC wired visibility through S_IRQ_CTRL/S_IRQ_CTRLACK, Secure EVENTQ MSI routing through S_EVENTQ_IRQ_CFG/S_GERROR, Secure PRIQ MSI routing through S_PRIQ_IRQ_CFG/S_GERROR.MSI_PRIQ_ABORT, and Secure GERROR MSI routing through S_GERROR_IRQ_CFG/S_GERROR.MSI_GERROR_ABORT, drives Apollo Hexagon DMA async fence doorbell signals into Linux-visible SPIs, and the Linux probe binds the doorbell IRQ and waits on interrupt-driven fence completion before polling fallback; full GIC/MSI ordering and upstream arm-smmu-v3 lifecycle remain open. |
| SMMU-COMP-080 | functional-slice | QBox Apollo TBU + DMA | TLM StreamID plus endpoint PASID/SSID propagation and modeled STE output attributes for context-bypass, STE.Config all-bypass, stage-1/stage-2/nested translation, ATS Translated payload paths, the bounded GATOS_PAR return path, the architected non-secure SMMU_GATOS register group RUN/PAR/no-event ATOS path, the Secure SMMU_S_GATOS RUN/PAR/no-event ATOS path with S_GATOS_SID.SSEC Secure-vs-Non-secure stream selection, bounded ATOS_ADDR.TYPE stage-selection on SMMU_GATOS, ATOS_ADDR.PnU/InD access-field decode with STE output-override suppression on architected ATOS_PAR success, a non-advertised internal VATOS/S_VATOS stage-1-only model with GATOS/VATOS PAR isolation plus VMID-scoped VATOS rejection, per-SID/SSID ATS tagging, per-SID map/cache isolation, SID/page/global plus ASID/VMID/SSID-tagged command invalidation, Linux guest ATC_INV/TLBI_NH_ALL plus RIL TLBI_NH_VA range-command stress coverage, and a second Linux-visible StreamID 0x2 DMA master are present; full PCIe/RID topology remains open. |
| SMMU-COMP-090 | functional-slice | guest tools/IREE staging | `iree-run-module --device=apollo-hexagon` now dispatches through a repo-local upstream-style HAL registry frontend that dynamically loads/registers the staged Apollo Hexagon C HAL plugin; upstream IREE source checkout is configured under `sources/iree`, while Apollo HAL build/registry integration remains open. |
| SMMU-REF-000 | reference-only | `sources/smmu` | Pinned reference corpus exists, with one known C++ test failure. |

## Machine-readable checklist

<!-- QBOX_SMMUV3_CHECKLIST_JSON_BEGIN -->
```json
{
  "version": 1,
  "allowed_statuses": [
    "implemented",
    "functional-slice",
    "reference-only",
    "missing",
    "blocked"
  ],
  "known_reference_failures": [
    {
      "id": "REF-FAIL-CPP-STALL-PENDING",
      "path": "build/verification/smmu-reference-cpp-v1.7.8-build-20260510.log",
      "pattern": "test_bug3_stall_pending_fields",
      "description": "Pinned sources/smmu C++ reference has one known failing stall-pending regression test."
    }
  ],
  "rows": [
    {
      "id": "SMMU-COMP-000",
      "title": "Inventory/checklist/no-overclaiming gate",
      "status": "implemented",
      "owner": "superproject docs/scripts",
      "claim_scope": "Compliance inventory only; not SMMUv3 feature compliance.",
      "source_evidence": [
        {
          "path": "doc/spec/qbox-smmuv3-compliance-checklist.md",
          "pattern": "QBOX_SMMUV3_CHECKLIST_JSON_BEGIN",
          "description": "Machine-readable checklist is embedded in this document."
        },
        {
          "path": "scripts/check_qbox_smmuv3_compliance.py",
          "pattern": "QBOX_SMMUV3_CHECKLIST_JSON_BEGIN",
          "description": "Checker parses this checklist and validates evidence/platform invariants."
        },
        {
          "path": "doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md",
          "pattern": "Backlog verification matrix",
          "description": "Reviewed plan contains per-backlog verification gates."
        }
      ]
    },
    {
      "id": "SMMU-COMP-010",
      "title": "Compatibility ABI and canonical Apollo TBU ownership",
      "status": "functional-slice",
      "owner": "sources/qbox/systemc-components/apollo_smmu_tbu",
      "claim_scope": "Apollo TBU owns an architected core contract object for canonical SystemC ownership plus register/queue, STE/CD, walker, and replay-state ownership metadata, routes the guest-visible SMMUv3 register aperture through that core, stores CMDQ/EVENTQ/PRIQ, stream/context selector, walker state, fault/replay scalar protocol state, STAG stall-record table storage, and endpoint replay payload record storage behind that core boundary, and factors queue helpers, walker geometry helpers, descriptor-walk validation/fetch planning/step classification, descriptor-fetch lifecycle/fault capture, descriptor memory-read request/result wrapping, pure STE/CD descriptor decode helpers, EVENTQ fault-record layout, replay/status packing helpers, stall-record lookup helpers, endpoint replay record lookup/reset helpers, endpoint replay allocation/retirement state transitions, endpoint replay redrive payload/status state transitions, endpoint replay downstream transaction request/result wrapping, and a swappable adapter descriptor/replay I/O executor interface behind the same boundary while preserving the compatibility adapter; the default executor still performs physical descriptor memory reads and endpoint replay b_transport side effects in the adapter, and any QEMU translation bridge remains pending.",
      "source_evidence": [
        {
          "path": "doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md",
          "pattern": "Ownership contract and platform invariants",
          "description": "Plan names Apollo TBU/SystemC core as canonical Hexagon DMA translation owner until a QEMU bridge is verified."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "apollo_smmu_tbu",
          "description": "Current TBU compatibility model exists."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_arch_core.h",
          "pattern": "cmdq_state\\(\\)",
          "description": "Architected core object records canonical owner, compatibility adapter, state ownership contracts, CMDQ/EVENTQ/PRIQ queue state storage, stream/context selector state storage, walker state storage, fault/replay scalar protocol state storage, STAG stall-record table storage, endpoint replay payload record storage, queue/walker geometry helpers, descriptor-walk validation/fetch planning/step classification helpers, descriptor-fetch lifecycle/fault capture helpers, descriptor memory-read request/result wrapping helpers, pure Stream-table/STE/CD descriptor decode helpers, EVENTQ fault-record layout helpers, replay/status packing helpers, stall-record lookup helpers, endpoint replay lookup/reset helpers, endpoint replay allocation/retirement state transition helpers, endpoint replay redrive payload/status transition helpers, endpoint replay downstream transaction request/result wrapping helpers, and adapter-side descriptor/replay I/O executor request helpers."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "class arch_io_executor",
          "description": "Apollo TBU isolates adapter-executed descriptor memory reads and endpoint replay b_transport I/O behind a swappable executor interface fed by architected core request objects."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedCoreOwnsCanonicalTranslationState",
          "description": "Component test asserts the canonical SystemC owner, compatibility adapter contract, state-ownership metadata, register aperture classification, and core-owned queue/stream/walker/fault-replay state aliasing."
        }
      ],
      "runtime_evidence": [
        {
          "path": "doc/verification/qbox-smmu-stream-context-replay-2026-05-10.md",
          "pattern": "compliance-oriented integration slice",
          "description": "Existing runtime report scopes the current behavior as a compatibility/compliance-oriented slice."
        },
        {
          "path": "doc/verification/qbox-smmuv3-core-owner-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-010 architected core ownership functional slice",
          "description": "Verification report records build, component test, lane, and static checker evidence for the core ownership and register-routing contract."
        }
      ]
    },
    {
      "id": "SMMU-COMP-020",
      "title": "Architected register file and memory-backed queues",
      "status": "functional-slice",
      "owner": "sources/qbox/systemc-components/apollo_smmu_tbu + Apollo Linux probe",
      "claim_scope": "Apollo TBU exposes an initial guest-visible architected SMMUv3 register/queue aperture at offset 0x1000 including the non-secure SMMU_GATOS_CTRL/SID/ADDR/PAR RUN-to-PAR register path with modeled ATOS_ADDR.TYPE/RnW/PnU/InD decode plus architected ATOS_PAR STE-output-override suppression and the SMMU_S_* Secure page with Secure SMMU_S_GATOS RUN/PAR completion through S_GATOS_SID.SSEC Secure-vs-Non-secure stream selection and the Secure CR0/STRTAB bank at offset 0x8000 with independent Secure STRTAB/CMDQ/EVENTQ/PRIQ bank state and memory-backed Secure CMDQ fetch/consume for selected commands plus modeled CFGI/TLBI/ATC SSec security-state routing, Non-secure SSec CERROR_ILL, Secure ATC_INV_SYNC CERROR pause/skip/recovery plus Secure CMD_SYNC MSI success/abort/GERRORN acknowledgement plus Secure CMD_SYNC S_IRQ_CTRL visibility plus Secure EVENTQ/PRIQ/GERROR MSI bank routing/abort reporting, and now component-tests CFGI/TLBI/ATC invalidation side effects, including ASID/VMID/SSID-tagged targeting, modeled TLBI_NH_VA/TLBI_NH_VAA range invalidation plus reserved NUM/SCALE/TG CERROR_ILL rejection, IDR0.ATS/PRI advertisement for modeled ATC/PRI command support, IDR3.RIL advertisement with Linux >64KB SG-DMA TLBI_NH_VA range-command stress, modeled additional TLBI opcode coverage for NSNH/EL2/EL3/S12/S2 with scoped TLBI_NSNH_ALL invalidation preserving modeled EL2-regime entries, Secure-only S-EL2/S-S12/S-S2/SNH TLBI opcode coverage, TTL/Leaf hint accounting, modeled TTL/TG leaf-level filtering, and Leaf=0 table-walk cache invalidation accounting, IDR3.MPAM/MPAMIDR VMS discovery, CD.PARTID/PMG VMS PARTID_MAP remap plus STE.PARTID/PMG fallback assignment into downstream TLM MPAM attributes with MPAMIDR range-to-UNKNOWN handling and GBPMPAM global-bypass assignment plus GMPAM queue/MSI write, CMDQ/STE/VMS fetch attributes, STE-sourced CD fetch attributes, S1MPAM CD/helper-walk STE attributes before CD/VMS override, client-derived TT fetch attributes, and ATS Translated ATSCHK-disabled GBPMPAM plus ATSCHK-enabled STE/CD-sourced MPAM attributes, CMD_CFGI_VMS_PIDM modeled VMS/PARTID_MAP invalidation, spec-position CR0 SMMUEN/PRIQEN/EVENTQEN/CMDQEN gates, EVENTQ/PRIQ OVFLG/OVACKFLG overflow acknowledgement flags, architected EVENTQ_ABT_ERR/PRIQ_ABT_ERR queue-write abort bits, IDR1.ECMDQ/S_IDR0.ECMDQ=0 ECMDQ discovery/control-page RES0/WI policy, IDR3.DPT=0 CMD_DPTI_ALL/CMD_DPTI_PA rejection with CMDQ_CONS.CERROR_ILL plus GERROR signaling, unconfigured CMDQ abort reporting with CMDQ_CONS.CERROR_ABT, and modeled failed CMD_ATC_INV completion reporting with CMDQ_CONS.CERROR_ATC_INV_SYNC on CMD_SYNC, including multi-outstanding coalescing plus queue pause/skip/recovery coverage. The Linux guest probe also enables the CR0 queue gates, drives CMDQ ATC_INV and TLBI_NH_ALL through the guest-visible queue, the guest DMA stress path drives a RIL TLBI_NH_VA range command after >64KB SG traffic, verifies the modeled invalidation counter, component tests exercise additional TLBI NSNH/EL2/EL3/S12/S2 with scoped TLBI_NSNH_ALL invalidation and Secure-only S-EL2/S-S12/S-S2/SNH opcodes, and validates CMD_DPTI_ALL is rejected because DPT is not advertised. This is not full CMDQ/EVENTQ/PRIQ or DPT compliance. The slice also includes explicit security-state-derived MPAM PARTID-space tagging plus Secure GBPMPAM/GMPAM register-bank attribute selection in the Apollo SMMU TLM extension/status for modeled Non-secure, Secure, Realm, and Root endpoint states.",
      "source_evidence": [
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "REG_SMMUV3_BASE = 0x1000",
          "description": "Compatibility-preserving SMMUv3 register aperture base."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "process_cmdq",
          "description": "Initial memory-backed CMDQ ring processing helper."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "push_arch_queue_record",
          "description": "Shared EVENTQ/PRIQ record push helper with wrap/overflow checks."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdqProducerWriteConsumesMemoryBackedCommands",
          "description": "CTest/gTest unit coverage exercises the register socket, ring helpers, memory-backed CMDQ, EVENTQ, PRIQ, and overflow/GERROR ack behavior."
        },
        {
          "path": "build/verification/apollo-smmu-tbu-smmu-comp-020-final-build-20260510.log",
          "pattern": "Built target apollo_smmu_tbu",
          "description": "Apollo TBU target rebuild after SMMU-COMP-020 functional slice."
        },
        {
          "path": "build/verification/apollo-smmu-tbu-reg-queue-test-build-20260510.log",
          "pattern": "Built target apollo-smmu-tbu-tests",
          "description": "Apollo SMMUv3 reg/queue unit-test target builds successfully."
        },
        {
          "path": "sources/qbox/platforms/buildroot/conf_aarch64.lua",
          "pattern": "size=0x10000, bind = \"&router.initiator_socket\"",
          "description": "QBox platform exposes enough Apollo TBU MMIO space for the compatibility registers, SMMUv3 page 0 at relative offset 0x1000, and the SMMU_S_* Secure page at relative offset 0x9000."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "SMMUV3_SECURE_PAGE = 0x8000",
          "description": "Apollo TBU decodes the architected SMMU_S_* Secure register page at the SMMUv3 PAGE_0 + 0x8000 offset."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "read_smmuv3_secure_reg",
          "description": "Secure page reads expose S_IDR1.SECURE_IMPL/SEL2 and independent Secure STRTAB, CMDQ, and EVENTQ bank state."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureRegisterBankConfiguresStrtabCmdqAndEventq",
          "description": "Component test verifies guest-visible SMMU_S_* writes configure independent Secure STRTAB, CMDQ, and EVENTQ banks without clobbering Non-secure state."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "process_secure_cmdq",
          "description": "Secure CMDQ producer writes now fetch and consume memory-backed SMMU_S_CMDQ entries when Secure CR0 enables the queue."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureCmdqProducerConsumesMemoryBackedCommands",
          "description": "Component test verifies Secure CMDQ gating, command fetch, CMD_SYNC/ATC_INV processing, ATS invalidation, and Non-secure CMDQ isolation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_CMDQ_SSEC",
          "description": "Apollo TBU decodes the modeled architected SSec bit for command-queue entries."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureCmdqSsecCfgiTargetsSelectedSecurityState",
          "description": "Component test verifies S_CMDQ CFGI_STE with SSec=1 invalidates Secure configuration-cache state while SSec=0 targets Non-secure state."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "NonSecureCmdqSsecCfgiIsIllegal",
          "description": "Component test verifies Non-secure CMDQ with SSec=1 raises CERROR_ILL and does not invalidate Secure configuration state."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureCmdqAtcInvSyncCerrorPausesAndRecovers",
          "description": "Component test verifies Secure ATC_INV completion failures pause on S_CMD_SYNC with CERROR_ATC_INV_SYNC and recover after software skips the failed sync via S_CMDQ_CONS."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureCmdSyncMsiWriteAndAbortAreReported",
          "description": "Component test verifies Secure CMD_SYNC CS=IRQ MSI write success, failed MSI abort accounting through S_GERROR.MSI_CMDQ_ABORT, S_GERRORN acknowledgement, shared IRQ status, and Non-secure GERROR isolation."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureCmdSyncIrqUsesSecureCtrlBank",
          "description": "Component test verifies Secure S_CMD_SYNC completion IRQ status is exposed through S_IRQ_CTRL/S_IRQ_CTRLACK rather than the Non-secure IRQ_CTRL bank."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureEventqMsiAndAbortUseSecureBank",
          "description": "Component test verifies Secure EVENTQ IRQ/MSI uses S_EVENTQ_IRQ_CFG, reports failed Secure EVENTQ MSI writes through S_GERROR.MSI_EVENTQ_ABORT, and preserves Non-secure EVENTQ/GERROR isolation."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecurePriqMsiAndAbortUseSecureBank",
          "description": "Component test verifies Secure PRIQ records and IRQ/MSI use S_PRIQ/S_PRIQ_IRQ_CFG, reports failed Secure PRIQ MSI writes through S_GERROR.MSI_PRIQ_ABORT, and preserves Non-secure PRIQ/GERROR isolation."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureGerrorMsiAndAbortUseSecureBank",
          "description": "Component test verifies Secure GERROR IRQ/MSI uses S_GERROR_IRQ_CFG, reports failed Secure GERROR MSI writes through S_GERROR.MSI_GERROR_ABORT, and preserves Non-secure GERROR isolation."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-selftest.c",
          "pattern": "SMMUv3 architected queue register selftest",
          "description": "Linux probe configures guest-visible CMDQ/EVENTQ/PRIQ rings and verifies queue side effects through MMIO."
        },
        {
          "path": "scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh",
          "pattern": "SMMUv3 architected queue",
          "description": "Hexagon guest smoke requires a robust guest-visible architected queue selftest marker; APOLLO UART output may interleave later words."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "FEATURE_ARCH_CMD_INVALIDATION",
          "description": "Apollo TBU advertises the command-driven invalidation functional slice."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "handle_cmdq_atc_inv",
          "description": "CMDQ ATC_INV invalidates modeled ATS cache entries by SID/page/global scope."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdqInvalidationCommandsClearAtsBySidPageAndGlobal",
          "description": "Component test covers CFGI_STE, TLBI_NH_VA, per-SID ATC_INV, and global ATC_INV cache invalidation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "FEATURE_ARCH_TAGGED_INVALIDATION",
          "description": "Apollo TBU advertises the ASID/VMID/SSID-tagged invalidation functional slice."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_CMDQ_TLBI_ASID_SHIFT",
          "description": "CMDQ TLBI decoding extracts the architected ASID/VMID tag fields used by the functional slice."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdqTaggedInvalidationHonorsAsidVmidAndSsid",
          "description": "Component test covers ASID/VMID-tagged TLBI and SSID-scoped ATC_INV invalidation behavior."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-selftest.c",
          "pattern": "SMMUv3 command invalidation selftest ok",
          "description": "Linux probe drives guest-visible CMDQ ATC_INV/TLBI_NH_ALL and verifies the invalidation counter."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "FEATURE_ARCH_CR0_QUEUE_GATES",
          "description": "Apollo TBU advertises spec-position CR0 queue enable gate enforcement."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "Cr0QueueEnableGatesCmdEventAndPriQueues",
          "description": "Component test proves CMDQ/EVENTQ/PRIQ do not advance while CR0 gates are disabled and do advance after SMMUEN plus queue enable bits are set."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-selftest.c",
          "pattern": "APOLLO_SMMUV3_CR0_ENABLE_QUEUES",
          "description": "Linux probe writes spec-position CR0 SMMUEN/PRIQEN/EVENTQEN/CMDQEN/ATSCHK before queue use."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "FEATURE_ARCH_DPTI_UNSUPPORTED",
          "description": "Apollo TBU advertises the IDR3.DPT=0 DPTI unsupported-command functional slice."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "handle_cmdq_dpti_unsupported",
          "description": "CMD_DPTI_ALL/CMD_DPTI_PA set CMDQ_CONS.CERROR_ILL and GERROR through the guest-visible CMDQ model when IDR3.DPT=0."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "FEATURE_ARCH_CMDQ_CERROR",
          "description": "Apollo TBU advertises CMDQ_CONS.ERR/CERROR field modeling for command queue errors."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_CMDQ_CONS_ERR_SHIFT",
          "description": "CMDQ_CONS.ERR is exposed at the architected bit position used by Linux arm-smmu-v3."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_CMDQ_CERROR_ABT",
          "description": "Apollo TBU models the architected command queue abort CERROR class."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_CMDQ_CERROR_ATC_INV_SYNC",
          "description": "Apollo TBU models the architected CMD_SYNC error class for failed prior CMD_ATC_INV completion."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_atc_inv_sync_pending_count",
          "description": "Apollo TBU tracks outstanding modeled ATC invalidation completion failures until CMD_SYNC reports them."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_atc_inv_sync_force_fail_count",
          "description": "Component tests can force multiple outstanding ATC_INV completion failures."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "DptiCommandsSetGerrorWhenDptUnsupported",
          "description": "Component test covers DPTI_ALL and DPTI_PA rejection, CMDQ_CONS.CERROR_ILL reporting, software skip/clear, and GERROR acknowledgement."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdqUnconfiguredQueueSetsCerrorAbt",
          "description": "Component test covers unconfigured CMDQ abort reporting, CMDQ_CONS.CERROR_ABT, GERROR signalling, and software skip/clear."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdSyncAfterFailedAtcInvSetsCerrorAtcInvSync",
          "description": "Component test covers a modeled failed CMD_ATC_INV completion being reported by the following CMD_SYNC as CMDQ_CONS.CERROR_ATC_INV_SYNC."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdSyncCoalescesOutstandingAtcInvFailuresAndPauses",
          "description": "Component test covers multiple failed CMD_ATC_INV completions coalescing into one CMD_SYNC CERROR and pausing the queue until software skips the failing sync."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-selftest.c",
          "pattern": "SMMUv3 DPTI unsupported command selftest ok",
          "description": "Linux probe drives CMD_DPTI_ALL and validates guest-visible CMDQ_CONS.CERROR_ILL plus GERROR status because IDR3.DPT=0."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-selftest.c",
          "pattern": "APOLLO_SMMUV3_ARCH_CERROR_ILL",
          "description": "Linux probe decodes and checks architected CMDQ_CONS.CERROR_ILL."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "FEATURE_ARCH_QUEUE_OVERFLOW_FLAGS",
          "description": "Apollo TBU advertises architected output queue overflow flag coverage."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "EventAndPriQueueOverflowFlagsToggleAndAck",
          "description": "Component test covers EVENTQ/PRIQ OVFLG toggling, coalescing while unacknowledged, and OVACKFLG acknowledgement."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_GERROR_EVENTQ_ABORT",
          "description": "Apollo TBU exposes the architected SMMU_GERROR.EVENTQ_ABT_ERR bit for Event queue access aborts."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_GERROR_PRIQ_ABORT",
          "description": "Apollo TBU exposes the architected SMMU_GERROR.PRIQ_ABT_ERR bit for PRI queue access aborts."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "EventAndPriQueueWriteAbortUseArchitectedGerrorBits",
          "description": "Component test covers failed EVENTQ/PRIQ record writes setting the architected GERROR abort bits and active-bit acknowledgement."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "FEATURE_ARCH_CFGI_VMS_PIDM",
          "description": "Apollo TBU advertises the modeled CMD_CFGI_VMS_PIDM VMS/PARTID_MAP invalidation slice."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "handle_cmdq_cfgi_vms_pidm",
          "description": "CMD_CFGI_VMS_PIDM decodes the VMID operand and invalidates modeled VMID-indexed VMS/PARTID_MAP state without ATS/TLB flushing."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdqCfgiVmsPidmInvalidatesModeledVmsState",
          "description": "Component test covers non-matching and matching VMID invalidation of modeled VMS state."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_IDR3_MPAM",
          "description": "TBU advertises the architectural IDR3.MPAM discovery bit for the modeled VMS/MPAM slice."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "SMMUV3_MPAMIDR",
          "description": "TBU exposes SMMU_MPAMIDR at architected offset 0x130."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "MpamDiscoveryAdvertisesVmsPrerequisites",
          "description": "Component test verifies IDR3.MPAM, IDR3.DPT clear, MPAMIDR PARTID_MAX, and VMS feature bits."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-selftest.c",
          "pattern": "APOLLO_SMMUV3_ARCH_IDR3\t\t\t0x00007794",
          "description": "Linux guest probe expects the updated IDR3.MPAM discovery value."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "record_arch_mpam_from_cd",
          "description": "TBU resolves CD.PARTID/CD.PMG and remaps nested virtual PARTID through the fetched VMS.PARTID_MAP."
        },
        {
          "path": "sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h",
          "pattern": "mpam_partid",
          "description": "The Apollo SMMU TLM extension carries the resolved downstream MPAM PARTID and PMG attributes."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "VmsPartidMapRemapsCdPartidToMpamExtension",
          "description": "Component test covers CD virtual PARTID lookup through VMS.PARTID_MAP and downstream MPAM TLM extension propagation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "record_arch_mpam_from_ste",
          "description": "TBU assigns STE.PARTID/STE.PMG when STE.S1MPAM is clear, preserving the architected MPAM fallback path."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SteMpamAttributesPropagateWhenS1MpamDisabled",
          "description": "Component test covers STE-sourced PARTID/PMG propagation on downstream TLM transactions."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "apply_arch_mpam_range",
          "description": "TBU checks modeled PARTID/PMG values against SMMU_MPAMIDR limits and marks unsupported values UNKNOWN."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "MpamRangeOverflowMarksUnknownAttributes",
          "description": "Component test covers PARTID/PMG overflow to UNKNOWN downstream MPAM attributes."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "SMMUV3_GBPMPAM",
          "description": "TBU exposes the Non-secure SMMU_GBPMPAM register at architected offset 0x13c."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "record_arch_mpam_from_gbp",
          "description": "TBU assigns GBPMPAM PARTID/PMG to client transactions while SMMU_CR0.SMMUEN is clear."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "GlobalBypassUsesGbpmpamAttributes",
          "description": "Component test covers GBPMPAM Update programming and downstream global-bypass MPAM attributes."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "populate_arch_mpam_extension",
          "description": "TBU populates Apollo SMMU TLM MPAM attributes from SMMU_GMPAM for modeled SMMU-originated writes."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "GmpamAttributesPropagateOnEventqWrites",
          "description": "Component test covers GMPAM Update programming and EVENTQ record write MPAM attribute propagation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "apply_gmpam",
          "description": "TBU marks selected SMMU-originated read paths for GMPAM MPAM attribute propagation."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "GmpamAttributesPropagateOnCmdqFetches",
          "description": "Component test covers GMPAM attributes on command queue fetches."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "GmpamAttributesPropagateOnSteAndVmsFetches",
          "description": "Component test covers GMPAM attributes on STE and VMS fetches."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "populate_arch_mpam_extension_from_state",
          "description": "TBU reuses the resolved STE MPAM state on modeled L1CD/CD fetches."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SteMpamAttributesPropagateOnCdFetches",
          "description": "Component test covers STE-sourced MPAM attributes on context descriptor fetches."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "execute_descriptor_memory_read\\(desc_read, desc\\)",
          "description": "TBU applies the current client MPAM state to modeled translation-table descriptor fetches."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SteMpamAttributesPropagateOnS1TtFetches",
          "description": "Component test covers client-derived MPAM attributes on stage-1 translation-table fetches."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SteMpamAttributesPropagateOnS2TtFetches",
          "description": "Component test covers client-derived MPAM attributes on stage-2 translation-table fetches."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_last_ste5 = ste5",
          "description": "TBU retains the fetched STE word5 so S1MPAM paths can use STE.PMG/VMSPtr consistently for helper-walk MPAM attribution."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SteMpamAttributesPropagateOnS1MpamCdFetches",
          "description": "Component test covers STE-derived MPAM on CD fetches while STE.S1MPAM is set, followed by CD-derived client MPAM."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "NestedS1MpamAttributesPropagateOnStage2HelperWalks",
          "description": "Component test covers STE-derived MPAM on nested CD-fetch stage-2 helper walks and later CD/VMS-remapped stage-2 TT fetches."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "preserve_mpam_state",
          "description": "TBU preserves the MPAM decision made by the ATS Translated gate while routing the downstream payload."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "AtsTranslatedAtschkDisabledUsesGbpmpamAttributes",
          "description": "Component test covers GBPMPAM attributes on ATSCHK-disabled ATS Translated traffic."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "AtsTranslatedSteMpamAttributesPropagateWhenAtschkEnabled",
          "description": "Component test covers STE-derived MPAM attributes on ATSCHK-enabled ATS Translated traffic."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "AtsTranslatedCdMpamAttributesPropagateWhenS1MpamEnabled",
          "description": "Component test covers CD-derived MPAM attributes on ATSCHK-enabled ATS Translated traffic when STE.S1MPAM is enabled."
        },
        {
          "path": "sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h",
          "pattern": "mpam_partid_space",
          "description": "Apollo SMMU TLM extension carries the modeled MPAM PARTID space alongside PARTID/PMG."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_MPAM_SPACE_NONSECURE",
          "description": "Apollo TBU includes the Non-secure MPAM PARTID-space and security-state-derived PARTID-space mapping."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "MpamAttributesCarryNonSecurePartidSpace",
          "description": "Component test verifies downstream MPAM attributes and status expose the modeled Non-secure PARTID-space."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_SECURITY_ANY",
          "description": "Apollo TBU can preserve legacy all-state ATS/TLB invalidation while adding explicit per-security-state cache filtering for Secure CMDQ SSec routing."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ats_security_matches",
          "description": "ATS/TLB cache entries carry a modeled security-state tag used by Secure CMDQ TLBI/ATC invalidation routing."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureCmdqSsecTlbiAtcTargetsSelectedSecurityState",
          "description": "Component test verifies S_CMDQ TLBI_NH_VA with SSec=1 invalidates Secure ATS/TLB state while SSec=0 ATC_INV targets Non-secure state."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "NonSecureCmdqSsecTlbiAtcAreIllegal",
          "description": "Component test verifies Non-secure CMDQ TLBI/ATC with SSec=1 raises CERROR_ILL and preserves Secure ATS/TLB state."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "cmdq_tlbi_range_bytes",
          "description": "Apollo TBU decodes modeled TLBI range NUM/SCALE/TG fields into byte spans for address-based TLB invalidation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "clear_ats_cache_range_asid",
          "description": "TLBI_NH_VA invalidates modeled ATS/TLB cache entries across an ASID/VMID-qualified range."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "clear_ats_cache_range_vmid",
          "description": "TLBI_NH_VAA invalidates modeled ATS/TLB cache entries across a VMID-qualified range."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdqTlbiRangeInvalidatesModeledAtsSpan",
          "description": "Component test verifies TLBI_NH_VA and TLBI_NH_VAA range commands invalidate only entries inside the modeled span."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "cmdq_tlbi_range_encoding_reserved",
          "description": "Apollo TBU detects the architecturally reserved TLBI range encoding NUM==0, SCALE==0, TG!=0."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdqTlbiRangeReservedEncodingIsIllegal",
          "description": "Component test verifies Non-secure and Secure CMDQ TLBI range reserved encodings raise CERROR_ILL and preserve modeled ATS/TLB state."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "cmdq_tlbi_ttl",
          "description": "Apollo TBU decodes TLBI TTL hints for modeled address-based TLBI commands."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "cmdq_tlbi_leaf",
          "description": "Apollo TBU decodes TLBI Leaf hints for modeled address-based TLBI commands."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdqTlbiTtlLeafHintsFollowRangeTg",
          "description": "Component test verifies TLBI TG/TTL/Leaf accounting, TG==0 TTL suppression, TTL/TG leaf-level filtering, and Leaf=0 table-walk cache invalidation accounting."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ats_tlbi_level_matches",
          "description": "Apollo TBU filters modeled address-based TLBI invalidations by TTL level and TG granule when those hints are present."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_last_cmd_table_invalidated",
          "description": "Apollo TBU records modeled Leaf=0 table-walk cache invalidation accounting separately from leaf translation entries."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_IDR3_RIL",
          "description": "Apollo TBU advertises the architectural IDR3.RIL capability bit for modeled range invalidation."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-selftest.c",
          "pattern": "APOLLO_SMMUV3_ARCH_IDR3_RIL",
          "description": "Linux guest probe expects IDR3.RIL to be set alongside the modeled MPAM bit."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-selftest.c",
          "pattern": "apollo_hexagon_issue_ril_tlbi",
          "description": "Linux guest DMA stress issues a CMDQ TLBI_NH_VA range command using NUM/TG fields after SG DMA cache population."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-selftest.c",
          "pattern": "SMMUv3 RIL TLBI_NH_VA range selftest ok",
          "description": "Linux guest selftest reports the RIL TLBI_NH_VA range command and modeled invalidation count."
        },
        {
          "path": "scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh",
          "pattern": "SMMUv3 RIL TLBI_NH_VA range selftest ok",
          "description": "Guest smoke requires the RIL range-command marker in the QBox boot log."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_CMD_TLBI_NSNH_ALL",
          "description": "Apollo TBU recognizes the common Non-secure Non-Hyp all-scope TLBI opcode."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_CMD_TLBI_EL2_VAA",
          "description": "Apollo TBU recognizes EL2 VA-all-ASID TLBI and dispatches it through VMID/range invalidation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_CMD_TLBI_S2_IPA",
          "description": "Apollo TBU recognizes stage-2 IPA TLBI and applies VMID-qualified range invalidation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "cmdq_opcode_is_address_tlbi",
          "description": "Apollo TBU classifies address-based TLBI opcodes before range reserved-field validation."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdqAdditionalTlbiOpcodesInvalidateModeledAts",
          "description": "Component test verifies representative NSNH, S12, S2 IPA, EL2 ASID, and EL2 VAA invalidation side effects."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_CMD_TLBI_S_EL2_ASID",
          "description": "Apollo TBU recognizes the Secure EL2 ASID TLBI opcode."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_CMD_TLBI_S_S2_IPA",
          "description": "Apollo TBU recognizes the Secure stage-2 IPA TLBI opcode."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_CMD_TLBI_SNH_ALL",
          "description": "Apollo TBU recognizes the Secure non-Hyp all-scope TLBI opcode."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "cmdq_opcode_is_secure_tlbi",
          "description": "Apollo TBU classifies Secure-only TLBI opcodes and rejects them on the Non-secure CMDQ."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureOnlyTlbiOpcodesRequireSecureCmdqAndTargetSecureState",
          "description": "Component test verifies Secure-only TLBI Non-secure rejection plus Secure CMDQ ASID/range/all-scope invalidation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_mpam_partid_space_for_security_state",
          "description": "Apollo TBU derives modeled MPAM PARTID-space from the endpoint security state."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "MpamAttributesCarrySecurityPartidSpace",
          "description": "Component test verifies downstream MPAM attributes and status expose Non-secure, Secure, Realm, and Root PARTID spaces."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_gbpmpam_for_security_state",
          "description": "Apollo TBU selects SMMU_S_GBPMPAM for modeled Secure endpoint client attributes."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_gmpam_for_security_state",
          "description": "Apollo TBU selects SMMU_S_GMPAM for modeled Secure SMMU-originated attributes."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureMpamRegisterBanksDriveAttributes",
          "description": "Component test verifies Secure GBPMPAM/GMPAM register banks drive downstream MPAM attributes."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "clear_ats_cache_nsnh",
          "description": "Scoped TLBI_NSNH_ALL helper removes only ATS entries tagged with the modeled NSNH TLBI regime."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdqTlbiNsnhAllPreservesEl2RegimeEntries",
          "description": "Component test verifies modeled TLBI_NSNH_ALL invalidates only NSNH-tagged ATS entries and preserves explicitly tagged EL2-regime entries."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "SMMUV3_GATOS_CTRL",
          "description": "Apollo TBU exposes the architected non-secure SMMU_GATOS_CTRL register at PAGE_0 offset 0x100."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "SMMUV3_GATOS_PAR_LO",
          "description": "Apollo TBU exposes the architected non-secure SMMU_GATOS_PAR readback register at PAGE_0 offset 0x118."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "run_arch_gatos_register_translate",
          "description": "RUN writes on SMMU_GATOS_CTRL execute the modeled ATOS translation, write PAR, clear RUN, and suppress EVENTQ/PRI side effects for ATOS faults."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_secure_gatos_par",
          "description": "Apollo TBU stores an independent Secure SMMU_S_GATOS PAR value."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_smmu_enabled_for_security_state",
          "description": "Secure GATOS translation is gated by Secure CR0.SMMUEN instead of the Non-secure CR0 bank."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "architectural SMMU_S_GATOS register translation",
          "description": "Secure RUN writes execute through the Secure GATOS register path and log SMMU_S_GATOS completion."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureSmmuv3GatosRegistersUseSecureBank",
          "description": "Component test verifies Secure GATOS uses the Secure STRTAB bank and returns the Secure PA in PAR."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureSmmuv3GatosFaultDoesNotRecordEvent",
          "description": "Component test verifies Secure GATOS fault PAR encoding without Non-secure or Secure EVENTQ producer movement."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_ATOS_ADDR_TYPE_STAGE1_STAGE2",
          "description": "Apollo TBU decodes architected ATOS_ADDR.TYPE values for stage-1, stage-2, and stage-1+stage-2 GATOS requests."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_atos_validate_ste_config",
          "description": "Apollo TBU rejects reserved ATOS_ADDR.TYPE values with INV_REQ and unsupported stage requests with INV_STAGE before returning PAR."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "atos-stage2-translation",
          "description": "Apollo TBU can perform a bounded stage-2-only ATOS walk for nested streams when ATOS_ADDR.TYPE requests stage 2."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "Smmuv3GatosAddrTypeReservedAndInvStage",
          "description": "Component test verifies reserved ATOS_ADDR.TYPE returns INV_REQ, stage-2 on a stage-1-only stream returns INV_STAGE, and stage-1 succeeds."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "Smmuv3GatosAddrTypeNestedStageSelection",
          "description": "Component test verifies nested stream ATOS stage-1-only, stage-1+stage-2, and stage-2-only selection through SMMU_GATOS_PAR."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_ATOS_SID_SECURE_STREAM",
          "description": "Apollo TBU models SMMU_S_GATOS_SID.SSEC bit 53 for Secure versus Non-secure stream lookup selection."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureSmmuv3GatosSsecSelectsNonsecureStream",
          "description": "Component test verifies Secure ATOS SSEC-clear Non-secure stream lookup, including the Secure-CR0 gate and Non-secure STRTAB selection."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_last_atos_privileged",
          "description": "Apollo TBU records ATOS_ADDR.PnU from architected GATOS requests."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_last_atos_instruction",
          "description": "Apollo TBU records ATOS_ADDR.InD from architected GATOS requests."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "STE output attributes ignored for ATOS",
          "description": "Architected ATOS_PAR success suppresses modeled STE output-attribute overrides while preserving the compatibility GATOS_PAR path."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "Smmuv3GatosAddrAccessFieldsIgnoreSteOverrides",
          "description": "Component test validates ATOS_ADDR.PnU/InD/RnW decode and architected ATOS_PAR STE-override suppression."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedIdr0AdvertisesAtsPri",
          "description": "Component test verifies guest-visible SMMU_IDR0 advertises ATS and PRI for the modeled command support."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "SMMUV3_IDR6 = 0x190",
          "description": "Apollo TBU assigns the architected SMMU_IDR6 discovery slot for ECMDQ unsupported RES0 handling."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "SMMUV3_CMDQ_CONTROL_PAGE_BASE_LO = 0x4000",
          "description": "Apollo TBU assigns the first ECMDQ control-page discovery aperture for unsupported RES0/WI handling."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_ECMDQ_UNSUPPORTED_RES0",
          "description": "Apollo TBU records the no-overclaim ECMDQ unsupported RES0 policy."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "EcmdqUnsupportedRegistersAreRes0",
          "description": "Component test verifies IDR6/S_IDR6 and ECMDQ control-page probes remain RES0/WI when ECMDQ is not advertised."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "SMMUV3_IIDR = 0x018",
          "description": "Apollo TBU assigns SMMU_IIDR to the architected Page 0 offset."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "SMMUV3_AIDR = 0x01c",
          "description": "Apollo TBU assigns SMMU_AIDR to the architected Page 0 offset."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SMMUV3_IIDR",
          "description": "Component test verifies IIDR and AIDR are distinct architected register slots."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_IDR5_OAS_48",
          "description": "Apollo TBU advertises a 48-bit modeled output address size in SMMU_IDR5."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_IDR5_GRAN64K",
          "description": "Apollo TBU advertises modeled 4K/16K/64K granules in SMMU_IDR5."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ARCH_IDR5_GRAN64K",
          "description": "Component test verifies SMMU_IDR5 granule and OAS discovery bits."
        }
      ],
      "runtime_evidence": [
        {
          "path": "build/verification/apollo-smmu-tbu-reg-queue-ctest-20260510.log",
          "pattern": "100% tests passed",
          "description": "CTest confirms the Apollo SMMUv3 reg/queue unit test passes."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-register-bank-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/030 guest-visible `SMMU_S_.*` Secure register banking",
          "description": "Verification report records the Secure register-bank build, component-test, and static-check evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-cmdq-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020 Secure command queue memory-backed lifecycle",
          "description": "Verification report records the Secure CMDQ memory-backed lifecycle build and component-test evidence."
        },
        {
          "path": "build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-020-final.log",
          "pattern": "SMMUv3 page-table walker/ATS/PRI/fault queue ready",
          "description": "Existing runtime slice still proves guest-visible SMMUv3 readiness marker."
        },
        {
          "path": "build/verification/apollo-smmu-tbu-reg-queue-ctest-guest-selftest-20260510.log",
          "pattern": "100% tests passed",
          "description": "CTest still passes after exposing the SMMUv3 aperture to the guest platform window."
        },
        {
          "path": "build/verification/qbox-linux-smmu-guest-queue-selftest-20260510.log",
          "pattern": "Linux Image:",
          "description": "Linux Image rebuild includes the guest-visible architected queue selftest."
        },
        {
          "path": "build/verification/qbox-platform-smmu-guest-queue-selftest-20260510.log",
          "pattern": "QBox Buildroot platform runtime built",
          "description": "QBox platform rebuild includes the enlarged Apollo TBU register window."
        },
        {
          "path": "build/verification/stage-artifacts-smmu-guest-queue-selftest-20260510.log",
          "pattern": "Staged Linux \\+ Buildroot artifacts",
          "description": "Updated Linux and Buildroot artifacts were staged into the QBox platform artifact directory."
        },
        {
          "path": "build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-guest-queue-selftest-final.log",
          "pattern": "SMMUv3 architected queue register selftest",
          "description": "Guest boot log proves Linux can access and validate the architected CMDQ/EVENTQ/PRIQ aperture."
        },
        {
          "path": "build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-guest-queue-selftest-final.driver.log",
          "pattern": "PASS: QBox guest IREE Hexagon tiny-CNN output matched",
          "description": "End-to-end guest smoke passes after the guest-visible SMMUv3 queue selftest."
        },
        {
          "path": "build/verification/apollo-smmuv3-cmd-invalidation-ctest-20260510.log",
          "pattern": "100% tests passed",
          "description": "CTest confirms the command-driven invalidation functional slice passes."
        },
        {
          "path": "build/verification/apollo-smmuv3-tagged-invalidation-ctest-20260510.log",
          "pattern": "100% tests passed",
          "description": "CTest confirms ASID/VMID/SSID-tagged invalidation coverage passes."
        },
        {
          "path": "doc/verification/qbox-smmuv3-linux-cmd-invalidation-verification-2026-05-10.md",
          "pattern": "Guest smoke",
          "description": "Verification report records Linux guest-driven CMDQ invalidation and end-to-end smoke evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-dpti-unsupported-verification-2026-05-10.md",
          "pattern": "SMMU-COMP-020 DPTI unsupported-command functional slice",
          "description": "Verification report records DPTI unsupported-command evidence and remaining DPT blockers."
        },
        {
          "path": "doc/verification/qbox-smmuv3-dpt-register-res0-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050/060 DPT unsupported-register RES0 slice",
          "description": "Verification report records DPT_BASE, DPT_BASE_CFG, and DPT_CFG_FAR RES0/WI behavior while IDR3.DPT is clear."
        },
        {
          "path": "doc/verification/qbox-smmuv3-cmdq-cerror-verification-2026-05-10.md",
          "pattern": "SMMU-COMP-020 CMDQ CERROR functional slice",
          "description": "Verification report records CMDQ_CONS.CERROR_ILL evidence for IDR3.DPT=0 DPTI rejection."
        },
        {
          "path": "doc/verification/qbox-smmuv3-cmdq-cerror-abt-verification-2026-05-10.md",
          "pattern": "SMMU-COMP-020 CMDQ CERROR_ABT functional slice",
          "description": "Verification report records CMDQ_CONS.CERROR_ABT evidence for enabled but unconfigured command queues."
        },
        {
          "path": "doc/verification/qbox-smmuv3-cmdq-cerror-atc-inv-sync-verification-2026-05-10.md",
          "pattern": "SMMU-COMP-020 CMDQ CERROR_ATC_INV_SYNC functional slice",
          "description": "Verification report records CMDQ_CONS.CERROR_ATC_INV_SYNC evidence for failed prior CMD_ATC_INV completion."
        },
        {
          "path": "doc/verification/qbox-smmuv3-cmdq-cerror-atc-inv-sync-multi-verification-2026-05-10.md",
          "pattern": "SMMU-COMP-020 CMDQ CERROR_ATC_INV_SYNC multi-outstanding pause/recovery slice",
          "description": "Verification report records multi-outstanding CERROR_ATC_INV_SYNC coalescing, pause, skip, and recovery evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-queue-ovflg-verification-2026-05-10.md",
          "pattern": "SMMU-COMP-020/050/060 EVENTQ/PRIQ OVFLG/OVACKFLG functional slice",
          "description": "Follow-up report records component build, CTest, static checker, and lane evidence for output queue overflow flags."
        },
        {
          "path": "doc/verification/qbox-smmuv3-queue-abort-gerror-verification-2026-05-10.md",
          "pattern": "SMMU-COMP-020/050/060/070 EVENTQ/PRIQ queue abort GERROR functional slice",
          "description": "Follow-up report records component build, CTest, static checker, and lane evidence for architected output queue abort GERROR bits."
        },
        {
          "path": "doc/verification/qbox-smmuv3-cfgi-vms-pidm-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020 CMD_CFGI_VMS_PIDM functional slice",
          "description": "Verification report records build, CTest, static checker, and lane evidence for modeled CFGI_VMS_PIDM invalidation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-discovery-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 MPAM/VMS discovery functional slice",
          "description": "Verification report records build, focused gTest/CTest, static checker, and lane evidence for IDR3.MPAM/MPAMIDR discovery coherence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-partid-remap-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 MPAM PARTID_MAP remap functional slice",
          "description": "Verification report records build, CTest, focused gTest, static checker, and lane evidence for CD.PARTID remap into downstream MPAM attributes."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ste-mpam-attrs-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 STE-sourced MPAM functional slice",
          "description": "Verification report records build, CTest, focused gTest, static checker, and lane evidence for STE.PARTID/PMG fallback assignment."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-range-unknown-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 MPAM range-to-UNKNOWN functional slice",
          "description": "Verification report records build, CTest, focused gTest, static checker, and lane evidence for MPAMIDR PARTID/PMG range handling."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-gbpmpam-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 GBPMPAM global-bypass functional slice",
          "description": "Verification report records build, CTest, focused gTest, static checker, and lane evidence for GBPMPAM global-bypass assignment."
        },
        {
          "path": "doc/verification/qbox-smmuv3-gbpa-global-bypass-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/030/080 GBPA global-bypass attribute/abort slice",
          "description": "Verification report records SMMU_GBPA output attributes for disabled-SMMU bypass and GBPA.ABORT no-event abort behavior."
        },
        {
          "path": "doc/verification/qbox-smmuv3-agbpa-res0-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/030/080 AGBPA unsupported-RES0 slice",
          "description": "Verification report records unsupported SMMU_AGBPA/SMMU_S_AGBPA RES0/WI behavior."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-gmpam-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 GMPAM originated-write functional slice",
          "description": "Verification report records build, CTest, focused gTest, static checker, and lane evidence for GMPAM queue/MSI write, CMDQ/STE/VMS fetch attributes, STE-sourced CD fetch attributes, and client-derived TT fetch attributes."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-gmpam-fetch-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 GMPAM originated-fetch functional slice",
          "description": "Verification report records build, CTest, focused gTest, static checker, and lane evidence for GMPAM command-queue, STE, L1STD, and VMS fetch attributes."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-ste-cd-fetch-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 STE-sourced CD fetch functional slice",
          "description": "Verification report records build, CTest, focused gTest, static checker, and lane evidence for STE-sourced L1CD/CD fetch attributes."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-tt-fetch-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 client-derived TT fetch functional slice",
          "description": "Verification report records build, CTest, focused gTest, static checker, and lane evidence for client-derived stage-1/stage-2 translation-table descriptor fetch attributes."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-s1mpam-helper-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 S1MPAM nested helper MPAM functional slice",
          "description": "Verification report records build, CTest, focused gTest, static checker, and lane evidence for S1MPAM CD/helper-walk STE attributes before CD/VMS override."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-ats-translated-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050/060 ATS Translated MPAM functional slice",
          "description": "Verification report records build, CTest, focused gTest, static checker, and lane evidence for ATS Translated GBPMPAM, STE-sourced, and CD-sourced MPAM attributes."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-partid-space-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 MPAM PARTID-space functional slice",
          "description": "Verification report records build, focused gTest/CTest, static checker, and lane evidence for explicit Non-secure PARTID-space tagging."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-cmdq-ssec-cfgi-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020 Secure CMDQ SSec CFGI functional slice",
          "description": "Verification report records build, component test, static checker, lane, and guest smoke evidence for modeled CFGI SSec routing and Non-secure SSec CERROR_ILL."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-cmdq-ssec-tlbi-atc-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020 Secure CMDQ SSec TLBI/ATC functional slice",
          "description": "Verification report records build, component test, static checker, lane, and guest smoke evidence for modeled TLBI/ATC SSec routing and Non-secure SSec CERROR_ILL."
        },
        {
          "path": "doc/verification/qbox-smmuv3-tlbi-range-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/040 TLBI range invalidation functional slice",
          "description": "Verification report records build, component test, static checker, lane, and guest smoke evidence for modeled TLBI_NH_VA/TLBI_NH_VAA range invalidation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-tlbi-range-reserved-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/040 TLBI range reserved-encoding functional slice",
          "description": "Verification report records build, CTest, static checker, lane, and guest smoke evidence for reserved NUM/SCALE/TG CERROR_ILL rejection."
        },
        {
          "path": "doc/verification/qbox-smmuv3-tlbi-level-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/040 TLBI TTL/Leaf level-aware invalidation slice",
          "description": "Verification report records build, CTest, focused gTest, static checker, lane, and guest smoke evidence for TLBI TG/TTL/Leaf hint accounting plus modeled level-aware invalidation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ril-range-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/040/080 IDR3.RIL Linux range-command stress slice",
          "description": "Verification report records build, CTest, focused gTest, Linux build/stage, static checker, lane, and guest smoke evidence for IDR3.RIL and Linux RIL TLBI_NH_VA range-command stress."
        },
        {
          "path": "doc/verification/qbox-smmuv3-additional-tlbi-opcodes-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/040 additional TLBI opcode slice",
          "description": "Verification report records build, CTest, focused gTest, static checker, lane, and final closure evidence for modeled additional TLBI opcode coverage."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-tlbi-opcodes-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/040 Secure-only TLBI opcode slice",
          "description": "Verification report records build, CTest, focused gTest, static checker, lane, and final closure evidence for modeled Secure-only TLBI opcode coverage."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-security-partid-space-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 MPAM security PARTID-space slice",
          "description": "Verification report records build, focused gTest/CTest, static checker, lane, and final closure evidence for security-state-derived MPAM PARTID-space tagging."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-mpam-register-bank-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 Secure GBPMPAM/GMPAM register-bank attribute slice",
          "description": "Verification report records build, focused gTest/CTest, static checker, lane, and final closure evidence for Secure MPAM register-bank attribute selection."
        },
        {
          "path": "doc/verification/qbox-smmuv3-architected-gatos-registers-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/030/080 architected non-secure SMMU_GATOS register slice",
          "description": "Verification report records build, focused gTest/CTest, static checker, lane, and closure evidence for the non-secure SMMU_GATOS RUN/PAR/no-event path."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-gatos-registers-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/030/080 Secure SMMU_S_GATOS register slice",
          "description": "Verification report records build, focused gTest/CTest, static checker, lane, and closure evidence for the Secure SMMU_S_GATOS RUN/PAR/no-event path."
        },
        {
          "path": "build/verification/smmu-atos-addr-type-build-20260511.log",
          "pattern": "Built target apollo-smmu-tbu-tests",
          "description": "Apollo SMMU TBU tests rebuild after ATOS_ADDR.TYPE matrix implementation."
        },
        {
          "path": "build/verification/smmu-atos-addr-type-gtest-20260511.log",
          "pattern": "Smmuv3GatosAddrTypeNestedStageSelection",
          "description": "Focused gTest exercises reserved/INV_STAGE and nested ATOS_ADDR.TYPE stage-selection cases."
        },
        {
          "path": "build/verification/smmu-atos-addr-type-ctest-20260511.log",
          "pattern": "100% tests passed",
          "description": "CTest regression passes for the Apollo SMMU TBU component suite after ATOS_ADDR.TYPE changes."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-gatos-ssec-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/080 S_GATOS.SSEC stream-selection slice",
          "description": "Verification report records build, focused gTest, CTest, static checker, and lane evidence for S_GATOS.SSEC stream selection."
        },
        {
          "path": "build/verification/smmu-secure-gatos-ssec-gtest-20260511.log",
          "pattern": "[  PASSED  ]",
          "description": "Focused gTest covers Secure GATOS SSEC Secure and Non-secure stream-selection paths."
        },
        {
          "path": "doc/verification/qbox-smmuv3-atos-access-fields-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/080 ATOS_ADDR access-field attribute slice",
          "description": "Verification report records build, focused gTest, CTest, static checker, lane, and closure evidence for the bounded ATOS_ADDR access-field attribute slice."
        },
        {
          "path": "build/verification/smmu-atos-access-fields-gtest-20260511.log",
          "pattern": "[  PASSED  ]",
          "description": "Focused gTest covers ATOS_ADDR.PnU/InD/RnW decode and STE-output-override suppression while preserving the compatibility GATOS_PAR path."
        },
        {
          "path": "doc/verification/qbox-smmuv3-idr0-ats-pri-advertisement-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/060 IDR0 ATS/PRI advertisement slice",
          "description": "Verification report records IDR0 ATS/PRI advertisement, Linux probe constant, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ecmdq-register-res0-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/060 ECMDQ unsupported-register RES0 slice",
          "description": "Verification report records unsupported ECMDQ IDR6 and control-page RES0/WI behavior."
        },
        {
          "path": "build/verification/smmu-ecmdq-register-res0-build-20260511.log",
          "pattern": "Built target apollo-smmu-tbu-tests",
          "description": "Focused build includes the ECMDQ unsupported-register component test."
        },
        {
          "path": "build/verification/smmu-ecmdq-register-res0-gtest-20260511.log",
          "pattern": "EcmdqUnsupportedRegistersAreRes0",
          "description": "Focused gTest covers ECMDQ unsupported discovery/register probes."
        },
        {
          "path": "build/verification/smmu-ecmdq-register-res0-ctest-20260511.log",
          "pattern": "100% tests passed",
          "description": "CTest confirms the Apollo SMMU TBU component suite passes after the ECMDQ slice."
        },
        {
          "path": "doc/verification/qbox-smmuv3-iidr-aidr-register-slots-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020 IIDR/AIDR register-slot correction slice",
          "description": "Verification report records the IIDR/AIDR offset correction and no-overclaim boundary."
        },
        {
          "path": "build/verification/smmu-iidr-aidr-register-slots-build-20260511.log",
          "pattern": "Built target apollo-smmu-tbu-tests",
          "description": "Focused build includes the IIDR/AIDR register-slot assertion."
        },
        {
          "path": "build/verification/smmu-iidr-aidr-register-slots-gtest-20260511.log",
          "pattern": "ArchitectedRegisterMmioSurface",
          "description": "Focused gTest exercises the architected register MMIO surface including IIDR/AIDR slots."
        },
        {
          "path": "build/verification/smmu-iidr-aidr-register-slots-ctest-20260511.log",
          "pattern": "100% tests passed",
          "description": "CTest confirms the Apollo SMMU TBU component suite passes after the IIDR/AIDR correction."
        },
        {
          "path": "doc/verification/qbox-smmuv3-idr5-granule-oas-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/040/050 IDR5 granule/OAS discovery slice",
          "description": "Verification report records IDR5 granule/OAS discovery alignment."
        },
        {
          "path": "build/verification/smmu-idr5-granule-oas-build-20260511.log",
          "pattern": "Built target apollo-smmu-tbu-tests",
          "description": "Focused build includes the IDR5 discovery assertions."
        },
        {
          "path": "build/verification/smmu-idr5-granule-oas-gtest-20260511.log",
          "pattern": "3 tests from 3 test suites ran",
          "description": "Focused gTest covers IDR5 discovery, granule walker matrix, and 48-bit OAS abort boundary."
        },
        {
          "path": "build/verification/smmu-idr5-granule-oas-ctest-20260511.log",
          "pattern": "100% tests passed",
          "description": "CTest confirms the Apollo SMMU TBU component suite passes after IDR5 discovery alignment."
        },
        {
          "path": "doc/verification/qbox-smmuv3-idr1-discovery-limits-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/030/050/060 IDR1 discovery/limits slice",
          "description": "Verification report records IDR0.ST_LEVEL and IDR1 SID/SSID, queue-depth, and attribute-override discovery alignment."
        },
        {
          "path": "build/verification/smmu-idr1-discovery-limits-build-20260511.log",
          "pattern": "Built target apollo-smmu-tbu-tests",
          "description": "Focused build includes the IDR1 discovery-limit assertions."
        },
        {
          "path": "build/verification/smmu-idr1-discovery-limits-gtest-20260511.log",
          "pattern": "2 tests from 2 test suites ran",
          "description": "Focused gTest covers Non-secure and Secure IDR1 discovery fields and RES0 masking."
        },
        {
          "path": "build/verification/smmu-idr1-discovery-limits-ctest-20260511.log",
          "pattern": "100% tests passed",
          "description": "CTest confirms the Apollo SMMU TBU component suite passes after IDR1 discovery alignment."
        },
        {
          "path": "doc/verification/qbox-smmuv3-idr0-stage-ttf-cd2l-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/030/040 IDR0 S1P/TTF/CD2L discovery slice",
          "description": "Verification report records stage-1/stage-2, AArch64 TTF, ST_LEVEL, and CD2L discovery alignment."
        },
        {
          "path": "build/verification/smmu-idr0-stage-ttf-cd2l-build-20260511.log",
          "pattern": "Built target apollo-smmu-tbu-tests",
          "description": "Focused build includes the IDR0 stage/TTF/CD2L assertions."
        },
        {
          "path": "build/verification/smmu-idr0-stage-ttf-cd2l-gtest-20260511.log",
          "pattern": "ArchitectedRegisterMmioSurface",
          "description": "Focused gTest covers the updated IDR0 discovery surface."
        },
        {
          "path": "build/verification/smmu-idr0-stage-ttf-cd2l-ctest-20260511.log",
          "pattern": "100% tests passed",
          "description": "CTest confirms the Apollo SMMU TBU component suite passes after IDR0 discovery alignment."
        },
        {
          "path": "doc/verification/qbox-smmuv3-idr0-asid16-vmid16-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/040/060 IDR0 ASID16/VMID16 discovery slice",
          "description": "Verification report records IDR0 ASID16/VMID16 discovery and high-bit tag invalidation evidence."
        },
        {
          "path": "build/verification/smmu-idr0-asid16-vmid16-build-20260511.log",
          "pattern": "Built target apollo-smmu-tbu-tests",
          "description": "Focused build includes ASID16/VMID16 discovery and tagged-invalidation checks."
        },
        {
          "path": "build/verification/smmu-idr0-asid16-vmid16-gtest-20260511.log",
          "pattern": "CmdqTaggedInvalidationHonorsAsidVmidAndSsid",
          "description": "Focused gTest covers high-bit ASID/VMID tagged invalidation retention."
        },
        {
          "path": "build/verification/smmu-idr0-asid16-vmid16-ctest-20260511.log",
          "pattern": "100% tests passed",
          "description": "CTest confirms the Apollo SMMU TBU component suite passes after ASID16/VMID16 discovery alignment."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-idr3-sams-res0-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/060 Secure IDR3 SAMS/RES0 slice",
          "description": "Verification report records Secure SMMU_S_IDR3 SAMS/RES0 behavior instead of Non-secure IDR3 mirroring."
        },
        {
          "path": "build/verification/smmu-secure-idr3-sams-res0-build-20260511.log",
          "pattern": "Built target apollo-smmu-tbu-tests",
          "description": "Focused build includes the Secure IDR3 component assertion."
        },
        {
          "path": "build/verification/smmu-secure-idr3-sams-res0-gtest-20260511.log",
          "pattern": "SecureRegisterBankConfiguresStrtabCmdqAndEventq",
          "description": "Focused gTest covers SMMU_S_IDR3 RES0/SAMS masking."
        },
        {
          "path": "build/verification/smmu-secure-idr3-sams-res0-ctest-20260511.log",
          "pattern": "100% tests passed",
          "description": "CTest confirms the Apollo SMMU TBU component suite passes after Secure IDR3 correction."
        },
        {
          "path": "doc/verification/qbox-smmuv3-idr4-implementation-defined-zero-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020 IDR4 implementation-defined zero slice",
          "description": "Verification report records the explicit zero-valued Non-secure and Secure IDR4 discovery policy."
        },
        {
          "path": "build/verification/smmu-idr4-implementation-defined-zero-build-20260511.log",
          "pattern": "Built target apollo-smmu-tbu-tests",
          "description": "Focused build includes the IDR4 register-surface assertions."
        },
        {
          "path": "build/verification/smmu-idr4-implementation-defined-zero-gtest-20260511.log",
          "pattern": "SecureRegisterBankConfiguresStrtabCmdqAndEventq",
          "description": "Focused gTest covers Non-secure IDR4 and Secure S_IDR4 zero-valued reads."
        },
        {
          "path": "build/verification/smmu-idr4-implementation-defined-zero-ctest-20260511.log",
          "pattern": "100% tests passed",
          "description": "CTest confirms the Apollo SMMU TBU component suite passes after IDR4 exposure."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-idr0-msi-stall-res0-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/070 Secure IDR0 MSI/stall/RES0 slice",
          "description": "Verification report records Secure S_IDR0 MSI, stall-model, ECMDQ, and RES0 discovery behavior."
        },
        {
          "path": "build/verification/smmu-secure-idr0-msi-stall-res0-build-20260511.log",
          "pattern": "Built target apollo-smmu-tbu-tests",
          "description": "Focused build includes the Secure IDR0 component assertions."
        },
        {
          "path": "build/verification/smmu-secure-idr0-msi-stall-res0-gtest-20260511.log",
          "pattern": "SecureRegisterBankConfiguresStrtabCmdqAndEventq",
          "description": "Focused gTest covers Secure S_IDR0 MSI/stall/ECMDQ/RES0 discovery."
        },
        {
          "path": "build/verification/smmu-secure-idr0-msi-stall-res0-ctest-20260511.log",
          "pattern": "100% tests passed",
          "description": "CTest confirms the Apollo SMMU TBU component suite passes after Secure IDR0 correction."
        },
        {
          "path": "doc/verification/qbox-smmuv3-aidr-v33-idr3-mandatory-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/040/060 AIDR v3.3 and IDR3 mandatory discovery slice",
          "description": "Verification report records AIDR v3.3 and IDR3 mandatory v3.2/v3.3 discovery alignment."
        },
        {
          "path": "build/verification/smmu-aidr-v33-idr3-mandatory-build-20260511.log",
          "pattern": "Built target apollo-smmu-tbu-tests",
          "description": "Focused build includes the AIDR/IDR3 discovery assertions."
        },
        {
          "path": "build/verification/smmu-aidr-v33-idr3-mandatory-gtest-20260511.log",
          "pattern": "ArchitectedRegisterMmioSurface",
          "description": "Focused gTest covers AIDR v3.3 plus IDR3 HAD/XNX/FWB/STT/BBML2/E0PD/PTWNNC discovery bits."
        },
        {
          "path": "build/verification/smmu-aidr-v33-idr3-mandatory-ctest-20260511.log",
          "pattern": "100% tests passed",
          "description": "CTest confirms the Apollo SMMU TBU component suite passes after AIDR/IDR3 discovery alignment."
        }
      ]
    },
    {
      "id": "SMMU-COMP-030",
      "title": "Stream table and context descriptor decode",
      "status": "functional-slice",
      "owner": "Apollo TBU + Apollo Linux probe",
      "claim_scope": "Bounded linear/2-level STRTAB StreamID selection, spec-bitfield S1 STE/CD pointer decode, S1CDMax-bounded linear/64K-L2 CD-table SSID indexing, nested CD/L1CD and stage-1 TT descriptor-fetch IPA stage-2 translation, modeled S1DSS/substream descriptor faults to F_STREAM_DISABLED/C_BAD_SUBSTREAMID, STE.Config==0 no-event termination, no-substream S1DSS terminate/bypass policy including nested S2 translation after bypass, modeled STE output-attribute propagation on context-bypass, STE.Config all-bypass, stage-1/stage-2/nested translation, ATS Translated payload paths, the bounded GATOS_PAR return path, the architected non-secure SMMU_GATOS register group RUN/PAR/no-event ATOS path, the Secure SMMU_S_GATOS RUN/PAR/no-event ATOS path, a bounded ATOS_ADDR.TYPE matrix for reserved INV_REQ, missing-stage INV_STAGE, nested stage-1-only, stage-2-only, and stage-1+stage-2 register requests, plus ATOS_ADDR.PnU/InD/RnW access-field decode and architected ATOS_PAR STE-output-override suppression plus a non-advertised internal VATOS/S_VATOS stage-1-only model with GATOS/VATOS PAR isolation and SMMU_VATOS_SEL-to-STE.S2VMID rejection, endpoint PASID/SSID TLM propagation into ATS/event tagging, modeled STE/CD reserved-bit plus illegal-encoding faults, configured Secure stream-table banking, Secure stage-2-only NSCFG/S_S2TTB selection, Secure nested stage-1-derived NSIPA-to-S2TTB/S_S2TTB selection, Secure nested stage-1 TT-fetch S2TTB/S_S2TTB selection, STE.S2R/S2S stage-2 fault record/stall policy plus terminate-only STALL_MODEL validation, and Linux guest-driven CMDQ invalidation probes are covered by functional slices; full PCIe PASID/CD invalidation parity, guest-visible complete VATOS/S_VATOS, remaining ATOS_ADDR fields beyond TYPE/RnW/PnU/InD and full attribute parity, and partial ATOS register parity beyond the modeled non-secure/Secure GATOS slices, remaining Secure command lifecycle parity beyond the modeled memory-backed S_CMDQ fetch/sync/invalidation/error-recovery/MSI slice, complete Root/Realm RME/GPT/GPC policy, full Arm reserved-matrix parity, and true upstream arm-smmu-v3 CD invalidation lifecycle remain open. The slice also accepts modeled Secure, Realm, and Root endpoint transactions on the existing translation path and rejects invalid security-state transactions before translation while Root and complete Realm RME/GPT/GPC paths remain out of scope for the current QBox security-state model.",
      "source_evidence": [
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "REG_ARCH_STREAM_ID",
          "description": "TBU exposes an architected-probe StreamID selector for stream table walks."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_STRTAB_FMT_2LVL",
          "description": "TBU decodes STRTAB_BASE_CFG linear/two-level format fields."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_FAULT_BAD_STREAM_ID",
          "description": "Out-of-range StreamID probes now produce an explicit architected bad-StreamID fault reason in the functional slice."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedLinearStreamTableUsesSelectedStreamId",
          "description": "Component test verifies selected-SID bounded linear STRTAB lookup and invalid SID replay."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedTwoLevelStreamTableSelectsL2Ste",
          "description": "Component test verifies two-level STRTAB L1/L2 STE selection."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-selftest.c",
          "pattern": "SMMUv3 stream/context descriptor probe ok",
          "description": "Existing Linux probe still stages STE/CD descriptors and checks the compatibility result."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "FEATURE_ARCH_CD_TABLE_INDEX",
          "description": "TBU advertises the functional CD-table SSID indexing slice."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_STE_S1CDMAX_SHIFT",
          "description": "TBU decodes STE.S1CDMax to bound selected SSID context descriptor lookup."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_STE_S1FMT_64K_L2",
          "description": "TBU supports the modeled 64K two-level context descriptor table format."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "REG_ARCH_SSID",
          "description": "TBU exposes a compatibility-preserving test selector for an architected SubstreamID/PASID value."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedContextDescriptorTableIndexesSelectedSsid",
          "description": "Component test verifies SSID-selected linear CD lookup, S1CDMax out-of-range faulting, no-substream S1DSS terminate/bypass policy, and 64K-L2 CD table lookup."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_STE_S1DSS_BYPASS",
          "description": "TBU decodes the S1DSS no-substream bypass policy value."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_last_cd_bypass",
          "description": "TBU records S1DSS bypass state in the architected CD detail register model."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "no-SSID context descriptor bypass",
          "description": "TBU logs no-substream S1DSS bypass decisions during stream/context walks."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "architectural nested CD fetch stage-2 walk",
          "description": "Nested STE CD fetch IPAs are translated through the stage-2 descriptor walker before the CD is read."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "architectural nested L1CD fetch stage-2 walk",
          "description": "Nested 64K-L2 L1CD fetch IPAs are translated through the stage-2 descriptor walker before the L1CD is read."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedNestedL1CdFetchStage2Walks",
          "description": "Component vector verifies nested 64K-L2 L1CD and L2CD fetches through stage 2 on the success path."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "stage2_translate_descriptor_fetch",
          "description": "Nested stage-1 translation-table descriptor fetch IPAs are translated through stage 2 before descriptor reads."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ARCH_STE_S1DSS_TERMINATE",
          "description": "Component vector verifies no-substream S1DSS terminate produces a CD fault."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ARCH_STE_S1DSS_BYPASS",
          "description": "Component vector verifies no-substream S1DSS bypass identity translation and detail bit."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "architectural nested S1DSS bypass stage-2 walk",
          "description": "TBU routes nested STE S1DSS bypass cases into a stage-2 descriptor walk instead of identity-final PA."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "bypass_s2ttb",
          "description": "Component vector verifies nested S1DSS bypass still applies the stage-2 table walk."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "FEATURE_ARCH_RESERVED_ENCODING_CHECKS",
          "description": "TBU advertises the modeled STE/CD reserved and illegal encoding validation slice."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_reject_reserved_ste",
          "description": "TBU rejects unsupported/reserved STE words before using stream descriptor state."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "reserved CD encoding",
          "description": "TBU rejects modeled reserved CD word bits before using context descriptor state."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "illegal S1DSS encoding",
          "description": "TBU rejects the modeled illegal S1DSS encoding with an S1 CD fault."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedSteCdReservedEncodingFaults",
          "description": "Component vector verifies illegal STE.Config, reserved STE/CD words, illegal S1DSS, and reserved 64K-L2 CD L1 entries fault."
        },
        {
          "path": "sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h",
          "pattern": "substream_id_valid",
          "description": "Common TLM extension carries endpoint SubstreamID/PASID metadata with translated requests."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "EndpointSubstreamIdTagsAtsAndFaultEvents",
          "description": "Component test verifies endpoint-provided SSID tags ATS entries and EVENTQ SSV/SubstreamID fields."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-selftest.c",
          "pattern": "APOLLO_SMMUV3_ARCH_CMD_TLBI_NH_ALL",
          "description": "Linux probe stages a guest-visible TLBI_NH_ALL command through the SMMUv3 CMDQ model."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_EVENT_F_STREAM_DISABLED",
          "description": "TBU maps modeled S1DSS stream-disabled descriptor faults to the architected F_STREAM_DISABLED event number."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_EVENT_C_BAD_SUBSTREAMID",
          "description": "TBU maps modeled bad SubstreamID descriptor faults to the architected C_BAD_SUBSTREAMID event number."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedStreamDisabledAndBadSubstreamEvents",
          "description": "Component vector verifies S1DSS stream-disabled and out-of-range SubstreamID EVENTQ records."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "FEATURE_ARCH_CONFIG_DISABLED_NO_EVENT",
          "description": "TBU advertises modeled STE.Config==0 disabled-stream no-event termination."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedConfigDisabledSuppressesEvents",
          "description": "Component vector verifies valid STE.Config==0 terminates without pushing an EVENTQ record."
        },
        {
          "path": "sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h",
          "pattern": "security_state",
          "description": "Apollo SMMU TLM extension carries endpoint security-state metadata."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_security_state_supported",
          "description": "Apollo TBU supports Non-secure plus modeled Secure, Realm, and Root endpoint transactions while complete RME/GPT/GPC behavior remains gated."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureRealmRootEndpointAcceptedInvalidRejectedBeforeTranslation",
          "description": "Component test verifies Secure/Realm/Root-tagged traffic translates and invalid security-state traffic is rejected before translation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "record_arch_eventq_security_route",
          "description": "Apollo TBU records the active security state for modeled EVENTQ route accounting."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "m_arch_eventq_secure_records",
          "description": "Component test verifies Secure fault events and invalid-state events routed by masked Root event-state accounting are recorded in their modeled EVENTQ security-state routes."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_CD_NSCFG0",
          "description": "TBU decodes modeled CD.NSCFG0 as the starting NS attribute for Secure stage-1 table walks."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_DESC_NS",
          "description": "TBU decodes modeled stage-1 leaf descriptor NS output for Secure nested stage-2 IPA-space selection."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureNestedStage1OutputNsSelectsS2Ttb",
          "description": "Component test verifies Secure nested stage-1 CD.NSCFG0 and leaf NS select S2TTB or S_S2TTB for final stage-2 translation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_last_s1_tt_fetch_s2ttb",
          "description": "TBU records whether nested Secure stage-1 TT descriptor fetches used S2TTB or S_S2TTB."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_STE_S2R",
          "description": "TBU models the STE.S2R stage-2 fault-record control bit."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "apply_arch_stage2_fault_policy",
          "description": "Stage-2 stream/context walk failures apply STE.S2R/S2S record/stall policy before event emission."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "Stage2SteS2rS2sControlsRecordAndStall",
          "description": "Component test covers suppressed, non-stall, and stalled stage-2 fault outcomes."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_stall_model_terminates_stage2_stalls",
          "description": "TBU validates that terminate-only STALL_MODEL rejects stage-2 STE.S2S instead of allowing an impossible stall path."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SteS2sRejectedWhenStallModelTerminateOnly",
          "description": "Component test verifies STALL_MODEL==terminate-only plus stage-2 S2S emits C_BAD_STE, while non-stage-2 S2S remains accepted."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "record_arch_ste_output_attrs",
          "description": "TBU records modeled STE MTCFG/MemAttr/SHCFG/ALLOCCFG/INSTCFG/PRIVCFG/NSCFG output attributes when the context-descriptor path returns bypass."
        },
        {
          "path": "sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h",
          "pattern": "output_attrs_valid",
          "description": "Common SMMU TLM extension carries modeled STE bypass output-attribute metadata downstream."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SteBypassOutputAttributesPropagateOnContextBypass",
          "description": "Component test verifies context-bypass propagation of MTCFG/MemAttr, shareability, allocation, instruction, privilege, and NS attributes including MTCFG=0 memType suppression."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_STE_CFG_BYPASS",
          "description": "Apollo TBU names and accepts the modeled STE.Config all-bypass encoding while preserving existing ATS Translated rejection behavior through the compatibility alias."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "architectural STE.Config all-bypass",
          "description": "Apollo TBU returns identity translation for the modeled STE.Config all-bypass path and applies STE output attributes before downstream transport."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SteConfigBypassOutputAttributesPropagate",
          "description": "Component test verifies STE.Config all-bypass identity access plus MTCFG/MemAttr, shareability, allocation, instruction, privilege, and NS output-attribute propagation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ats-translated",
          "description": "Apollo TBU records modeled STE output attributes on successful ATS Translated configuration checks and preserves them across translated payload routing."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "AtsTranslatedSteOutputAttributesPropagateWhenAtschkEnabled",
          "description": "Component test verifies MTCFG/MemAttr, shareability, allocation, instruction, privilege, and NS output attributes on the ATS Translated downstream TLM payload."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_CTRL_GATOS_TRANSLATE",
          "description": "Apollo TBU exposes a modeled compatibility-register command for bounded GATOS_PAR translation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "REG_ARCH_PAR_LO",
          "description": "Apollo TBU exposes a 64-bit GATOS_PAR return register through REG_ARCH_PAR_LO/HI."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_gatos_success_par",
          "description": "Apollo TBU encodes translated PA plus modeled STE ATTR/SH output attributes in successful GATOS_PAR values."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "GatosParReportsSteOutputAttributes",
          "description": "Component test verifies GATOS_PAR ATTR/SH fields from modeled STE output attributes."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "GatosParFaultCodeForUnmappedPage",
          "description": "Component test verifies GATOS_PAR fault bit, FAULTCODE, and REASON for an unmapped translation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "SMMUV3_GATOS_CTRL",
          "description": "Apollo TBU exposes the architected non-secure SMMU_GATOS_CTRL register at PAGE_0 offset 0x100."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "SMMUV3_GATOS_PAR_LO",
          "description": "Apollo TBU exposes the architected non-secure SMMU_GATOS_PAR readback register at PAGE_0 offset 0x118."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "run_arch_gatos_register_translate",
          "description": "RUN writes on SMMU_GATOS_CTRL execute the modeled ATOS translation, write PAR, clear RUN, and suppress EVENTQ/PRI side effects for ATOS faults."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "Smmuv3GatosRegistersRunAndClear",
          "description": "Component test verifies SMMU_GATOS_SID/ADDR input, RUN clear-on-completion, successful PAR PA bits, and readable SID/ADDR state."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "Smmuv3GatosFaultDoesNotRecordEvent",
          "description": "Component test verifies SMMU_GATOS fault PAR encoding without EVENTQ producer movement or fault-count side effects."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_secure_gatos_par",
          "description": "Apollo TBU stores an independent Secure SMMU_S_GATOS PAR value."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_smmu_enabled_for_security_state",
          "description": "Secure GATOS translation is gated by Secure CR0.SMMUEN instead of the Non-secure CR0 bank."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "architectural SMMU_S_GATOS register translation",
          "description": "Secure RUN writes execute through the Secure GATOS register path and log SMMU_S_GATOS completion."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureSmmuv3GatosRegistersUseSecureBank",
          "description": "Component test verifies Secure GATOS uses the Secure STRTAB bank and returns the Secure PA in PAR."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureSmmuv3GatosFaultDoesNotRecordEvent",
          "description": "Component test verifies Secure GATOS fault PAR encoding without Non-secure or Secure EVENTQ producer movement."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_ATOS_ADDR_TYPE_STAGE1_STAGE2",
          "description": "Apollo TBU decodes architected ATOS_ADDR.TYPE values for stage-1, stage-2, and stage-1+stage-2 GATOS requests."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_atos_validate_ste_config",
          "description": "Apollo TBU rejects reserved ATOS_ADDR.TYPE values with INV_REQ and unsupported stage requests with INV_STAGE before returning PAR."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "atos-stage2-translation",
          "description": "Apollo TBU can perform a bounded stage-2-only ATOS walk for nested streams when ATOS_ADDR.TYPE requests stage 2."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "Smmuv3GatosAddrTypeReservedAndInvStage",
          "description": "Component test verifies reserved ATOS_ADDR.TYPE returns INV_REQ, stage-2 on a stage-1-only stream returns INV_STAGE, and stage-1 succeeds."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "Smmuv3GatosAddrTypeNestedStageSelection",
          "description": "Component test verifies nested stream ATOS stage-1-only, stage-1+stage-2, and stage-2-only selection through SMMU_GATOS_PAR."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_ATOS_SID_SECURE_STREAM",
          "description": "Apollo TBU models SMMU_S_GATOS_SID.SSEC bit 53 for Secure versus Non-secure stream lookup selection."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureSmmuv3GatosSsecSelectsNonsecureStream",
          "description": "Component test verifies Secure ATOS SSEC-clear Non-secure stream lookup, including the Secure-CR0 gate and Non-secure STRTAB selection."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_last_atos_privileged",
          "description": "Apollo TBU records ATOS_ADDR.PnU from architected GATOS requests."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_last_atos_instruction",
          "description": "Apollo TBU records ATOS_ADDR.InD from architected GATOS requests."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "STE output attributes ignored for ATOS",
          "description": "Architected ATOS_PAR success suppresses modeled STE output-attribute overrides while preserving the compatibility GATOS_PAR path."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "Smmuv3GatosAddrAccessFieldsIgnoreSteOverrides",
          "description": "Component test validates ATOS_ADDR.PnU/InD/RnW decode and architected ATOS_PAR STE-override suppression."
        }
      ],
      "runtime_evidence": [
        {
          "path": "build/verification/apollo-smmuv3-strtab-streamid-ctest-20260510.log",
          "pattern": "100% tests passed",
          "description": "CTest confirms the linear/two-level STRTAB StreamID component tests pass."
        },
        {
          "path": "build/verification/qbox-platform-smmu-comp-030-strtab-streamid-20260510.log",
          "pattern": "QBox Buildroot platform runtime built",
          "description": "Full QBox platform runtime rebuild passes with the STRTAB StreamID changes."
        },
        {
          "path": "build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-030-strtab-streamid.driver.log",
          "pattern": "PASS: QBox guest IREE Hexagon tiny-CNN output matched",
          "description": "Guest IREE Hexagon smoke still passes after the STRTAB StreamID slice."
        },
        {
          "path": "doc/verification/qbox-smmuv3-comp-030-verification-2026-05-10.md",
          "pattern": "ARCH_FAULT_BAD_STREAM_ID",
          "description": "Verification report records invalid StreamID replay evidence and remaining blockers."
        },
        {
          "path": "build/verification/apollo-smmuv3-cd-table-ssid-ctest-20260510.log",
          "pattern": "100% tests passed",
          "description": "CTest confirms the CD-table SSID indexing component vector passes."
        },
        {
          "path": "doc/verification/qbox-smmuv3-cd-table-ssid-verification-2026-05-10.md",
          "pattern": "FEATURE_ARCH_CD_TABLE_INDEX",
          "description": "Verification report records the CD-table SSID indexing slice evidence and remaining blockers."
        },
        {
          "path": "build/verification/qbox-platform-smmu-cd-table-ssid-20260510.log",
          "pattern": "QBox Buildroot platform runtime built",
          "description": "Full QBox platform runtime rebuild passes with the CD-table SSID indexing changes."
        },
        {
          "path": "build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-cd-table-ssid.driver.log",
          "pattern": "PASS: QBox guest IREE Hexagon tiny-CNN output matched",
          "description": "Guest IREE Hexagon smoke still passes after the CD-table SSID indexing slice."
        },
        {
          "path": "build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-reserved-encoding.log",
          "pattern": "features=0xffff",
          "description": "Guest runtime log exposes the updated Apollo TBU feature bitmap including FEATURE_ARCH_RESERVED_ENCODING_CHECKS."
        },
        {
          "path": "build/verification/apollo-smmuv3-s1dss-policy-ctest-20260510.log",
          "pattern": "100% tests passed",
          "description": "CTest confirms the S1DSS no-substream terminate/bypass component vector passes."
        },
        {
          "path": "doc/verification/qbox-smmuv3-s1dss-policy-verification-2026-05-10.md",
          "pattern": "ARCH_STE_S1DSS_BYPASS",
          "description": "Verification report records S1DSS bypass/terminate evidence and remaining blockers."
        },
        {
          "path": "build/verification/qbox-platform-smmu-s1dss-policy-20260510.log",
          "pattern": "QBox Buildroot platform runtime built",
          "description": "Full QBox platform runtime rebuild passes with the S1DSS policy changes."
        },
        {
          "path": "build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-s1dss-policy.driver.log",
          "pattern": "PASS: QBox guest IREE Hexagon tiny-CNN output matched",
          "description": "Guest IREE Hexagon smoke still passes after the S1DSS policy slice."
        },
        {
          "path": "build/verification/apollo-smmuv3-s1dss-nested-s2-ctest-20260510.log",
          "pattern": "100% tests passed",
          "description": "CTest confirms the nested S1DSS-bypass stage-2 component vector passes."
        },
        {
          "path": "doc/verification/qbox-smmuv3-s1dss-nested-s2-verification-2026-05-10.md",
          "pattern": "architectural nested S1DSS bypass stage-2 walk",
          "description": "Verification report records nested S1DSS bypass stage-2 evidence and remaining blockers."
        },
        {
          "path": "doc/verification/qbox-smmuv3-nested-cd-fetch-s2-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/040/050 nested CD fetch stage-2 functional slice",
          "description": "Verification report records nested CD fetch stage-2 walk and CLASS=CD fault evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-nested-tt-fetch-s2-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/040/050 nested TT fetch stage-2 functional slice",
          "description": "Verification report records nested stage-1 TT descriptor fetch stage-2 walk and CLASS=TT fault evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-nested-l1cd-fetch-s2-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/040/050 nested L1CD fetch stage-2 functional slice",
          "description": "Verification report records nested 64K-L2 L1CD fetch stage-2 walk and CLASS=CD fault evidence."
        },
        {
          "path": "build/verification/qbox-platform-smmu-s1dss-nested-s2-20260510.log",
          "pattern": "QBox Buildroot platform runtime built",
          "description": "Full QBox platform runtime rebuild passes with the nested S1DSS-bypass stage-2 changes."
        },
        {
          "path": "build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-s1dss-nested-s2.driver.log",
          "pattern": "PASS: QBox guest IREE Hexagon tiny-CNN output matched",
          "description": "Guest IREE Hexagon smoke still passes after the nested S1DSS-bypass stage-2 slice."
        },
        {
          "path": "build/verification/apollo-smmuv3-reserved-encoding-ctest-20260510.log",
          "pattern": "100% tests passed",
          "description": "CTest confirms the modeled STE/CD reserved and illegal encoding component vector passes."
        },
        {
          "path": "doc/verification/qbox-smmuv3-reserved-encoding-verification-2026-05-10.md",
          "pattern": "ArchitectedSteCdReservedEncodingFaults",
          "description": "Verification report records reserved/illegal STE/CD encoding evidence and remaining blockers."
        },
        {
          "path": "build/verification/qbox-platform-smmu-reserved-encoding-20260510.log",
          "pattern": "QBox Buildroot platform runtime built",
          "description": "Full QBox platform runtime rebuild passes with the reserved/illegal encoding checks."
        },
        {
          "path": "build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-reserved-encoding.driver.log",
          "pattern": "PASS: QBox guest IREE Hexagon tiny-CNN output matched",
          "description": "Guest IREE Hexagon smoke still passes after the reserved/illegal encoding slice."
        },
        {
          "path": "doc/verification/qbox-smmuv3-endpoint-ssid-verification-2026-05-10.md",
          "pattern": "Endpoint PASID/SSID functional slice",
          "description": "Verification report records component/platform/guest evidence for endpoint SubstreamID propagation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-linux-cmd-invalidation-verification-2026-05-10.md",
          "pattern": "SMMUv3 command invalidation selftest ok",
          "description": "Runtime report captures the Linux command invalidation probe marker."
        },
        {
          "path": "doc/verification/qbox-smmuv3-stream-substream-events-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/050 stream/substream EVENTQ functional slice",
          "description": "Verification report records F_STREAM_DISABLED/C_BAD_SUBSTREAMID event-number mapping, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-security-state-gate-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/050 security-state unsupported-gate functional slice",
          "description": "Verification report records prior build, focused gTest/CTest, static checker, and lane evidence for security-state rejection."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-endpoint-acceptance-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/050 Secure/Realm/Root endpoint acceptance slice",
          "description": "Verification report records Secure/Realm/Root endpoint read/debug-read acceptance plus invalid security-state rejection evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-security-eventq-routing-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 security-state EVENTQ routing functional slice",
          "description": "Verification report records modeled EVENTQ security-state route accounting plus per-state logical bank mirrors and configured Secure-bank routing for rejected events."
        },
        {
          "path": "doc/verification/qbox-smmuv3-security-eventq-bank-mirror-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 security-state EVENTQ bank mirror functional slice",
          "description": "Verification report records per-security-state logical EVENTQ bank mirrors for committed records."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-eventq-bank-route-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 configured Secure EVENTQ bank route",
          "description": "Verification report records configured Secure EVENTQ bank routing, component CTest, static checker, lane, and guest regression evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-strtab-bank-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030 Secure stream-table bank selection functional slice",
          "description": "Verification report records configured Secure STRTAB bank selection and focused component evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-s2ttb-nscfg-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/040 Secure stage-2 table-base selection functional slice",
          "description": "Verification report records Secure stage-2-only NSCFG selection between S2TTB and S_S2TTB."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-stage1-nsipa-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/040 Secure stage-1-derived NSIPA selection functional slice",
          "description": "Verification report records build, CTest, static checker, lane, and guest evidence for Secure nested stage-1-derived S2TTB/S_S2TTB selection."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-stage1-ttfetch-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/040 Secure nested stage-1 translation-table descriptor fetch",
          "description": "Verification report records Secure nested stage-1 TT-fetch S2TTB/S_S2TTB selection evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ste-s2r-s2s-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/050 STE.S2R/S2S stage-2 record/stall policy",
          "description": "Verification report records build, focused gTest/CTest, static checker, lane, and closure evidence for STE.S2R/S2S."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ste-s2s-stall-model-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/050 STE.S2S terminate-only STALL_MODEL validation",
          "description": "Verification report records build, focused gTest/CTest, static checker, lane, and closure evidence for terminate-only STALL_MODEL validation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ste-bypass-output-attrs-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/080 STE bypass output-attribute propagation",
          "description": "Verification report records build, focused gTest/CTest, static checker, lane, and closure evidence for modeled STE bypass output-attribute propagation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ste-config-bypass-output-attrs-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/080 STE.Config all-bypass output-attribute propagation",
          "description": "Verification report records build, focused gTest/CTest, static checker, lane, and closure evidence for modeled STE.Config all-bypass output-attribute propagation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-output-attrs-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/080 ATS Translated STE output-attribute propagation",
          "description": "Verification report records build, focused gTest/CTest, static checker, lane, and closure evidence for ATS Translated output-attribute propagation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-gatos-par-output-attrs-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/080 GATOS_PAR STE output-attribute return path",
          "description": "Verification report records build, focused gTest/CTest, static checker, lane, and closure evidence for bounded GATOS_PAR output attributes."
        },
        {
          "path": "doc/verification/qbox-smmuv3-architected-gatos-registers-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/030/080 architected non-secure SMMU_GATOS register slice",
          "description": "Verification report records build, focused gTest/CTest, static checker, lane, and closure evidence for the non-secure SMMU_GATOS RUN/PAR/no-event path."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-gatos-registers-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/030/080 Secure SMMU_S_GATOS register slice",
          "description": "Verification report records build, focused gTest/CTest, static checker, lane, and closure evidence for the Secure SMMU_S_GATOS RUN/PAR/no-event path."
        },
        {
          "path": "build/verification/smmu-atos-addr-type-build-20260511.log",
          "pattern": "Built target apollo-smmu-tbu-tests",
          "description": "Apollo SMMU TBU tests rebuild after ATOS_ADDR.TYPE matrix implementation."
        },
        {
          "path": "build/verification/smmu-atos-addr-type-gtest-20260511.log",
          "pattern": "Smmuv3GatosAddrTypeNestedStageSelection",
          "description": "Focused gTest exercises reserved/INV_STAGE and nested ATOS_ADDR.TYPE stage-selection cases."
        },
        {
          "path": "build/verification/smmu-atos-addr-type-ctest-20260511.log",
          "pattern": "100% tests passed",
          "description": "CTest regression passes for the Apollo SMMU TBU component suite after ATOS_ADDR.TYPE changes."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-gatos-ssec-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/080 S_GATOS.SSEC stream-selection slice",
          "description": "Verification report records build, focused gTest, CTest, static checker, and lane evidence for S_GATOS.SSEC stream selection."
        },
        {
          "path": "build/verification/smmu-secure-gatos-ssec-gtest-20260511.log",
          "pattern": "[  PASSED  ]",
          "description": "Focused gTest covers Secure GATOS SSEC Secure and Non-secure stream-selection paths."
        },
        {
          "path": "doc/verification/qbox-smmuv3-atos-access-fields-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/080 ATOS_ADDR access-field attribute slice",
          "description": "Verification report records build, focused gTest, CTest, static checker, lane, and closure evidence for the bounded ATOS_ADDR access-field attribute slice."
        },
        {
          "path": "build/verification/smmu-atos-access-fields-gtest-20260511.log",
          "pattern": "[  PASSED  ]",
          "description": "Focused gTest covers ATOS_ADDR.PnU/InD/RnW decode and STE-output-override suppression while preserving the compatibility GATOS_PAR path."
        }
      ]
    },
    {
      "id": "SMMU-COMP-040",
      "title": "Architected page-table walker matrix",
      "status": "functional-slice",
      "owner": "Apollo TBU",
      "claim_scope": "Selected 4K/16K/64K granule, command TLBI range invalidation, IDR3.RIL Linux range-command stress, modeled additional NSNH/EL2/EL3/S12/S2 plus scoped TLBI_NSNH_ALL invalidation and Secure-only S-EL2/S-S12/S-S2/SNH TLBI opcode coverage, reserved range encoding rejection, TTL/TG leaf-level filtering, and Leaf=0 table-walk cache invalidation accounting, block/page leaf, AF/permission fault, stage-2-only, nested CD/L1CD/TT-fetch/S2, nested S1+S2 including Secure stage-1-derived IPA-space S2TTB/S_S2TTB selection plus Secure stage-1 TT-fetch S2TTB/S_S2TTB selection, and nested S1DSS-bypass/S2 walker vectors are component-tested; full Arm reference-vector parity remains open. The slice now also covers bounded CD.E0PD unprivileged translation-fault behavior and nested stage-1 descriptor-fetch PTWNNC normalization for Device-mapped stage-2 memory.",
      "source_evidence": [
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_GRANULE_64K",
          "description": "TBU exposes functional walker granule configuration for 4K/16K/64K component vectors."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_STE_CFG_NESTED",
          "description": "TBU decodes selected stage-2-only and nested S1+S2 STE modes."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedWalkerGranuleBlockAndFaultMatrix",
          "description": "CTest covers selected 16K granule, block descriptor, access-flag, and permission fault vectors."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedWalkerStage2AndNestedMatrix",
          "description": "CTest covers selected stage-2-only, nested CD/TT-fetch/S2, nested S1+S2, and stage-2 fault vectors."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "architectural nested CD fetch stage-2 walk",
          "description": "TBU emits the nested CD fetch stage-2 walker path log and uses the S2 descriptor walker for CD IPA translation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "architectural nested L1CD fetch stage-2 walk",
          "description": "TBU emits the nested 64K-L2 L1CD fetch stage-2 walker path log and uses the S2 descriptor walker for L1CD IPA translation."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedNestedL1CdFetchStage2Walks",
          "description": "Component vector verifies the nested 64K-L2 L1CD fetch success path with stage-2 translation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "stage2_translate_descriptor_fetch",
          "description": "TBU uses the stage-2 descriptor walker for nested stage-1 translation-table descriptor fetch IPA translation."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedNestedTtFetchStage2FaultRecordsClassTt",
          "description": "Component vector verifies a nested stage-1 TT descriptor fetch S2 translation fault records CLASS=TT."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-selftest.c",
          "pattern": "SMMUv3 architectural descriptor probe ok 4-level",
          "description": "Linux probe still checks the staged 4-level compatibility descriptor path."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "architectural nested S1DSS bypass stage-2 walk",
          "description": "TBU emits the nested S1DSS-bypass stage-2 walker path log and uses the S2 descriptor walker."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "bypass_s2ttb",
          "description": "Stage-2/nested matrix includes a nested S1DSS-bypass S2 translation vector."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_last_s1_output_nonsecure_ipa",
          "description": "TBU records Secure stage-1-derived Non-secure IPA output state before final nested stage-2 table selection."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureNestedStage1OutputNsSelectsS2Ttb",
          "description": "Component vector verifies Secure nested S1+S2 table selection from CD.NSCFG0 and leaf NS output."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "architectural nested stage-1 TT fetch stage-2 walk",
          "description": "TBU logs the nested stage-1 TT descriptor fetch stage-2 walk and selected Secure/Non-secure IPA table root."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "clear_ats_cache_nsnh",
          "description": "Scoped TLBI_NSNH_ALL helper removes only ATS entries tagged with the modeled NSNH TLBI regime."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdqTlbiNsnhAllPreservesEl2RegimeEntries",
          "description": "Component test verifies modeled TLBI_NSNH_ALL invalidates only NSNH-tagged ATS entries and preserves explicitly tagged EL2-regime entries."
        }
      ],
      "runtime_evidence": [
        {
          "path": "build/verification/apollo-smmuv3-walker-matrix-ctest-20260510.log",
          "pattern": "100% tests passed",
          "description": "Component CTest passes with the expanded walker matrix vectors."
        },
        {
          "path": "doc/verification/qbox-smmuv3-comp-040-verification-2026-05-10.md",
          "pattern": "ArchitectedWalkerStage2AndNestedMatrix",
          "description": "Verification report records the walker matrix scope, evidence, and remaining blockers."
        },
        {
          "path": "doc/verification/qbox-smmuv3-nested-cd-fetch-s2-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/040/050 nested CD fetch stage-2 functional slice",
          "description": "Verification report records nested CD fetch stage-2 walker evidence and remaining blockers."
        },
        {
          "path": "doc/verification/qbox-smmuv3-nested-tt-fetch-s2-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/040/050 nested TT fetch stage-2 functional slice",
          "description": "Verification report records nested TT descriptor fetch stage-2 walker evidence and remaining blockers."
        },
        {
          "path": "doc/verification/qbox-smmuv3-nested-l1cd-fetch-s2-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/040/050 nested L1CD fetch stage-2 functional slice",
          "description": "Verification report records nested L1CD fetch stage-2 walker evidence and remaining blockers."
        },
        {
          "path": "build/verification/apollo-smmuv3-s1dss-nested-s2-ctest-20260510.log",
          "pattern": "100% tests passed",
          "description": "Component CTest passes with the nested S1DSS-bypass S2 walker vector."
        },
        {
          "path": "doc/verification/qbox-smmuv3-s1dss-nested-s2-verification-2026-05-10.md",
          "pattern": "bypass_s2ttb",
          "description": "Verification report records the nested S1DSS-bypass S2 walker vector and remaining parity blockers."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-stage1-nsipa-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/040 Secure nested stage-1-derived NSIPA selection functional",
          "description": "Verification report records Secure nested stage-1-derived S2TTB/S_S2TTB component, static, lane, and guest regression evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-stage1-ttfetch-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/040 Secure nested stage-1 translation-table descriptor fetch",
          "description": "Verification report records Secure nested stage-1 TT-fetch S2TTB/S_S2TTB component, static, lane, and guest regression evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-idr5-granule-oas-verification-2026-05-11.md",
          "pattern": "bounded granules and 48-bit OAS behavior",
          "description": "Report ties IDR5 discovery to the existing bounded walker/OAS functional slices."
        },
        {
          "path": "doc/verification/qbox-smmuv3-e0pd-ptwnnc-behavior-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-040/050/060 E0PD/PTWNNC behavior slice",
          "description": "Verification report records bounded E0PD and PTWNNC behavior evidence."
        },
        {
          "path": "build/verification/smmu-e0pd-ptwnnc-behavior-gtest-20260511.log",
          "pattern": "\\[  PASSED  \\] 2 tests\\.",
          "description": "Focused gTest covers E0PD unprivileged-fault behavior and nested descriptor-fetch PTWNNC normalization."
        }
      ]
    },
    {
      "id": "SMMU-COMP-050",
      "title": "Fault/event replay matrix",
      "status": "functional-slice",
      "owner": "Apollo TBU + Apollo Linux probe",
      "claim_scope": "Architected common EVENTQ event numbers/substream fields including modeled F_STREAM_DISABLED/C_BAD_SUBSTREAMID for S1DSS/substream faults with C_BAD_SUBSTREAMID InputAddr payload validation, F_TRANSL_FORBIDDEN for SMMUEN/ATSCHK/EATS rejected Translated transactions, ATS Translated address-size no-event abort behavior, stage-2-only and architected nested split-stage ATS Translated IPA walks plus implementation-defined rejection for unsupported non-stage2/non-nested split-stage traffic, STE.Config==0b100 F_TRANSL_FORBIDDEN aborts, DPT register RES0/WI policy plus DPT EATS unsupported F_TRANSL_FORBIDDEN aborts, PASIDTT-disabled SSV/PnU/InD clearing, ATSCHK==0 Translated configuration-lookup bypass, partial ATS Translated event-priority validation for C_BAD_STREAMID/F_STE_FETCH/C_BAD_STE/F_VMS_FETCH before F_TRANSL_FORBIDDEN, CR2.REC_CFG_ATS-gated ATS Translated configuration-fault records, and modeled F_TLB_CONFLICT/F_CFG_CONFLICT event-number plus implementation-defined word3 Reason payload plumbing for conflict reports plus component-tested ATS/TLB cache-conflict detection/recovery and STE configuration-cache conflict detection/recovery, modeled F_UUT unsupported-upstream event-number plus zero-Reason injection, unsupported security-state rejection, and EVENTQ security-state route accounting plus per-state logical bank mirrors and configured Secure-bank routing for modeled Secure fault events plus invalid-state events routed by masked Root event-state accounting, C_BAD_STREAMID CR2.RECINVSID event-recording suppression for normal probes, non-stall C_BAD_STREAMID/C_BAD_STE/C_BAD_CD/F_STREAM_DISABLED RES0 payload encoding, suppresses EVENTQ records for valid STE.Config==0 disabled-stream aborts, STE.S2R/S2S-controlled stage-2 fault record/stall behavior including terminate-only STALL_MODEL invalid-STE validation, syndrome detail via private status, modeled PnU/InD/RnW plus CLASS=IN/TT/CD access class attributes for stalled translation faults, stage-2 IPA word3 layout including nested CD/L1CD and TT fetch translation failures, modeled NSIPA bit plumbing for supplied stalled stage-2 records, modeled STE/CD/F_WALK_EABT/F_VMS_FETCH fetch-address word3 layout plus actual STE.VMSPtr-triggered F_VMS_FETCH recording, IDR3.MPAM/MPAMIDR VMS discovery, full 64-byte VMS PARTID_MAP fetch/cache fill, CD.PARTID/PMG VMS PARTID_MAP remap plus STE.PARTID/PMG fallback assignment into downstream TLM MPAM attributes with MPAMIDR range-to-UNKNOWN handling and GBPMPAM global-bypass assignment plus GMPAM queue/MSI write, CMDQ/STE/VMS fetch attributes, STE-sourced CD fetch attributes, S1MPAM CD/helper-walk STE attributes before CD/VMS override, client-derived TT fetch attributes, and ATS Translated ATSCHK-disabled GBPMPAM plus ATSCHK-enabled STE/CD-sourced MPAM attributes, non-stall fetch-fault Reason/GPCF word1 encoding, modeled GPCF bit plumbing for fetch-event records, stall-pending state, STAG/STALL bits, StreamID+STAG matched CMD_RESUME, stream-wide CMD_STALL_TERM, duplicate stalled-fault suppression/merge, endpoint early retry without duplicate EVENTQ records while preserving CMD_RESUME acknowledgement plus stale uncommitted EVENTQ discard, negative replay matrix coverage, endpoint replay accounting, downstream replay transaction wrapping plus payload re-drive, and opt-in caller blocking until CMD_RESUME retry, overflow retention, CR0.EVENTQEN gating, EVENTQ OVFLG/OVACKFLG overflow acknowledgement, EVENTQ_ABT_ERR queue-write abort reporting, and full-queue stall-event buffering/redrive preserves the original security-state route when records are buffered before redrive; full event matrix parity, full Secure event-queue/security-state routing beyond SMMU_S_EVENTQ bank routing, full RME/GPT/GPC, broader real-hardware configuration-cache geometry parity, and upstream arm-smmu-v3 recovery parity remain open. The slice also includes explicit security-state-derived MPAM PARTID-space tagging plus Secure GBPMPAM/GMPAM register-bank attribute selection in the Apollo SMMU TLM extension/status for modeled Non-secure, Secure, Realm, and Root endpoint states. The slice also accepts modeled Secure, Realm, and Root endpoint transactions on the existing translation path and rejects invalid security-state transactions before translation while Root and complete Realm RME/GPT/GPC paths remain out of scope for the current QBox security-state model. The slice now also covers bounded CD.E0PD unprivileged translation-fault behavior and nested stage-1 descriptor-fetch PTWNNC normalization for Device-mapped stage-2 memory.",
      "source_evidence": [
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "FEATURE_ARCH_EVENT_RECORD_LAYOUT",
          "description": "TBU advertises the architected common EVENTQ record layout slice."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_EVENT_C_BAD_CD",
          "description": "TBU maps modeled fault reasons onto architected EVENTQ event numbers."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "REG_ARCH_FAULT_DETAIL",
          "description": "TBU exposes the latest fault syndrome detail word for replay verification."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "complete_stall",
          "description": "TBU consumes CMD_RESUME retry/terminate responses for pending stall records."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "terminate_stalls_for_stream",
          "description": "TBU consumes CMD_STALL_TERM and terminates modeled pending stalls for a StreamID."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "FaultReplayRecordsSyndromeAndResumeState",
          "description": "Component test covers CD/page fault syndrome detail and RESUME retry/terminate state."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedEventRecordLayoutCarriesSubstream",
          "description": "Component test verifies EVENTQ event number, StreamID, SubstreamID/SSV, InputAddr, and detail words."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdStallTermTerminatesPendingStalls",
          "description": "Component test verifies CMD_STALL_TERM termination accounting for modeled pending stalls."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "FaultReplayFullEventQueueBuffersAndRedrivesStall",
          "description": "Component test covers full EVENTQ stall buffering without setting OVFLG and redrive when software advances EVENTQ_CONS."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-selftest.c",
          "pattern": "SMMUv3 negative fault replay ok",
          "description": "Linux probe still validates the compatibility invalid-STE replay marker."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_QUEUE_OVFLG",
          "description": "TBU exposes the architected output queue overflow flag bit used by EVENTQ_PROD and EVENTQ_CONS."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "EventAndPriQueueOverflowFlagsToggleAndAck",
          "description": "Component test verifies EVENTQ OVFLG toggles once per unacknowledged overflow and clears when software writes OVACKFLG."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_GERROR_EVENTQ_ABORT",
          "description": "TBU exposes the architected EVENTQ_ABT_ERR GERROR bit for Event queue access aborts."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "EventAndPriQueueWriteAbortUseArchitectedGerrorBits",
          "description": "Component test verifies failed Event queue record writes set EVENTQ_ABT_ERR and are acknowledged through GERRORN."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "FEATURE_ARCH_STALL_BUFFER_REDRIVE",
          "description": "TBU advertises the full-queue stalled EVENTQ buffer/redrive functional slice."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_EVENT_STAG_MASK",
          "description": "Stalled EVENTQ word1 carries architected STAG bits and the STALL marker."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_CMD_RESUME_STAG_MASK",
          "description": "CMD_RESUME decodes STAG from command word1 and response from word0."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdResumeMatchesStreamIdAndStag",
          "description": "Component test validates StreamID+STAG matching and unknown-resume accounting."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_CTRL_NEGATIVE_REPLAY_WRITE",
          "description": "Write-negative replay command records permission faults with the write attribute."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "NegativeFaultReplayMatrixRecordsArchitectedEvents",
          "description": "Component test covers stalled replay records for bad StreamID, bad STE, bad CD, access, and permission faults."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "REG_ARCH_ENDPOINT_REPLAY_STATUS",
          "description": "TBU exposes pending/retry/success/terminate accounting for stalled endpoint replay records."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "complete_endpoint_replay",
          "description": "CMD_RESUME retry re-runs translation for the matching StreamID+STAG endpoint replay record."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "EndpointTransactionReplayRetriesAfterCmdResume",
          "description": "Component test validates endpoint replay accounting and retry translation after CMD_RESUME."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "redrive_endpoint_replay",
          "description": "TBU replays the held endpoint payload through downstream TLM after a matching CMD_RESUME retry."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "EndpointTransactionReplayRedrivesWritePayload",
          "description": "Component test validates held write payload re-drive to downstream memory after CMD_RESUME retry."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "wait_endpoint_replay_resume",
          "description": "TBU can wait a caller-visible endpoint transaction until CMD_RESUME retry resumes the matching replay record."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "EndpointTransactionReplayBlocksCallerUntilCmdResume",
          "description": "Component test validates opt-in caller blocking until matching CMD_RESUME retry."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "early_retry_endpoint_replays",
          "description": "TBU can retry pending endpoint replay records with current translations without clearing the pending STAG."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "EndpointEarlyRetryDoesNotDuplicateFaultAndRequiresResume",
          "description": "Component test validates early retry does not emit another EVENTQ record and still requires CMD_RESUME acknowledgement."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "discard_uncommitted_early_retry",
          "description": "TBU discards a buffered, uncommitted stale stalled EVENTQ record after successful early retry."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "EndpointEarlyRetryDiscardsUncommittedStaleEvent",
          "description": "Component test validates the permitted stale-event discard policy for buffered stalled faults."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "find_stall_by_fault",
          "description": "TBU finds an existing pending stall by StreamID, IOVA, and SSID to suppress duplicate records."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "StalledFaultsSuppressDuplicateEventRecords",
          "description": "Component test validates duplicate stalled faults merge onto the existing STAG without pushing another EVENTQ record."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_EVENT_PNU_SHIFT",
          "description": "Stalled translation EVENTQ word1 encodes the modeled PnU common access attribute at the Linux arm-smmu-v3 EVTQ_1_PnU bit."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_EVENT_IND_SHIFT",
          "description": "Stalled translation EVENTQ word1 encodes the modeled InD common access attribute and forces it low for writes."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_EVENT_CLASS_IN",
          "description": "Translation-fault EVENTQ word1 uses CLASS=IN for input-address faults."
        },
        {
          "path": "sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h",
          "pattern": "privileged",
          "description": "Endpoint metadata can carry modeled privilege attributes into the TBU fault path."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedEventRecordCommonAccessAttributesAreEncoded",
          "description": "Component test verifies PnU/InD/RnW and CLASS=IN encoding for stalled translation EVENTQ records."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "EndpointAccessAttributesPropagateToFaultEvent",
          "description": "Component test verifies endpoint TLM privilege/instruction metadata propagates into stalled EVENTQ PnU/InD/RnW fields."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_event_class_for_fault",
          "description": "EVENTQ word1 selects CLASS=TT for modeled translation-table faults instead of forcing all translation events to CLASS=IN."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedEventRecordClassDistinguishesTableFaults",
          "description": "Component test verifies translation-table faults encode CLASS=TT in stalled EVENTQ records."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_fault_event_class",
          "description": "TBU carries an event-class selector for modeled stage-2 CD/TT/IN translation-fault records."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedEventRecordStage2CdFaultUsesClassCd",
          "description": "Component test verifies CD-originated stage-2 translation faults encode CLASS=CD and IPA word3 data."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedNestedCdFetchStage2FaultRecordsClassCd",
          "description": "Component test verifies the nested CD-fetch/S2 failure path records a stalled EVENTQ record with S2, CLASS=CD, InputAddr, and CD IPA."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedNestedL1CdFetchStage2FaultRecordsClassCd",
          "description": "Component test verifies the nested 64K-L2 L1CD-fetch/S2 failure path records a stalled EVENTQ record with S2, CLASS=CD, InputAddr, and L1CD fetch IPA."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedNestedTtFetchStage2FaultRecordsClassTt",
          "description": "Component test verifies the nested stage-1 TT descriptor-fetch/S2 failure path records a stalled EVENTQ record with S2, CLASS=TT, InputAddr, and TT fetch IPA."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_EVENT_IPA_MASK",
          "description": "EVENTQ word3 encodes the architected stage-2 IPA field mask for modeled stage-2 faults."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_event_record_word3",
          "description": "TBU separates byte-exact EVENTQ word3 IPA/fetch-address layout data from private fault detail status."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedEventRecordStage2IpaIsEncoded",
          "description": "Component test verifies stalled stage-2 translation faults encode IPA in EVENTQ word3."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_EVENT_NSIPA_SHIFT",
          "description": "EVENTQ word1 exposes the architected NSIPA bit position for modeled stalled stage-2 fault records."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedEventRecordNsipaBitIsEncoded",
          "description": "Component test verifies modeled stalled stage-2 EVENTQ records can encode the NSIPA bit and IPA word3 data."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedEventRecordFetchAddressIsEncoded",
          "description": "Component test verifies F_STE_FETCH/F_CD_FETCH records encode fetch addresses in EVENTQ word3."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_EVENT_F_WALK_EABT",
          "description": "TBU maps descriptor-fetch external aborts to the architected F_WALK_EABT event number."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedEventRecordWalkEabtCarriesFetchAddress",
          "description": "Component test verifies F_WALK_EABT records carry CLASS=TT, InputAddr, and FetchAddr fields."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_EVENT_F_VMS_FETCH",
          "description": "TBU maps VMS fetch external aborts to the architected F_VMS_FETCH event number."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedEventRecordVmsFetchCarriesFetchAddress",
          "description": "Component test verifies F_VMS_FETCH records carry SubstreamID and FetchAddr word3 fields."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_EVENT_GPCF_SHIFT",
          "description": "TBU exposes the EVENTQ GPCF bit position used by modeled fetch-event records."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedEventRecordFetchGpcfBitIsEncoded",
          "description": "Component test verifies modeled fetch-event GPCF records set the EVENTQ bit while preserving FetchAddr."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_EVENT_F_STREAM_DISABLED",
          "description": "EVENTQ event-number mapping includes modeled F_STREAM_DISABLED for S1DSS stream-disabled cases."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_EVENT_C_BAD_SUBSTREAMID",
          "description": "EVENTQ event-number mapping includes modeled C_BAD_SUBSTREAMID for SubstreamID range/policy failures."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedStreamDisabledAndBadSubstreamEvents",
          "description": "Component vector verifies emitted stream/substream EVENTQ event numbers and StreamID/SSID fields."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_fault_record_suppressed",
          "description": "TBU carries an explicit no-event suppression flag for modeled faults that must not reach EVENTQ."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "AtsConfigDisabledReturnsUrWithoutEvent",
          "description": "Component vector verifies STE.Config==0 ATS Translation Requests return UR without recording EVENTQ entries."
        },
        {
          "path": "sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h",
          "pattern": "translated = false",
          "description": "TLM sideband can mark modeled ATS Translated endpoint transactions without changing default traffic."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_FAULT_TRANSL_FORBIDDEN",
          "description": "TBU has an explicit modeled fault reason for ATS Translated transactions forbidden by ATSCHK/EATS."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "allow_arch_translated_transaction",
          "description": "TBU checks modeled ATS Translated traffic against CR0.ATSCHK and effective STE.EATS before normal endpoint translation."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "AtsTranslatedTransactionForbiddenRecordsEvent",
          "description": "Component vector verifies forbidden translated traffic records F_TRANSL_FORBIDDEN and permitted EATS=FULL traffic continues."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_EVENT_F_TLB_CONFLICT",
          "description": "EVENTQ event-number mapping includes modeled F_TLB_CONFLICT for implementation-defined TLB conflict reports."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_EVENT_F_CFG_CONFLICT",
          "description": "EVENTQ event-number mapping includes modeled F_CFG_CONFLICT for implementation-defined configuration-cache conflict reports."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_EVENT_CONFLICT_REASON_TLB_TAG_MISMATCH",
          "description": "EVENTQ word3 mapping includes a modeled implementation-defined Reason payload for F_TLB_CONFLICT records."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_EVENT_CONFLICT_REASON_CFG_STE_CONT",
          "description": "EVENTQ word3 mapping includes a modeled implementation-defined Reason payload for F_CFG_CONFLICT records."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedConflictEventsAreMapped",
          "description": "Component vector verifies modeled conflict fault reasons emit F_TLB_CONFLICT/F_CFG_CONFLICT EVENTQ records with StreamID, InputAddr, and implementation-defined Reason word3 fields."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "record_config_cache_conflict_if_present",
          "description": "TBU detects modeled overlapping STE configuration-cache entries, records F_CFG_CONFLICT, and clears stale entries on recovery."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ConfigCacheConflictProbeRecordsAndRecovers",
          "description": "Component vector verifies modeled configuration-cache conflict recording, stale-entry recovery, and security-state isolation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_EVENT_F_UUT",
          "description": "EVENTQ event-number mapping includes modeled F_UUT for unsupported upstream transaction injection."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_CTRL_RECORD_F_UUT",
          "description": "Private compliance harness control can inject a modeled F_UUT record without requiring a real unsupported bus transaction."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedUnsupportedUpstreamEventCanBeInjected",
          "description": "Component vector verifies modeled F_UUT emits event number 0x01 with StreamID and zero implementation-defined Reason."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_record_bad_streamid_event",
          "description": "TBU gates normal C_BAD_STREAMID EVENTQ recording on SMMU_CR2.RECINVSID while preserving private fault status."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "BadStreamIdHonorsCr2RecInvsidForEventRecording",
          "description": "Component vector verifies out-of-range StreamID faults suppress EVENTQ records until CR2.RECINVSID is set."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_event_record_has_res0_payload",
          "description": "TBU zeros non-stall configuration-event payload words for architected RES0 layouts."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedConfigEventPayloadsAreRes0",
          "description": "Component vector verifies non-stall C_BAD_STE, C_BAD_CD, and F_STREAM_DISABLED payload words are RES0."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_event_record_has_fetch_reason",
          "description": "Non-stall fetch-fault EVENTQ records use word1 for implementation-defined Reason/GPCF instead of InputAddr."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ARCH_EVENT_GPCF_SHIFT, cd_word1",
          "description": "Component vector verifies non-stall fetch-fault word1 carries modeled GPCF and Reason remains otherwise zero."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "AtsTranslatedSteFetchRecordsBeforeSteDecode",
          "description": "Component vector verifies ATS Translated F_STE_FETCH is detected before STE decode/EATS and is gated by CR2.REC_CFG_ATS."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "FEATURE_ARCH_VMS_FETCH",
          "description": "TBU advertises the modeled VMS fetch functional slice."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_fetch_vms_if_enabled",
          "description": "TBU decodes a modeled STE.VMSPtr word and maps VMS memory access aborts to F_VMS_FETCH."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "AtsTranslatedVmsFetchRecordsBeforeForbidden",
          "description": "Component vector verifies ATS Translated F_VMS_FETCH priority before F_TRANSL_FORBIDDEN with REC_CFG_ATS-gated recording."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_VMS_PARTID_MAP_WORDS",
          "description": "TBU models the VMS PARTID_MAP as eight 64-bit words."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_last_vms_partid_map",
          "description": "TBU stores the last fetched VMS PARTID_MAP cache-fill contents for verification."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "VmsFetchCachesFullPartidMap",
          "description": "Component test verifies the full 64-byte VMS PARTID_MAP is fetched through STE.VMSPtr."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "record_arch_mpam_from_cd",
          "description": "TBU resolves nested CD virtual PARTID through VMS.PARTID_MAP before stage-1 table walking."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "VmsPartidMapRemapsCdPartidToMpamExtension",
          "description": "Component test verifies VMS.PARTID_MAP remap and downstream TLM MPAM attribute propagation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "record_arch_mpam_from_ste",
          "description": "TBU assigns STE.PARTID/STE.PMG to client transactions when STE.S1MPAM is clear."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SteMpamAttributesPropagateWhenS1MpamDisabled",
          "description": "Component test verifies STE.PARTID/PMG fallback propagation to the Apollo SMMU TLM extension."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "apply_arch_mpam_range",
          "description": "TBU maps unsupported PARTID/PMG values to modeled UNKNOWN MPAM attributes."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "MpamRangeOverflowMarksUnknownAttributes",
          "description": "Component test verifies unsupported PARTID/PMG values are reported as UNKNOWN on the downstream TLM extension."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "record_arch_mpam_from_gbp",
          "description": "TBU applies GBPMPAM PARTID/PMG to global-bypass client transactions."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "GlobalBypassUsesGbpmpamAttributes",
          "description": "Component test verifies GBPMPAM attributes are propagated on the downstream TLM extension while SMMUEN is clear."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "populate_arch_mpam_extension",
          "description": "TBU applies SMMU_GMPAM attributes to modeled SMMU-originated queue/MSI writes."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "GmpamAttributesPropagateOnEventqWrites",
          "description": "Component test verifies GMPAM attributes are propagated on EVENTQ writes."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "apply_gmpam",
          "description": "TBU marks CMDQ, STE, L1STD, and VMS fetches for SMMU_GMPAM attributes."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "GmpamAttributesPropagateOnCmdqFetches",
          "description": "Component test verifies GMPAM attributes are propagated on CMDQ fetches."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "GmpamAttributesPropagateOnSteAndVmsFetches",
          "description": "Component test verifies GMPAM attributes are propagated on STE and VMS fetches."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "populate_arch_mpam_extension_from_state",
          "description": "TBU applies resolved STE/CD MPAM state to selected originated descriptor fetches."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SteMpamAttributesPropagateOnCdFetches",
          "description": "Component test verifies STE-sourced MPAM attributes are propagated on CD fetches."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "execute_descriptor_memory_read\\(desc_read, desc\\)",
          "description": "TBU applies resolved client MPAM state to translation-table descriptor fetches."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SteMpamAttributesPropagateOnS1TtFetches",
          "description": "Component test verifies MPAM attributes are propagated on S1 TT fetches."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SteMpamAttributesPropagateOnS2TtFetches",
          "description": "Component test verifies MPAM attributes are propagated on S2 TT fetches."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_last_ste5 = ste5",
          "description": "TBU retains the fetched STE word5 so S1MPAM paths can use STE.PMG/VMSPtr consistently for helper-walk MPAM attribution."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SteMpamAttributesPropagateOnS1MpamCdFetches",
          "description": "Component test covers STE-derived MPAM on CD fetches while STE.S1MPAM is set, followed by CD-derived client MPAM."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "NestedS1MpamAttributesPropagateOnStage2HelperWalks",
          "description": "Component test covers STE-derived MPAM on nested CD-fetch stage-2 helper walks and later CD/VMS-remapped stage-2 TT fetches."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "preserve_mpam_state",
          "description": "TBU preserves the MPAM decision made by the ATS Translated gate while routing the downstream payload."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "AtsTranslatedAtschkDisabledUsesGbpmpamAttributes",
          "description": "Component test covers GBPMPAM attributes on ATSCHK-disabled ATS Translated traffic."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "AtsTranslatedSteMpamAttributesPropagateWhenAtschkEnabled",
          "description": "Component test covers STE-derived MPAM attributes on ATSCHK-enabled ATS Translated traffic."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "AtsTranslatedCdMpamAttributesPropagateWhenS1MpamEnabled",
          "description": "Component test covers CD-derived MPAM attributes on ATSCHK-enabled ATS Translated traffic when STE.S1MPAM is enabled."
        },
        {
          "path": "sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h",
          "pattern": "mpam_partid_space",
          "description": "Apollo SMMU TLM extension carries the modeled MPAM PARTID space alongside PARTID/PMG."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_MPAM_SPACE_NONSECURE",
          "description": "Apollo TBU includes the Non-secure MPAM PARTID-space and security-state-derived PARTID-space mapping."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "MpamAttributesCarryNonSecurePartidSpace",
          "description": "Component test verifies downstream MPAM attributes and status expose the modeled Non-secure PARTID-space."
        },
        {
          "path": "sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h",
          "pattern": "security_state",
          "description": "Apollo SMMU TLM extension carries endpoint security-state metadata."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_security_state_supported",
          "description": "Apollo TBU supports Non-secure plus modeled Secure, Realm, and Root endpoint transactions while complete RME/GPT/GPC behavior remains gated."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureRealmRootEndpointAcceptedInvalidRejectedBeforeTranslation",
          "description": "Component test verifies Secure/Realm/Root-tagged traffic translates and invalid security-state traffic is rejected before translation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_mpam_partid_space_for_security_state",
          "description": "Apollo TBU derives modeled MPAM PARTID-space from the endpoint security state."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "MpamAttributesCarrySecurityPartidSpace",
          "description": "Component test verifies downstream MPAM attributes and status expose Non-secure, Secure, Realm, and Root PARTID spaces."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_gbpmpam_for_security_state",
          "description": "Apollo TBU selects SMMU_S_GBPMPAM for modeled Secure endpoint client attributes."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_gmpam_for_security_state",
          "description": "Apollo TBU selects SMMU_S_GMPAM for modeled Secure SMMU-originated attributes."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureMpamRegisterBanksDriveAttributes",
          "description": "Component test verifies Secure GBPMPAM/GMPAM register banks drive downstream MPAM attributes."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_fault_stage2_stall",
          "description": "TBU stores the STE.S2S-derived stall decision for stage-2 fault event emission."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_STALL_MODEL_TERMINATE_ONLY",
          "description": "TBU exposes a modeled terminate-only STALL_MODEL used to validate illegal stage-2 STE.S2S configurations."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SteS2sRejectedWhenStallModelTerminateOnly",
          "description": "Component test confirms C_BAD_STE/non-stall EVENTQ behavior for terminate-only STALL_MODEL and stage-2 S2S."
        }
      ],
      "runtime_evidence": [
        {
          "path": "doc/verification/qbox-smmuv3-comp-050-verification-2026-05-10.md",
          "pattern": "FaultReplayRecordsSyndromeAndResumeState",
          "description": "Verification report records the original SMMU-COMP-050 component and platform validation evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-event-record-layout-verification-2026-05-10.md",
          "pattern": "ArchitectedEventRecordLayoutCarriesSubstream",
          "description": "Follow-up report records EVENTQ common-layout and STALL_TERM validation evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-queue-ovflg-verification-2026-05-10.md",
          "pattern": "EVENTQ overflow toggles SMMU_EVENTQ_PROD.OVFLG",
          "description": "Follow-up report records EVENTQ overflow flag validation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-queue-abort-gerror-verification-2026-05-10.md",
          "pattern": "EVENTQ_ABT_ERR",
          "description": "Follow-up report records Event queue abort GERROR validation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-eventq-stall-buffer-redrive-verification-2026-05-10.md",
          "pattern": "FaultReplayFullEventQueueBuffersAndRedrivesStall",
          "description": "Follow-up report records full EVENTQ stall buffering and redrive validation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-security-stall-event-buffer-route-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 security-state stalled EVENTQ buffer route functional slice",
          "description": "Verification report records that buffered stalled EVENTQ records preserve their original security-state route when redriven."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-eventq-bank-route-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 configured Secure EVENTQ bank route",
          "description": "Verification report records that configured Secure EVENTQ records use a separate Event queue bank instead of the Non-secure EVENTQ."
        },
        {
          "path": "doc/verification/qbox-smmuv3-stag-resume-verification-2026-05-10.md",
          "pattern": "SMMU-COMP-050 STAG/RESUME functional slice",
          "description": "Follow-up report records STAG/STALL EVENTQ layout, StreamID+STAG CMD_RESUME, and stream-wide CMD_STALL_TERM validation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-negative-replay-suite-verification-2026-05-10.md",
          "pattern": "SMMU-COMP-050 negative fault replay matrix functional slice",
          "description": "Follow-up report records negative replay matrix validation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-endpoint-replay-verification-2026-05-10.md",
          "pattern": "SMMU-COMP-050 endpoint replay accounting functional slice",
          "description": "Follow-up report records endpoint replay accounting validation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-endpoint-redrive-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 endpoint replay redrive functional slice",
          "description": "Follow-up report records downstream endpoint payload re-drive validation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-endpoint-blocking-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 endpoint blocking replay functional slice",
          "description": "Follow-up report records caller-blocking endpoint replay validation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-early-retry-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 endpoint early-retry functional slice",
          "description": "Follow-up report records endpoint early-retry validation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-early-retry-discard-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 endpoint early-retry stale-event discard functional slice",
          "description": "Follow-up report records stale uncommitted EVENTQ discard validation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-stall-suppression-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 stall suppression merge functional slice",
          "description": "Follow-up report records duplicate stalled-fault suppression and STAG merge validation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-event-record-access-attrs-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 EVENTQ common access attributes functional slice",
          "description": "Follow-up report records EVENTQ PnU/InD/RnW and CLASS=IN validation evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-nested-cd-fetch-s2-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/040/050 nested CD fetch stage-2 functional slice",
          "description": "Follow-up report records nested CD fetch translation failures as S2 CLASS=CD EVENTQ records."
        },
        {
          "path": "doc/verification/qbox-smmuv3-nested-tt-fetch-s2-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/040/050 nested TT fetch stage-2 functional slice",
          "description": "Follow-up report records nested TT descriptor fetch translation failures as S2 CLASS=TT EVENTQ records."
        },
        {
          "path": "doc/verification/qbox-smmuv3-nested-l1cd-fetch-s2-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/040/050 nested L1CD fetch stage-2 functional slice",
          "description": "Follow-up report records nested L1CD fetch translation failures as S2 CLASS=CD EVENTQ records."
        },
        {
          "path": "doc/verification/qbox-smmuv3-event-record-vms-fetch-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 EVENTQ F_VMS_FETCH functional slice",
          "description": "Follow-up report records F_VMS_FETCH event number, SSV/SubstreamID, and fetch-address word3 validation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-event-record-gpcf-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 EVENTQ GPCF functional slice",
          "description": "Follow-up report records modeled GPCF bit plumbing validation for fetch-event records."
        },
        {
          "path": "doc/verification/qbox-smmuv3-event-record-nsipa-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 EVENTQ NSIPA functional slice",
          "description": "Follow-up report records modeled NSIPA bit plumbing validation for stalled stage-2 records."
        },
        {
          "path": "doc/verification/qbox-smmuv3-stream-substream-events-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/050 stream/substream EVENTQ functional slice",
          "description": "Verification report records F_STREAM_DISABLED/C_BAD_SUBSTREAMID event-number mapping, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-c-bad-substreamid-layout-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 C_BAD_SUBSTREAMID layout functional slice",
          "description": "Verification report records C_BAD_SUBSTREAMID SSV/SubstreamID and InputAddr payload evidence, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-forbidden-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated F_TRANSL_FORBIDDEN functional slice",
          "description": "Verification report records ATS Translated sideband rejection, F_TRANSL_FORBIDDEN event evidence, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-rec-cfg-ats-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated REC_CFG_ATS functional slice",
          "description": "Verification report records ATS Translated configuration-fault suppression until CR2.REC_CFG_ATS, C_BAD_STE/C_BAD_STREAMID recording, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-smmuen-atschk-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated SMMUEN/ATSCHK functional slice",
          "description": "Verification report records SMMUEN-disabled F_TRANSL_FORBIDDEN and ATSCHK==0 configuration-lookup bypass evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-address-size-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated address-size functional slice",
          "description": "Verification report records the spec-permitted no-event abort behavior for Translated addresses above the modeled PA size."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-split-stage-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated split-stage unsupported functional slice",
          "description": "Verification report records implementation-defined F_TRANSL_FORBIDDEN for EATS_SPLIT Translated traffic on QBox's unsupported split-stage IPA protocol."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-split-stage-s2-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated split-stage stage-2-only slice",
          "description": "Verification report records EATS_SPLIT ATS Translated IPA validation through the modeled stage-2-only compatibility walker while non-stage2/non-nested split-stage remains rejected."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-split-stage-nested-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 architected nested ATS Translated split-stage IPA walk slice",
          "description": "Verification report records EATS_SPLIT ATS Translated IPA validation through the architected Nested STE stage-2-only walker."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-treq-split-stage-nested-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-060 architected nested ATS Translation Request split-stage IPA walk slice",
          "description": "Verification report records EATS_SPLIT ATS Translation Request IPA validation through the architected Nested STE stage-2-only walker."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-split-stage-access-overrides-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated split-stage access-override slice",
          "description": "Verification report records STE.PRIVCFG/INSTCFG effective access overrides on the modeled Nested STE EATS_SPLIT ATS Translated stage-2-only path."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-config-abort-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated STE.Config abort functional slice",
          "description": "Verification report records F_TRANSL_FORBIDDEN for ATS Translated traffic targeting STE.Config==0b100."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-dpt-unsupported-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated DPT unsupported functional slice",
          "description": "Verification report records F_TRANSL_FORBIDDEN for EATS_DPT Translated traffic while QBox lacks a DPT model."
        },
        {
          "path": "doc/verification/qbox-smmuv3-dpt-register-res0-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050/060 DPT unsupported-register RES0 slice",
          "description": "Verification report records unsupported DPT register RES0/WI behavior alongside DPTI and ATS DPT rejection."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-pasidtt-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated PASIDTT disabled functional slice",
          "description": "Verification report records SSV/PnU/InD clearing for ATS Translated traffic while SMMU_IDR3.PASIDTT is 0."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-priority-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated priority functional slice",
          "description": "Verification report records partial ATS Translated priority evidence for configuration faults before F_TRANSL_FORBIDDEN."
        },
        {
          "path": "doc/verification/qbox-smmuv3-conflict-events-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 EVENTQ conflict events functional slice",
          "description": "Verification report records modeled F_TLB_CONFLICT/F_CFG_CONFLICT event-number mapping, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-conflict-diagnostic-payload-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 EVENTQ conflict diagnostic payload functional slice",
          "description": "Verification report records implementation-defined word3 Reason payload coverage for modeled F_TLB_CONFLICT/F_CFG_CONFLICT records."
        },
        {
          "path": "doc/verification/qbox-smmuv3-config-cache-conflict-recovery-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 configuration-cache conflict recovery functional slice",
          "description": "Verification report records modeled STE configuration-cache conflict detection/recovery, build, CTest, static/lane, and guest smoke evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-f-uut-event-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 F_UUT unsupported-upstream EVENTQ functional slice",
          "description": "Verification report records modeled F_UUT injection, event number, zero Reason, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-recinvsid-bad-streamid-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 C_BAD_STREAMID RECINVSID functional slice",
          "description": "Verification report records normal C_BAD_STREAMID no-event suppression until CR2.RECINVSID, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-config-event-res0-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 configuration-event RES0 payload functional slice",
          "description": "Verification report records C_BAD_STREAMID/C_BAD_STE/C_BAD_CD/F_STREAM_DISABLED non-stall payload RES0 evidence, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-config-disabled-no-event-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/050/060 STE.Config disabled no-event functional slice",
          "description": "Verification report records STE.Config==0 no-event and ATS UR/no-event evidence, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-event-record-fetch-reason-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 EVENTQ fetch-fault word1 functional slice",
          "description": "Verification report records non-stall fetch-fault Reason/GPCF word1 encoding, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-ste-fetch-priority-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated F_STE_FETCH priority functional slice",
          "description": "Verification report records F_STE_FETCH priority and REC_CFG_ATS-gated recording evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-vms-fetch-priority-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated F_VMS_FETCH priority functional slice",
          "description": "Verification report records actual modeled STE.VMSPtr fetch abort, F_VMS_FETCH EVENTQ record, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-vms-partid-map-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050 VMS PARTID_MAP fetch/cache-fill functional slice",
          "description": "Verification report records build, focused gTest/CTest, static checker, and lane evidence for full VMS PARTID_MAP fetch/cache fill."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-discovery-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 MPAM/VMS discovery functional slice",
          "description": "Verification report records the architectural discovery coherence required before the modeled VMS path is advertised."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-partid-remap-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 MPAM PARTID_MAP remap functional slice",
          "description": "Verification report records CD.PARTID virtual-to-physical PARTID remap, PMG preservation, and downstream TLM extension propagation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ste-mpam-attrs-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 STE-sourced MPAM functional slice",
          "description": "Verification report records STE.PARTID/PMG fallback assignment and downstream TLM extension propagation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-range-unknown-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 MPAM range-to-UNKNOWN functional slice",
          "description": "Verification report records MPAMIDR range checks and UNKNOWN downstream TLM attribute propagation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-gbpmpam-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 GBPMPAM global-bypass functional slice",
          "description": "Verification report records GBPMPAM Update programming and downstream TLM attribute propagation for global bypass."
        },
        {
          "path": "doc/verification/qbox-smmuv3-gbpa-global-bypass-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/030/080 GBPA global-bypass attribute/abort slice",
          "description": "Verification report records SMMU_GBPA output attributes for disabled-SMMU bypass and GBPA.ABORT no-event abort behavior."
        },
        {
          "path": "doc/verification/qbox-smmuv3-agbpa-res0-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/030/080 AGBPA unsupported-RES0 slice",
          "description": "Verification report records unsupported SMMU_AGBPA/SMMU_S_AGBPA RES0/WI behavior."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-gmpam-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 GMPAM originated-write functional slice",
          "description": "Verification report records GMPAM Update programming and downstream TLM attribute propagation for queue/MSI writes."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-gmpam-fetch-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 GMPAM originated-fetch functional slice",
          "description": "Verification report records GMPAM Update programming and downstream TLM attribute propagation for command-queue, STE, L1STD, and VMS fetches."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-ste-cd-fetch-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 STE-sourced CD fetch functional slice",
          "description": "Verification report records resolved STE MPAM propagation on L1CD/CD fetches."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-tt-fetch-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 client-derived TT fetch functional slice",
          "description": "Verification report records current client MPAM propagation on S1/S2 TT descriptor fetches."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-s1mpam-helper-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 S1MPAM nested helper MPAM functional slice",
          "description": "Verification report records build, CTest, focused gTest, static checker, and lane evidence for S1MPAM CD/helper-walk STE attributes before CD/VMS override."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-ats-translated-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050/060 ATS Translated MPAM functional slice",
          "description": "Verification report records build, CTest, focused gTest, static checker, and lane evidence for ATS Translated GBPMPAM, STE-sourced, and CD-sourced MPAM attributes."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-partid-space-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 MPAM PARTID-space functional slice",
          "description": "Verification report records build, focused gTest/CTest, static checker, and lane evidence for explicit Non-secure PARTID-space tagging."
        },
        {
          "path": "doc/verification/qbox-smmuv3-security-state-gate-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/050 security-state unsupported-gate functional slice",
          "description": "Verification report records build, focused gTest/CTest, static checker, and lane evidence for Secure/Realm/Root endpoint acceptance plus invalid security-state rejection."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-security-partid-space-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 MPAM security PARTID-space slice",
          "description": "Verification report records build, focused gTest/CTest, static checker, lane, and final closure evidence for security-state-derived MPAM PARTID-space tagging."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-mpam-register-bank-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050 Secure GBPMPAM/GMPAM register-bank attribute slice",
          "description": "Verification report records build, focused gTest/CTest, static checker, lane, and final closure evidence for Secure MPAM register-bank attribute selection."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ste-s2r-s2s-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/050 STE.S2R/S2S stage-2 record/stall policy",
          "description": "Verification report records suppressed, non-stall, and stalled stage-2 EVENTQ policy evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ste-s2s-stall-model-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/050 STE.S2S terminate-only STALL_MODEL validation",
          "description": "Verification report records build, focused gTest/CTest, static checker, lane, and closure evidence for terminate-only STALL_MODEL validation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-idr5-granule-oas-verification-2026-05-11.md",
          "pattern": "bounded granules and 48-bit OAS behavior",
          "description": "Report ties IDR5 discovery to the existing bounded walker/OAS functional slices."
        },
        {
          "path": "doc/verification/qbox-smmuv3-e0pd-ptwnnc-behavior-verification-2026-05-11.md",
          "pattern": "stage-1 translation fault",
          "description": "Verification report records the E0PD F_TRANSLATION/stage-1 fault behavior."
        },
        {
          "path": "build/verification/smmu-e0pd-ptwnnc-behavior-gtest-20260511.log",
          "pattern": "CD.E0PD translation fault",
          "description": "Focused gTest log proves the modeled CD.E0PD translation-fault path was exercised."
        }
      ]
    },
    {
      "id": "SMMU-COMP-060",
      "title": "ATS/PRI protocol matrix",
      "status": "functional-slice",
      "owner": "Apollo TBU",
      "claim_scope": "ATS success/UR/CA outcomes including STE.Config==0 UR without EVENTQ recording, PRG-tagged PRI pending records, CMD_PRI_RESP head-ordered exact-PRG/StreamID/PASID clear/reject/unknown plus SMMUEN-disabled no-op, PRIQ_CONS advancement, and reserved-code CERROR_ILL accounting, Secure CMDQ CMD_PRI_RESP Non-secure StreamID accounting, IDR0.ATS/PRI advertisement plus explicit unsupported-command guards, PRIQ OVFLG/OVACKFLG overflow acknowledgement, PRIQ_ABT_ERR queue-write abort reporting, automatic PRI success response for no-PASID Last PPR overflow, STE.PPAR-driven PASID-prefixed overflow response selection with REC_CFG_ATS/RECINVSID-gated lookup-fault recording, plus failure responses for Secure-stream, invalid STE.PPAR lookup, disabled, and abort-active cases, modeled PRI PPR SSV/Last/R/W/X/Priv metadata, PRI PRGIndex 9-bit allocation/encoding/head-ordered response matching plus PRIQ_CONS advancement, Stop PASID Marker no-response handling, non-last overflow discard without auto-response, and incoming PPR enqueue independence from CR0.ATSCHK/STE.EATS, CR0.ATSCHK plus STE.EATS ATS Translation Request gates including architected nested split-stage IPA walks, modeled ATS Translated rejection with F_TRANSL_FORBIDDEN plus address-size no-event abort behavior, stage-2-only and architected nested split-stage ATS Translated IPA walks plus implementation-defined rejection for unsupported non-stage2/non-nested split-stage traffic, STE.Config==0b100 F_TRANSL_FORBIDDEN aborts, DPT register RES0/WI policy plus DPT EATS unsupported F_TRANSL_FORBIDDEN aborts, PASIDTT-disabled SSV/PnU/InD clearing, and ATSCHK==0 configuration-lookup bypass with GBPMPAM Translated MPAM attributes, ATSCHK-enabled STE/CD-sourced Translated MPAM attributes, CR2.REC_CFG_ATS-gated ATS Translated configuration-fault recording, partial Translated event-priority validation including F_VMS_FETCH from a modeled STE.VMSPtr path, and CR2.REC_CFG_ATS/RECINVSID event-recording gates are component-tested and Linux-probed; full packet-level ATS/PRI protocol remains open. ECMDQ unsupported discovery is explicitly RES0/WI while packet-level ECMDQ protocol remains open. The slice now also covers bounded CD.E0PD unprivileged translation-fault behavior and nested stage-1 descriptor-fetch PTWNNC normalization for Device-mapped stage-2 memory.",
      "source_evidence": [
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_ATS_RESP_UR",
          "description": "TBU distinguishes ATS success, unsupported-request, and completer-abort outcomes."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_IDR0_ATS",
          "description": "Apollo TBU advertises IDR0.ATS for modeled CMD_ATC_INV and ATS protocol support."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_IDR0_PRI",
          "description": "Apollo TBU advertises IDR0.PRI for modeled PRIQ and CMD_PRI_RESP support."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedIdr0AdvertisesAtsPri",
          "description": "Component test verifies the SMMUv3 register surface exposes the modeled ATS/PRI feature bits."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "AtsConfigDisabledReturnsUrWithoutEvent",
          "description": "Component vector verifies STE.Config==0 ATS Translation Requests return UR without EVENTQ records."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "complete_prg",
          "description": "TBU tracks PRG-tagged pending PRI requests, consumes CMD_PRI_RESP clear/reject/unknown responses only when the command matches the head pending PRG, and advances PRIQ_CONS for the retired head record."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedAtsPriProtocolMatrixAndPriResp",
          "description": "Component test covers ATS success/UR/CA and PRI response clear/reject paths."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdPriRespUnknownPrgIsAccounted",
          "description": "Component test covers unknown PRG response accounting."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "FEATURE_ARCH_ATSCHK_EATS_GATES",
          "description": "TBU advertises CR0.ATSCHK plus STE.EATS gate coverage for ATS Translation Requests."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_CTRL_ATS_TRANSLATION_REQUEST",
          "description": "TBU exposes an ATS Translation Request probe path distinct from the legacy descriptor probe."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "AtsTranslationRequestHonorsCr0AtschkAndSteEats",
          "description": "Component test covers split-stage EATS with ATSCHK clear, EATS disabled, and Full ATS success."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-selftest.c",
          "pattern": "SMMUv3 ATSCHK/EATS translation request selftest ok",
          "description": "Linux probe validates the ATSCHK/EATS Translation Request gate at boot."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "FEATURE_ARCH_REC_CFG_ATS_GATES",
          "description": "TBU advertises CR2.REC_CFG_ATS/RECINVSID recording gate coverage for ATS Translation Requests."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "AtsTranslationRequestHonorsCr2RecCfgAtsAndRecInvsid",
          "description": "Component test covers REC_CFG_ATS suppression/recording and ATS bad-StreamID RECINVSID interaction."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-selftest.c",
          "pattern": "SMMUv3 REC_CFG_ATS translation request selftest ok",
          "description": "Linux probe validates REC_CFG_ATS-gated recording for SMMUEN-disabled ATS Translation Requests."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "write_arch_output_queue_cons",
          "description": "TBU decodes output queue consumer writes, including OVACKFLG acknowledgement."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "EventAndPriQueueOverflowFlagsToggleAndAck",
          "description": "Component test verifies PRIQ OVFLG toggles once per unacknowledged overflow and clears when software writes OVACKFLG."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_GERROR_PRIQ_ABORT",
          "description": "TBU exposes the architected PRIQ_ABT_ERR GERROR bit for PRI queue access aborts."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "EventAndPriQueueWriteAbortUseArchitectedGerrorBits",
          "description": "Component test verifies failed PRI queue record writes set PRIQ_ABT_ERR and are acknowledged through GERRORN."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "FEATURE_ARCH_PRI_AUTO_RESPONSE",
          "description": "TBU advertises automatic PRI response coverage for unavailable PRIQ cases."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "record_pri_auto_response",
          "description": "TBU records automatic PRI failure responses and clears the matching pending PRG."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "PriProtocolAutoRespondsOnOverflowDisabledAndAbort",
          "description": "Component test verifies automatic PRI success for no-PASID PRIQ overflow and failure responses for disabled PRIQ and active PRIQ_ABT_ERR."
        },
        {
          "path": "sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h",
          "pattern": "translated = false",
          "description": "TLM sideband can mark modeled ATS Translated endpoint transactions without changing default traffic."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_FAULT_TRANSL_FORBIDDEN",
          "description": "TBU has an explicit modeled fault reason for ATS Translated transactions forbidden by ATSCHK/EATS."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "allow_arch_translated_transaction",
          "description": "TBU checks modeled ATS Translated traffic against CR0.ATSCHK and effective STE.EATS before normal endpoint translation."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "AtsTranslatedTransactionForbiddenRecordsEvent",
          "description": "Component vector verifies forbidden translated traffic records F_TRANSL_FORBIDDEN and permitted EATS=FULL traffic continues."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "AtsTranslatedSteFetchRecordsBeforeSteDecode",
          "description": "ATS Translated protocol vector verifies configuration-fetch abort priority before EATS decisions."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_fetch_vms_if_enabled",
          "description": "TBU checks modeled STE.VMSPtr before allowing ATS Translated traffic to fall through to F_TRANSL_FORBIDDEN."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "AtsTranslatedVmsFetchRecordsBeforeForbidden",
          "description": "Component vector verifies ATS Translated F_VMS_FETCH priority and REC_CFG_ATS policy."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "preserve_mpam_state",
          "description": "TBU preserves the MPAM decision made by the ATS Translated gate while routing the downstream payload."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "AtsTranslatedAtschkDisabledUsesGbpmpamAttributes",
          "description": "Component test covers GBPMPAM attributes on ATSCHK-disabled ATS Translated traffic."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "AtsTranslatedSteMpamAttributesPropagateWhenAtschkEnabled",
          "description": "Component test covers STE-derived MPAM attributes on ATSCHK-enabled ATS Translated traffic."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "AtsTranslatedCdMpamAttributesPropagateWhenS1MpamEnabled",
          "description": "Component test covers CD-derived MPAM attributes on ATSCHK-enabled ATS Translated traffic when STE.S1MPAM is enabled."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_priq_ppr_is_stop_marker",
          "description": "Apollo TBU models PRI PPR metadata and Stop PASID Marker detection."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "PriProtocolPprFieldsStopMarkerAndNonLastDiscard",
          "description": "Component test covers PPR metadata, Stop Marker no-response behavior, and non-last overflow discard without auto-response."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_pri_overflow_auto_response",
          "description": "Apollo TBU selects Success for no-PASID Last PPR overflow and checks STE.PPAR for PASID-prefixed overflow responses."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ARCH_PRI_RESP_ACCEPT",
          "description": "Component test validates no-PASID overflow uses Response Success while disabled and abort-active cases remain failures."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_STE_PPAR",
          "description": "Apollo TBU models the STE.PPAR bit used for PASID-prefixed PRI overflow auto-response selection."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_last_auto_response_ssv",
          "description": "Apollo TBU records whether an automatic PRI response carries modeled PASID/SSID metadata."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_arch_core.h",
          "pattern": "last_pri_response_stream_id",
          "description": "Architected fault/replay state records the StreamID, response code, ATS status, head-PRG ordering state, and unknown diagnostic for the last modeled CMD_PRI_RESP completion."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_arch_core.h",
          "pattern": "last_pri_response_stream_mismatch",
          "description": "Architected fault/replay state records a modeled CMD_PRI_RESP StreamID qualifier mismatch and the command StreamID."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_arch_core.h",
          "pattern": "last_pri_response_ssid_mismatch",
          "description": "Architected fault/replay state records a modeled CMD_PRI_RESP PASID/SSID qualifier mismatch and the command SSID."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_arch_core.h",
          "pattern": "last_pri_response_order_mismatch",
          "description": "Architected fault/replay state records CMD_PRI_RESP attempts that target a later PRG before the head pending PRG."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_arch_core.h",
          "pattern": "last_pri_response_head_prg",
          "description": "Architected fault/replay state preserves the head PRGIndex diagnostic when a CMD_PRI_RESP cannot retire the current head."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_pri_response_valid",
          "description": "Apollo TBU rejects modeled CMD_PRI_RESP response codes outside Success, Invalid Request, and Response Failure."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "PriProtocolOverflowUsesStePparForPasidAutoResponse",
          "description": "Component test covers STE.PPAR set, STE.PPAR clear, and invalid STE lookup outcomes for PASID-prefixed overflow auto-responses."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdPriRespRequiresHeadPrgOrdering",
          "description": "Component test proves CMD_PRI_RESP cannot retire a later PRG before the head pending PRG and preserves response diagnostics."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "advance_priq_cons_after_response",
          "description": "Apollo TBU advances the modeled PRIQ consumer index after a successful head PRG response retirement."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdPriRespAdvancesPriqConsForHeadRequest",
          "description": "Component test proves a successful head CMD_PRI_RESP advances SMMU_PRIQ_CONS and clears the PRIQ IRQ when the queue becomes empty."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdPriRespIgnoredWhenSmmuenDisabled",
          "description": "Component test proves CMD_PRI_RESP is silently ignored while SMMUEN is clear, leaving the pending PRG, PRIQ_CONS, and CERROR state unchanged."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdPriRespHonorsStreamIdQualifier",
          "description": "Component test covers modeled CMD_PRI_RESP StreamID qualifier mismatch and subsequent correct StreamID completion."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdPriRespHonorsSsidQualifier",
          "description": "Component test covers modeled CMD_PRI_RESP PASID/SSID qualifier mismatch and subsequent correct PASID/SSID completion."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdPriRespReservedResponseSetsCerrorIll",
          "description": "Component test covers reserved CMD_PRI_RESP response-code rejection with CMDQ_CONS.CERROR_ILL and pending PRG preservation."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureCmdPriRespReservedResponseSetsCerrorIll",
          "description": "Component test covers reserved Secure CMD_PRI_RESP response-code rejection with S_CMDQ_CONS.CERROR_ILL and pending PRG preservation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "secure_cmdq_command_security_state",
          "description": "Apollo TBU treats accepted Secure CMDQ CMD_PRI_RESP commands as targeting Non-secure StreamIDs and ignores the RES0 SSec bit for PRI responses."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureCmdPriRespIgnoresSsecAndTargetsNonSecure",
          "description": "Component test proves Secure CMD_PRI_RESP with bit[10] set consumes a Non-secure pending PRG without S_CMDQ CERROR."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "last_pri_response_unknown",
          "description": "Component test asserts unknown-PRG CMD_PRI_RESP diagnostic metadata while preserving the command response code."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_pri_secure_stream_auto_failure",
          "description": "Apollo TBU models the PRI miscellaneous rule that protocol PPRs from Secure streams receive Response Failure."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "PriProtocolSecureStreamAutoFailsWithoutQueueing",
          "description": "Component test covers Secure-stream PPR auto-failure and verifies no Secure PRIQ entry is queued."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "record_pri_ppar_lookup_fault",
          "description": "Apollo TBU applies REC_CFG_ATS/RECINVSID event-recording gates for STE.PPAR lookup failures during PRI overflow auto-response selection."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "PriProtocolPparLookupFaultHonorsRecCfgAts",
          "description": "Component test covers C_BAD_STE STE.PPAR lookup failure recording with REC_CFG_ATS set and suppression when clear."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "PriProtocolPparBadStreamIdHonorsRecInvsid",
          "description": "Component test covers C_BAD_STREAMID STE.PPAR lookup failure suppression until both CR2.REC_CFG_ATS and CR2.RECINVSID are set."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "Incoming PRI Page Request messages are a PRI-side protocol input",
          "description": "Apollo TBU documents that incoming PRI PPR enqueue is independent of CR0.ATSCHK and STE.EATS, with STE.PPAR consulted only for overflow auto-response."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "PriProtocolPprIgnoresAtschkAndSteEats",
          "description": "Component test proves PPR enqueue works with ATSCHK clear and with STE.EATS disabled while avoiding STE.PPAR auto-response lookup."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_PRIQ_PPR_PRG_MASK = 0x1ff",
          "description": "Apollo TBU defines and uses the architected 9-bit PRI PRGIndex mask for modeled PPR encoding and response matching."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "PriProtocolPrgIndexIsNineBitsAndWraps",
          "description": "Component test proves nonzero 9-bit PRGIndex wrapping and masked head-ordered CMD_PRI_RESP matching."
        }
      ],
      "runtime_evidence": [
        {
          "path": "doc/verification/qbox-smmuv3-idr0-ats-pri-advertisement-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/060 IDR0 ATS/PRI advertisement slice",
          "description": "Verification report records IDR0 ATS/PRI advertisement and command feature-gate evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-comp-060-verification-2026-05-10.md",
          "pattern": "ArchitectedAtsPriProtocolMatrixAndPriResp",
          "description": "Verification report records the SMMU-COMP-060 component and platform validation evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-queue-ovflg-verification-2026-05-10.md",
          "pattern": "PRIQ overflow toggles SMMU_PRIQ_PROD.OVFLG",
          "description": "Follow-up report records PRIQ overflow flag validation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-queue-abort-gerror-verification-2026-05-10.md",
          "pattern": "PRIQ_ABT_ERR",
          "description": "Follow-up report records PRI queue abort GERROR validation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-pri-auto-response-verification-2026-05-10.md",
          "pattern": "PRI auto-response",
          "description": "Follow-up report records PRIQ overflow, disabled, and abort-active automatic response validation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-forbidden-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated F_TRANSL_FORBIDDEN functional slice",
          "description": "Verification report records ATS Translated sideband rejection, F_TRANSL_FORBIDDEN event evidence, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-rec-cfg-ats-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated REC_CFG_ATS functional slice",
          "description": "Verification report records ATS Translated configuration-fault suppression until CR2.REC_CFG_ATS, C_BAD_STE/C_BAD_STREAMID recording, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-smmuen-atschk-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated SMMUEN/ATSCHK functional slice",
          "description": "Verification report records SMMUEN-disabled F_TRANSL_FORBIDDEN and ATSCHK==0 configuration-lookup bypass evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-address-size-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated address-size functional slice",
          "description": "Verification report records the spec-permitted no-event abort behavior for Translated addresses above the modeled PA size."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-split-stage-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated split-stage unsupported functional slice",
          "description": "Verification report records implementation-defined F_TRANSL_FORBIDDEN for EATS_SPLIT Translated traffic on QBox's unsupported split-stage IPA protocol."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-split-stage-s2-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated split-stage stage-2-only slice",
          "description": "Verification report records EATS_SPLIT ATS Translated IPA validation through the modeled stage-2-only compatibility walker while non-stage2/non-nested split-stage remains rejected."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-split-stage-nested-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 architected nested ATS Translated split-stage IPA walk slice",
          "description": "Verification report records EATS_SPLIT ATS Translated IPA validation through the architected Nested STE stage-2-only walker."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-treq-split-stage-nested-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-060 architected nested ATS Translation Request split-stage IPA walk slice",
          "description": "Verification report records EATS_SPLIT ATS Translation Request IPA validation through the architected Nested STE stage-2-only walker."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-config-abort-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated STE.Config abort functional slice",
          "description": "Verification report records F_TRANSL_FORBIDDEN for ATS Translated traffic targeting STE.Config==0b100."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-dpt-unsupported-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated DPT unsupported functional slice",
          "description": "Verification report records F_TRANSL_FORBIDDEN for EATS_DPT Translated traffic while QBox lacks a DPT model."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-pasidtt-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated PASIDTT disabled functional slice",
          "description": "Verification report records SSV/PnU/InD clearing for ATS Translated traffic while SMMU_IDR3.PASIDTT is 0."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-priority-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated priority functional slice",
          "description": "Verification report records partial ATS Translated priority evidence for configuration faults before F_TRANSL_FORBIDDEN."
        },
        {
          "path": "doc/verification/qbox-smmuv3-config-disabled-no-event-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/050/060 STE.Config disabled no-event functional slice",
          "description": "Verification report records STE.Config==0 ATS UR/no-event evidence, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-ste-fetch-priority-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated F_STE_FETCH priority functional slice",
          "description": "Verification report records F_STE_FETCH priority and REC_CFG_ATS-gated recording evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-vms-fetch-priority-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-050/060 ATS Translated F_VMS_FETCH priority functional slice",
          "description": "Verification report records actual modeled STE.VMSPtr fetch abort, F_VMS_FETCH EVENTQ record, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-mpam-ats-translated-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/050/060 ATS Translated MPAM functional slice",
          "description": "Verification report records build, CTest, focused gTest, static checker, and lane evidence for ATS Translated GBPMPAM, STE-sourced, and CD-sourced MPAM attributes."
        },
        {
          "path": "doc/verification/qbox-smmuv3-pri-ppr-stop-marker-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-060 PRI PPR/Stop Marker slice",
          "description": "Verification report records ground truth, scope, planned build, gTest, CTest, static, and lane evidence for PRI PPR/Stop Marker handling."
        },
        {
          "path": "doc/verification/qbox-smmuv3-pri-overflow-auto-response-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-060 PRI overflow auto-response slice",
          "description": "Verification report records ground truth, scope, planned build, gTest, CTest, static, and lane evidence for no-PASID overflow auto-response behavior."
        },
        {
          "path": "doc/verification/qbox-smmuv3-pri-response-head-order-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-060 PRI response head-ordered exact-PRG slice",
          "description": "Verification report records head-ordered exact-PRG CMD_PRI_RESP handling, PRIQ_CONS advancement, later-PRG preservation, response metadata, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-pri-response-smmuen-disabled-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-060 PRI response SMMUEN-disabled no-op slice",
          "description": "Verification report records CMD_PRI_RESP no-op behavior with SMMUEN clear, pending PRG preservation, PRIQ_CONS preservation, build, CTest, static checker, and lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-pri-response-streamid-qualifier-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-060 PRI response StreamID qualifier slice",
          "description": "Verification report records StreamID-qualified CMD_PRI_RESP matching, mismatch diagnostics, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-pri-response-ssid-qualifier-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-060 PRI response SSID qualifier slice",
          "description": "Verification report records PASID/SSID-qualified CMD_PRI_RESP matching, mismatch diagnostics, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-pri-response-reserved-code-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-060 PRI response reserved-code slice",
          "description": "Verification report records reserved CMD_PRI_RESP response-code rejection, CERROR_ILL reporting, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-pri-response-reserved-code-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-060 Secure PRI response reserved-code slice",
          "description": "Verification report records Secure CMD_PRI_RESP reserved response-code rejection, S_CMDQ_CONS.CERROR_ILL reporting, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-pri-response-nonsecure-stream-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-060 Secure CMD_PRI_RESP Non-secure StreamID slice",
          "description": "Verification report records Secure CMD_PRI_RESP Non-secure StreamID treatment, focused gTest, CTest, static checker, and lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-pri-response-unknown-prg-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-060 PRI response unknown-PRG diagnostic slice",
          "description": "Verification report records unknown-PRG CMD_PRI_RESP diagnostic metadata, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-pri-ppar-auto-response-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-060 PRI STE.PPAR auto-response",
          "description": "Verification report records ground truth, scope, planned build, gTest, CTest, static, and lane evidence for STE.PPAR-driven PASID-prefixed PRI overflow auto-responses."
        },
        {
          "path": "doc/verification/qbox-smmuv3-pri-secure-stream-auto-failure-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-060 PRI Secure-stream auto-failure",
          "description": "Verification report records ground truth, scope, planned build, gTest, CTest, static, and lane evidence for Secure-stream PRI auto-failure."
        },
        {
          "path": "doc/verification/qbox-smmuv3-pri-ppar-lookup-event-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-060 PRI STE.PPAR lookup event-recording",
          "description": "Verification report records ground truth, scope, planned build, gTest, CTest, static, and lane evidence for STE.PPAR lookup event-recording gates."
        },
        {
          "path": "doc/verification/qbox-smmuv3-pri-ppar-bad-streamid-recinvsid-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-060 PRI STE.PPAR bad StreamID RECINVSID slice",
          "description": "Verification report records C_BAD_STREAMID STE.PPAR lookup suppression until REC_CFG_ATS plus RECINVSID, build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-pri-ppr-atschk-eats-independence-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-060 PRI PPR ATSCHK/EATS independence slice",
          "description": "Verification report records build, targeted gTest, CTest, static checker, lane, and closure evidence for PPR ATSCHK/EATS independence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-pri-prg-index-nine-bit-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-060 PRI PRGIndex 9-bit slice",
          "description": "Verification report records build, targeted gTest, CTest, static checker, lane, and closure evidence for PRGIndex 9-bit behavior."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ecmdq-register-res0-verification-2026-05-11.md",
          "pattern": "Full ECMDQ support would require",
          "description": "Report documents that ECMDQ protocol semantics remain open while unsupported discovery is RES0/WI."
        },
        {
          "path": "doc/verification/qbox-smmuv3-e0pd-ptwnnc-behavior-verification-2026-05-11.md",
          "pattern": "Device-mapped stage-2 descriptors",
          "description": "Verification report records the PTWNNC normalization behavior associated with the advertised SMMUv3.3 surface."
        },
        {
          "path": "build/verification/smmu-e0pd-ptwnnc-behavior-gtest-20260511.log",
          "pattern": "PTWNNC normalizes",
          "description": "Focused gTest log proves nested stage-1 descriptor fetch PTWNNC normalization was exercised."
        }
      ]
    },
    {
      "id": "SMMU-COMP-070",
      "title": "Architected IRQ/MSI and visibility ordering",
      "status": "functional-slice",
      "owner": "QBox platform + Apollo TBU + Linux probe",
      "claim_scope": "Signal-level Apollo TBU interrupt outputs are modeled and component-tested for EVENTQ, PRIQ, CMDQ_SYNC, and GERROR, unsupported IRQ_CTRL bits are masked in IRQ_CTRL/IRQ_CTRLACK, raw GERROR exposure plus GERROR/GERRORN active-bit toggle acknowledgement is component-tested, output queue write aborts use architected EVENTQ_ABT_ERR/PRIQ_ABT_ERR bits, MSI IRQ_CFG registers, CMD_SYNC MSI writes, MSI abort GERROR bits, Secure CMD_SYNC wired visibility through S_IRQ_CTRL/S_IRQ_CTRLACK, Secure EVENTQ MSI routing through S_EVENTQ_IRQ_CFG/S_GERROR, Secure PRIQ MSI routing through S_PRIQ_IRQ_CFG/S_GERROR.MSI_PRIQ_ABORT, and Secure GERROR MSI routing through S_GERROR_IRQ_CFG/S_GERROR.MSI_GERROR_ABORT are component-tested; Apollo Hexagon DMA async fence IRQ status now drives Linux-visible doorbell signals until software ACK, and the Linux Apollo Hexagon probe binds the doorbell IRQ and waits on interrupt-driven fence completion before polling fallback. Full GIC/MSI ordering and upstream arm-smmu-v3 interrupt handling are not complete.",
      "source_evidence": [
        {
          "path": "sources/qbox/qemu-components/arm_smmuv3/include/arm-smmuv3.h",
          "pattern": "irq_out",
          "description": "QEMU wrapper exposes four IRQ outputs."
        },
        {
          "path": "doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md",
          "pattern": "Apollo TBU has no IRQ outputs",
          "description": "Gap matrix records Apollo TBU IRQ/MSI work as missing."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "sc_core::sc_vector<InitiatorSignalSocket<bool>> irq_out",
          "description": "Apollo TBU exposes four signal-level IRQ outputs for EVENTQ, PRIQ, CMDQ_SYNC, and GERROR."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "update_irq_outputs",
          "description": "Apollo TBU gates and updates IRQ outputs from architected status and IRQ_CTRL bits."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_IRQ_CTRL_WRITABLE_MASK",
          "description": "Apollo TBU masks unsupported IRQ_CTRL bits before updating IRQ_CTRLACK."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "read_arch_gerror_raw",
          "description": "Apollo TBU exposes raw GERROR toggle state through the architected GERROR register."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-selftest.c",
          "pattern": "apollo_smmuv3_gerror_active",
          "description": "Linux probe computes active global errors as GERROR xor GERRORN while reading the raw GERROR register."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "read_arch_gerror",
          "description": "Apollo TBU computes active global errors from raw GERROR/GERRORN toggle state."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ack_arch_gerror",
          "description": "Apollo TBU acknowledges GERRORN writes only for currently-active global error bits."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "ArchitectedIrqOutputsFollowQueueStatus",
          "description": "Component test verifies IRQ line assertion and deassertion for EVENTQ, PRIQ, CMDQ_SYNC, and GERROR."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "IrqCtrlReservedBitsAreMaskedInCtrlAck",
          "description": "Component test verifies unsupported IRQ_CTRL bits are masked in IRQ_CTRL and IRQ_CTRLACK."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "GerrorRegisterExposesRawToggleStateAndGerrornAcknowledgesActiveBits",
          "description": "Component test verifies active-only GERRORN acknowledgement and repeated error retoggle behavior."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "EventAndPriQueueWriteAbortUseArchitectedGerrorBits",
          "description": "Component test verifies output queue write abort GERROR active bits and acknowledgements."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "FEATURE_ARCH_IRQ_MSI_CFG",
          "description": "Apollo TBU advertises the MSI IRQ_CFG and MSI abort functional slice."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_GERROR_MSI_CMDQ_ABORT",
          "description": "Apollo TBU models architected MSI_CMDQ/EVENTQ/PRIQ/GERROR abort bits in GERROR."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "MsiIrqCfgRegistersAreMaskedAndGuarded",
          "description": "Component test verifies MSI IRQ_CFG masks and IRQ_CTRL guard behavior."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdSyncMsiWriteAndAbortAreReported",
          "description": "Component test verifies CMD_SYNC SIG_IRQ MSI writes and MSI_CMDQ_ABT_ERR reporting."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureEventqMsiAndAbortUseSecureBank",
          "description": "Component test verifies Secure EVENTQ MSI routing through S_EVENTQ_IRQ_CFG and S_GERROR.MSI_EVENTQ_ABORT on failed MSI writes."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecurePriqMsiAndAbortUseSecureBank",
          "description": "Component test verifies Secure PRIQ MSI routing through S_PRIQ_IRQ_CFG and S_GERROR.MSI_PRIQ_ABORT on failed MSI writes."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureGerrorMsiAndAbortUseSecureBank",
          "description": "Component test verifies Secure GERROR MSI routing through S_GERROR_IRQ_CFG and S_GERROR.MSI_GERROR_ABORT on failed MSI writes."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h",
          "pattern": "InitiatorSignalSocket<bool> irq_out",
          "description": "Apollo Hexagon DMA exposes a signal-level async fence IRQ output."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h",
          "pattern": "update_irq_output",
          "description": "Apollo Hexagon DMA asserts its IRQ output while any queue IRQ status bit is pending and deasserts after acknowledgement."
        },
        {
          "path": "sources/qbox/platforms/buildroot/conf_aarch64.lua",
          "pattern": "irq_out = {bind = \"&gic_0.spi_in_564\"}",
          "description": "QBox platform binds the primary Apollo Hexagon DMA doorbell IRQ to the Linux-visible DTS doorbell interrupt."
        },
        {
          "path": "sources/qbox/tests/components/apollo_hexagon_dma/apollo-hexagon-dma-tests.cc",
          "pattern": "AsyncFenceDrivesIrqSignalUntilAck",
          "description": "Component test verifies multi-queue async fence IRQ signal assertion, retention while another queue is pending, and deassertion after ACK."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon.c",
          "pattern": "platform_get_irq_byname_optional",
          "description": "Linux probe resolves the named doorbell interrupt from the Apollo Hexagon DTS binding."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon.c",
          "pattern": "devm_request_irq",
          "description": "Linux probe registers an interrupt handler for the Apollo Hexagon doorbell IRQ."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon.c",
          "pattern": "async_irq_pending",
          "description": "Linux IRQ handler caches pending queue bits before acknowledging the level doorbell interrupt."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon.c",
          "pattern": "wait_for_completion_timeout",
          "description": "Linux submit path waits for interrupt-driven async fence completion before using the existing polling fallback."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon.c",
          "pattern": "async fence irq wait",
          "description": "Linux logs make the interrupt-driven async fence wait path visible in guest-runtime evidence."
        }
      ],
      "runtime_evidence": [
        {
          "path": "build/verification/apollo-smmu-tbu-irq-output-test-20260510.log",
          "pattern": "100% tests passed",
          "description": "CTest verifies the signal-level Apollo TBU IRQ functional slice."
        },
        {
          "path": "build/verification/qbox-platform-smmu-comp-070-irq-output-20260510.log",
          "pattern": "QBox Buildroot platform runtime built",
          "description": "Full QBox Buildroot platform runtime rebuild passed with the IRQ output slice."
        },
        {
          "path": "build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-070-irq-output.driver.log",
          "pattern": "PASS: QBox guest IREE Hexagon tiny-CNN output matched",
          "description": "Guest IREE smoke passed while runtime logs exposed architected IRQ update markers."
        },
        {
          "path": "doc/verification/qbox-smmuv3-irq-ctrl-mask-verification-2026-05-10.md",
          "pattern": "SMMU-COMP-070 IRQ_CTRL reserved-bit mask functional slice",
          "description": "Verification report records IRQ_CTRL writable-mask build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-gerrorn-toggle-verification-2026-05-10.md",
          "pattern": "SMMU-COMP-070 GERROR/GERRORN active-bit toggle functional slice",
          "description": "Verification report records GERROR/GERRORN active-bit toggle build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-gerror-raw-toggle-verification-2026-05-10.md",
          "pattern": "SMMU-COMP-070 raw GERROR toggle register functional slice",
          "description": "Verification report records raw GERROR/GERRORN build, Linux, platform, guest smoke, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-queue-abort-gerror-verification-2026-05-10.md",
          "pattern": "SMMU-COMP-020/050/060/070 EVENTQ/PRIQ queue abort GERROR functional slice",
          "description": "Verification report records queue-abort GERROR build, CTest, and static/lane evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-irq-msi-cfg-verification-2026-05-10.md",
          "pattern": "SMMU-COMP-070 MSI IRQ_CFG functional slice",
          "description": "Verification report records MSI IRQ_CFG/CMD_SYNC MSI and MSI abort validation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-cmd-sync-irq-bank-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-070 Secure CMD_SYNC IRQ bank route functional slice",
          "description": "Verification report records build, component test, static checker, lane, and guest smoke evidence for Secure CMD_SYNC S_IRQ_CTRL/S_IRQ_CTRLACK visibility."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-eventq-msi-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-070 Secure EVENTQ MSI bank route functional slice",
          "description": "Verification report records build, component test, static checker, lane, and guest smoke evidence for Secure EVENTQ MSI bank routing and Secure GERROR abort reporting."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-priq-msi-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-070 Secure PRIQ MSI bank route functional slice",
          "description": "Verification report records build, component test, static checker, lane, and guest smoke evidence for Secure PRIQ MSI bank routing and Secure GERROR abort reporting."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-gerror-msi-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-070 Secure GERROR MSI bank route functional slice",
          "description": "Verification report records build, component test, static checker, lane, and guest smoke evidence for Secure GERROR MSI bank routing and Secure GERROR abort reporting."
        },
        {
          "path": "doc/verification/qbox-smmuv3-dma-async-irq-signal-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-070 DMA async IRQ signal functional slice",
          "description": "Verification report records build, focused gTest/CTest, static checker, and lane evidence for DMA async fence IRQ signal delivery."
        },
        {
          "path": "doc/verification/qbox-smmuv3-linux-dma-irq-wait-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-070 Linux DMA async IRQ wait functional slice",
          "description": "Verification report records Linux Image rebuild and static/lane evidence for the doorbell IRQ handler and completion wait path."
        },
        {
          "path": "build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-linux-dma-irq-wait.driver.log",
          "pattern": "PASS: QBox guest IREE Hexagon tiny-CNN output matched",
          "description": "Guest smoke passed with the Linux DMA IRQ wait runtime contract enabled."
        },
        {
          "path": "build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-linux-dma-irq-wait.log",
          "pattern": "async fence irq wait signaled queue=1",
          "description": "Guest UART log proves the Apollo Hexagon CNN queue completed through the interrupt-driven async fence wait path."
        }
      ]
    },
    {
      "id": "SMMU-COMP-080",
      "title": "Multi-master and multi-StreamID isolation",
      "status": "functional-slice",
      "owner": "QBox Apollo TBU + DMA",
      "claim_scope": "TLM transactions carry StreamID plus endpoint PASID/SSID metadata and modeled STE output attributes for context-bypass, STE.Config all-bypass, stage-1/stage-2/nested translation, ATS Translated payload paths, the bounded GATOS_PAR return path, the architected non-secure SMMU_GATOS register group RUN/PAR/no-event ATOS path, the Secure SMMU_S_GATOS RUN/PAR/no-event ATOS path with S_GATOS_SID.SSEC Secure-vs-Non-secure stream selection, bounded ATOS_ADDR.TYPE stage-selection on SMMU_GATOS, ATOS_ADDR.PnU/InD access-field decode with STE output-override suppression on architected ATOS_PAR success, a non-advertised internal VATOS/S_VATOS stage-1-only model with GATOS/VATOS PAR isolation and VMID-scoped VATOS rejection, and Apollo TBU dynamic maps/ATS cache entries are isolated per SID and tagged per endpoint SSID, CMDQ invalidation can clear ATS cache entries by SID/page/global plus ASID/VMID/SSID-tagged scope in component tests, the Linux guest probe drives ATC_INV/TLBI_NH_ALL through the SMMUv3 CMDQ model, and QBox platform/DTS expose a second Linux-visible StreamID 0x2 DMA master. Full PCIe/RID multi-master topology remains open.",
      "source_evidence": [
        {
          "path": "sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h",
          "pattern": "class ApolloSmmuStreamIdExtension",
          "description": "Common TLM extension carries a DMA master StreamID with translated transactions."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h",
          "pattern": "trans\\.set_extension\\(&stream_id_ext\\)",
          "description": "Apollo Hexagon DMA attaches its configured StreamID to SMMU-translated TLM transactions."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "FEATURE_MULTI_STREAM_ID",
          "description": "Apollo TBU advertises the multi-StreamID functional slice."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "map.stream_id != stream_id",
          "description": "Dynamic map lookup is filtered by transaction StreamID."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "clear_ats_cache\\(uint32_t stream_id\\)",
          "description": "ATS cache invalidation can target only the selected StreamID."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "MultiStreamIdMapsAreIsolated",
          "description": "Component test verifies same-IOVA independent SID mappings, unknown-SID denial, and per-SID invalidation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "clear_ats_cache_page\\(uint32_t stream_id, uint64_t page\\)",
          "description": "ATS cache invalidation can target a selected StreamID and IOVA page."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdqInvalidationCommandsClearAtsBySidPageAndGlobal",
          "description": "Component test verifies command-driven invalidation preserves or clears SID-scoped ATS entries as expected."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "clear_ats_cache_page_ssid",
          "description": "ATC_INV can target a selected StreamID, IOVA page, and optional SSID tag."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "CmdqTaggedInvalidationHonorsAsidVmidAndSsid",
          "description": "Component test verifies tagged invalidation preserves unrelated ASID/VMID/SSID entries."
        },
        {
          "path": "sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h",
          "pattern": "substream_id_valid",
          "description": "Common TLM extension carries endpoint SubstreamID/PASID metadata alongside StreamID."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h",
          "pattern": "CAP_ENDPOINT_PASID",
          "description": "Apollo Hexagon DMA advertises endpoint PASID capability and attaches PASID/SSID metadata to translated TLM transactions."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "FEATURE_ENDPOINT_SUBSTREAM_ID",
          "description": "Apollo TBU advertises endpoint SubstreamID propagation and consumes it for ATS/event tagging."
        },
        {
          "path": "sources/qbox/platforms/buildroot/conf_aarch64.lua",
          "pattern": "substream_id = 0x3",
          "description": "QBox Buildroot platform configures a non-zero endpoint PASID/SSID on the Hexagon DMA endpoint."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "EndpointSubstreamIdTagsAtsAndFaultEvents",
          "description": "Component test verifies endpoint SSID tags ATS entries and EVENTQ records."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-selftest.c",
          "pattern": "APOLLO_SMMUV3_ARCH_CMD_ATC_INV",
          "description": "Linux probe stages a guest-visible ATC_INV command for the Hexagon StreamID."
        },
        {
          "path": "sources/qbox/platforms/buildroot/conf_aarch64.lua",
          "pattern": "APOLLO_HEXAGON_AUX_STREAM_ID = 0x2",
          "description": "QBox platform declares the auxiliary DMA master StreamID."
        },
        {
          "path": "sources/qbox/platforms/buildroot/conf_aarch64.lua",
          "pattern": "hexagon_dma_1",
          "description": "QBox platform instantiates the auxiliary DMA master."
        },
        {
          "path": "sources/qbox/platforms/buildroot/conf_aarch64.lua",
          "pattern": "hexagon_smmu_tbu_1",
          "description": "QBox platform instantiates a matching auxiliary TBU for the second master."
        },
        {
          "path": "configs/linux/apollo_soc.dts",
          "pattern": "hexagon-aux@1c300000",
          "description": "Linux DTS exposes a second Apollo Hexagon DMA endpoint."
        },
        {
          "path": "configs/linux/apollo_soc.dts",
          "pattern": "iommus = <&smmu 0x2>",
          "description": "Auxiliary endpoint is behind the SMMUv3 with StreamID 0x2."
        },
        {
          "path": "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon.c",
          "pattern": "/dev/accel/accel\\*",
          "description": "Linux probe registers Hexagon endpoints through DRM accel device minors."
        },
        {
          "path": "scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh",
          "pattern": "/dev/accel/accel\\* stream-id=0x2",
          "description": "Guest smoke requires the auxiliary StreamID 0x2 DRM accel probe marker."
        },
        {
          "path": "sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h",
          "pattern": "output_attrs_valid",
          "description": "Common TLM extension carries modeled STE bypass output attributes with downstream StreamID-tagged transactions."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SteBypassOutputAttributesPropagateOnContextBypass",
          "description": "Component test observes modeled STE bypass output attributes on a downstream transaction using the SMMU StreamID extension."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_STE_CFG_BYPASS",
          "description": "Apollo TBU names and accepts the modeled STE.Config all-bypass encoding while preserving existing ATS Translated rejection behavior through the compatibility alias."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "architectural STE.Config all-bypass",
          "description": "Apollo TBU returns identity translation for the modeled STE.Config all-bypass path and applies STE output attributes before downstream transport."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SteConfigBypassOutputAttributesPropagate",
          "description": "Component test verifies STE.Config all-bypass identity access plus MTCFG/MemAttr, shareability, allocation, instruction, privilege, and NS output-attribute propagation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ats-translated",
          "description": "Apollo TBU records modeled STE output attributes on successful ATS Translated configuration checks and preserves them across translated payload routing."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "AtsTranslatedSteOutputAttributesPropagateWhenAtschkEnabled",
          "description": "Component test verifies MTCFG/MemAttr, shareability, allocation, instruction, privilege, and NS output attributes on the ATS Translated downstream TLM payload."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_CTRL_GATOS_TRANSLATE",
          "description": "Apollo TBU exposes a modeled compatibility-register command for bounded GATOS_PAR translation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "REG_ARCH_PAR_LO",
          "description": "Apollo TBU exposes a 64-bit GATOS_PAR return register through REG_ARCH_PAR_LO/HI."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_gatos_success_par",
          "description": "Apollo TBU encodes translated PA plus modeled STE ATTR/SH output attributes in successful GATOS_PAR values."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "GatosParReportsSteOutputAttributes",
          "description": "Component test verifies GATOS_PAR ATTR/SH fields from modeled STE output attributes."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "GatosParFaultCodeForUnmappedPage",
          "description": "Component test verifies GATOS_PAR fault bit, FAULTCODE, and REASON for an unmapped translation."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "SMMUV3_GATOS_CTRL",
          "description": "Apollo TBU exposes the architected non-secure SMMU_GATOS_CTRL register at PAGE_0 offset 0x100."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "SMMUV3_GATOS_PAR_LO",
          "description": "Apollo TBU exposes the architected non-secure SMMU_GATOS_PAR readback register at PAGE_0 offset 0x118."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "run_arch_gatos_register_translate",
          "description": "RUN writes on SMMU_GATOS_CTRL execute the modeled ATOS translation, write PAR, clear RUN, and suppress EVENTQ/PRI side effects for ATOS faults."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "Smmuv3GatosRegistersRunAndClear",
          "description": "Component test verifies SMMU_GATOS_SID/ADDR input, RUN clear-on-completion, successful PAR PA bits, and readable SID/ADDR state."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "Smmuv3GatosFaultDoesNotRecordEvent",
          "description": "Component test verifies SMMU_GATOS fault PAR encoding without EVENTQ producer movement or fault-count side effects."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_secure_gatos_par",
          "description": "Apollo TBU stores an independent Secure SMMU_S_GATOS PAR value."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_smmu_enabled_for_security_state",
          "description": "Secure GATOS translation is gated by Secure CR0.SMMUEN instead of the Non-secure CR0 bank."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "architectural SMMU_S_GATOS register translation",
          "description": "Secure RUN writes execute through the Secure GATOS register path and log SMMU_S_GATOS completion."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureSmmuv3GatosRegistersUseSecureBank",
          "description": "Component test verifies Secure GATOS uses the Secure STRTAB bank and returns the Secure PA in PAR."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureSmmuv3GatosFaultDoesNotRecordEvent",
          "description": "Component test verifies Secure GATOS fault PAR encoding without Non-secure or Secure EVENTQ producer movement."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_ATOS_ADDR_TYPE_STAGE1_STAGE2",
          "description": "Apollo TBU decodes architected ATOS_ADDR.TYPE values for stage-1, stage-2, and stage-1+stage-2 GATOS requests."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "arch_atos_validate_ste_config",
          "description": "Apollo TBU rejects reserved ATOS_ADDR.TYPE values with INV_REQ and unsupported stage requests with INV_STAGE before returning PAR."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "atos-stage2-translation",
          "description": "Apollo TBU can perform a bounded stage-2-only ATOS walk for nested streams when ATOS_ADDR.TYPE requests stage 2."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "Smmuv3GatosAddrTypeReservedAndInvStage",
          "description": "Component test verifies reserved ATOS_ADDR.TYPE returns INV_REQ, stage-2 on a stage-1-only stream returns INV_STAGE, and stage-1 succeeds."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "Smmuv3GatosAddrTypeNestedStageSelection",
          "description": "Component test verifies nested stream ATOS stage-1-only, stage-1+stage-2, and stage-2-only selection through SMMU_GATOS_PAR."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "ARCH_ATOS_SID_SECURE_STREAM",
          "description": "Apollo TBU models SMMU_S_GATOS_SID.SSEC bit 53 for Secure versus Non-secure stream lookup selection."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "SecureSmmuv3GatosSsecSelectsNonsecureStream",
          "description": "Component test verifies Secure ATOS SSEC-clear Non-secure stream lookup, including the Secure-CR0 gate and Non-secure STRTAB selection."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_last_atos_privileged",
          "description": "Apollo TBU records ATOS_ADDR.PnU from architected GATOS requests."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "m_arch_last_atos_instruction",
          "description": "Apollo TBU records ATOS_ADDR.InD from architected GATOS requests."
        },
        {
          "path": "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h",
          "pattern": "STE output attributes ignored for ATOS",
          "description": "Architected ATOS_PAR success suppresses modeled STE output-attribute overrides while preserving the compatibility GATOS_PAR path."
        },
        {
          "path": "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc",
          "pattern": "Smmuv3GatosAddrAccessFieldsIgnoreSteOverrides",
          "description": "Component test validates ATOS_ADDR.PnU/InD/RnW decode and architected ATOS_PAR STE-override suppression."
        }
      ],
      "runtime_evidence": [
        {
          "path": "build/verification/apollo-smmuv3-multi-sid-ctest-20260510.log",
          "pattern": "100% tests passed",
          "description": "CTest covers the multi-StreamID isolation functional slice."
        },
        {
          "path": "build/verification/qbox-platform-smmu-comp-080-multi-sid-20260510.log",
          "pattern": "QBox Buildroot platform runtime built",
          "description": "Full QBox platform runtime rebuild passed with the StreamID extension in DMA/TBU headers."
        },
        {
          "path": "build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-080-multi-sid.driver.log",
          "pattern": "PASS: QBox guest IREE Hexagon tiny-CNN output matched",
          "description": "Guest IREE smoke passed after DMA started attaching StreamID extensions to translated requests."
        },
        {
          "path": "build/verification/apollo-smmuv3-cmd-invalidation-ctest-20260510.log",
          "pattern": "100% tests passed",
          "description": "CTest covers SID/page/global invalidation behavior after the command invalidation slice."
        },
        {
          "path": "build/verification/apollo-smmuv3-tagged-invalidation-ctest-20260510.log",
          "pattern": "100% tests passed",
          "description": "CTest covers ASID/VMID/SSID-tagged invalidation behavior."
        },
        {
          "path": "doc/verification/qbox-smmuv3-endpoint-ssid-verification-2026-05-10.md",
          "pattern": "Guest smoke",
          "description": "Verification report records runtime evidence that guest DMA traffic carries endpoint SSID tags through the TBU."
        },
        {
          "path": "doc/verification/qbox-smmuv3-linux-cmd-invalidation-verification-2026-05-10.md",
          "pattern": "ATC_INV",
          "description": "Runtime report records guest-visible ATC_INV/TLBI_NH_ALL command invalidation evidence."
        },
        {
          "path": "doc/verification/qbox-smmuv3-multi-master-topology-verification-2026-05-10.md",
          "pattern": "QBox SMMUv3 Multi-Master Topology Verification",
          "description": "Verification report records platform, Linux, runtime smoke, and static evidence for the StreamID 0x2 topology slice."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ste-bypass-output-attrs-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/080 STE bypass output-attribute propagation",
          "description": "Verification report records downstream TLM extension evidence for modeled STE bypass output attributes without claiming full PCIe/RID topology parity."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ste-config-bypass-output-attrs-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/080 STE.Config all-bypass output-attribute propagation",
          "description": "Verification report records build, focused gTest/CTest, static checker, lane, and closure evidence for modeled STE.Config all-bypass output-attribute propagation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-ats-translated-output-attrs-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/080 ATS Translated STE output-attribute propagation",
          "description": "Verification report records build, focused gTest/CTest, static checker, lane, and closure evidence for ATS Translated output-attribute propagation."
        },
        {
          "path": "doc/verification/qbox-smmuv3-gatos-par-output-attrs-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/080 GATOS_PAR STE output-attribute return path",
          "description": "Verification report records build, focused gTest/CTest, static checker, lane, and closure evidence for bounded GATOS_PAR output attributes."
        },
        {
          "path": "doc/verification/qbox-smmuv3-architected-gatos-registers-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/030/080 architected non-secure SMMU_GATOS register slice",
          "description": "Verification report records build, focused gTest/CTest, static checker, lane, and closure evidence for the non-secure SMMU_GATOS RUN/PAR/no-event path."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-gatos-registers-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-020/030/080 Secure SMMU_S_GATOS register slice",
          "description": "Verification report records build, focused gTest/CTest, static checker, lane, and closure evidence for the Secure SMMU_S_GATOS RUN/PAR/no-event path."
        },
        {
          "path": "build/verification/smmu-atos-addr-type-build-20260511.log",
          "pattern": "Built target apollo-smmu-tbu-tests",
          "description": "Apollo SMMU TBU tests rebuild after ATOS_ADDR.TYPE matrix implementation."
        },
        {
          "path": "build/verification/smmu-atos-addr-type-gtest-20260511.log",
          "pattern": "Smmuv3GatosAddrTypeNestedStageSelection",
          "description": "Focused gTest exercises reserved/INV_STAGE and nested ATOS_ADDR.TYPE stage-selection cases."
        },
        {
          "path": "build/verification/smmu-atos-addr-type-ctest-20260511.log",
          "pattern": "100% tests passed",
          "description": "CTest regression passes for the Apollo SMMU TBU component suite after ATOS_ADDR.TYPE changes."
        },
        {
          "path": "doc/verification/qbox-smmuv3-secure-gatos-ssec-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/080 S_GATOS.SSEC stream-selection slice",
          "description": "Verification report records build, focused gTest, CTest, static checker, and lane evidence for S_GATOS.SSEC stream selection."
        },
        {
          "path": "build/verification/smmu-secure-gatos-ssec-gtest-20260511.log",
          "pattern": "[  PASSED  ]",
          "description": "Focused gTest covers Secure GATOS SSEC Secure and Non-secure stream-selection paths."
        },
        {
          "path": "doc/verification/qbox-smmuv3-atos-access-fields-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-030/080 ATOS_ADDR access-field attribute slice",
          "description": "Verification report records build, focused gTest, CTest, static checker, lane, and closure evidence for the bounded ATOS_ADDR access-field attribute slice."
        },
        {
          "path": "build/verification/smmu-atos-access-fields-gtest-20260511.log",
          "pattern": "[  PASSED  ]",
          "description": "Focused gTest covers ATOS_ADDR.PnU/InD/RnW decode and STE-output-override suppression while preserving the compatibility GATOS_PAR path."
        }
      ]
    },
    {
      "id": "SMMU-COMP-090",
      "title": "Upstream IREE HAL registry",
      "status": "functional-slice",
      "owner": "Apollo guest tools/IREE staging",
      "claim_scope": "Repo-local iree-run-module dispatch now discovers apollo-hexagon through an upstream-style HAL registry frontend, dynamically dlopens/registers the staged Apollo Hexagon C HAL plugin, and rejects CPU fallback; upstream IREE source checkout is configured under sources/iree, while Apollo HAL build/registry integration remains pending.",
      "source_evidence": [
        {
          "path": ".gitmodules",
          "pattern": "github.com/iree-org/iree.git",
          "description": "Official upstream IREE source is configured as the sources/iree submodule."
        },
        {
          "path": "sources/iree/README.md",
          "pattern": "IREE: Intermediate Representation Execution Environment",
          "description": "The sources/iree checkout contains the upstream IREE source tree."
        },
        {
          "path": "configs/buildroot/external/apollo_qbox/package/iree-runtime/iree-runtime.mk",
          "pattern": "IREE_RUNTIME_BUILD_OPTS = --target iree-run-module",
          "description": "Buildroot can build the IREE runtime runner from the upstream source checkout."
        },
        {
          "path": "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hal_registry.c",
          "pattern": "apollo_iree_hal_registry_lookup",
          "description": "Repo-local HAL registry lookup exposes the apollo-hexagon device name."
        },
        {
          "path": "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hal_registry.c",
          "pattern": "dlopen\\(plugin_path, RTLD_NOW \\| RTLD_LOCAL\\)",
          "description": "Repo-local HAL registry dynamically loads the staged Apollo Hexagon C HAL plugin."
        },
        {
          "path": "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hal_registry.c",
          "pattern": "APOLLO_IREE_HEXAGON_PLUGIN_EXPORT_NAME",
          "description": "Repo-local HAL registry resolves the Apollo C HAL plugin query export before registration."
        },
        {
          "path": "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_run_module.c",
          "pattern": "dynamically registered C HAL plugin=%s",
          "description": "Run-module compatible frontend logs the dynamically registered plugin path, driver name, and ABI version."
        },
        {
          "path": "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hal_registry.c",
          "pattern": "CPU fallback device is disabled",
          "description": "CPU fallback device names are rejected for Apollo execution proof."
        },
        {
          "path": "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hexagon_plugin.c",
          "pattern": "iree_hal_executable_plugin_query",
          "description": "Repo-local plugin exports the upstream executable_plugin query symbol."
        },
        {
          "path": "scripts/stage_iree_tiny_cnn_guest_artifacts.sh",
          "pattern": "--executable_plugin",
          "description": "Guest staging dispatches Apollo execution through iree-run-module with the staged dynamic C HAL plugin."
        }
      ],
      "runtime_evidence": [
        {
          "path": "doc/verification/qbox-smmuv3-comp-090-verification-2026-05-10.md",
          "pattern": "SMMU-COMP-090 remains a functional slice",
          "description": "Verification report records registry dispatch evidence and the upstream-source blocker."
        },
        {
          "path": "doc/verification/qbox-smmuv3-iree-dynamic-registry-verification-2026-05-11.md",
          "pattern": "SMMU-COMP-090 dynamic C HAL plugin registry functional slice",
          "description": "Verification report records the dynamic C HAL plugin registry proof and remaining upstream IREE blocker."
        },
        {
          "path": "build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-iree-dynamic-registry.driver.log",
          "pattern": "PASS: QBox guest IREE Hexagon tiny-CNN output matched",
          "description": "QBox guest smoke completed the dynamic registry tiny-CNN path."
        },
        {
          "path": "build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-iree-dynamic-registry.log",
          "pattern": "dynamically registered C HAL plugin=",
          "description": "Guest runtime log proves the staged C HAL plugin was dynamically registered."
        }
      ]
    },
    {
      "id": "SMMU-REF-000",
      "title": "Pinned external SMMUv3 reference corpus",
      "status": "reference-only",
      "owner": "sources/smmu",
      "claim_scope": "Behavioral reference corpus, not copied into QBox implementation.",
      "reference_evidence": [
        {
          "path": "sources/smmu/README.md",
          "pattern": "ARM SMMU v3",
          "description": "Reference repository describes C++ and Rust SMMUv3 implementations."
        },
        {
          "path": "sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md",
          "pattern": "System Memory Management Unit",
          "description": "Spec-derived markdown is available in the submodule."
        },
        {
          "path": "build/verification/smmu-reference-cpp-v1.7.8-build-20260510.log",
          "pattern": "test_bug3_stall_pending_fields",
          "description": "Known C++ reference failure is preserved as a blocker/limitation."
        }
      ]
    }
  ]
}
```
<!-- QBOX_SMMUV3_CHECKLIST_JSON_END -->
