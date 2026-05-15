#!/usr/bin/env python3
"""Validate the QBox SMMUv3 compliance checklist and platform invariants.

The checker is intentionally conservative. It validates the machine-readable
checklist embedded in doc/spec/qbox-smmuv3-compliance-checklist.md, checks that
required evidence exists, and proves key QBox/DTS StreamID and named-IRQ
invariants. It does not certify full SMMUv3 compliance.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BEGIN = "<!-- QBOX_SMMUV3_CHECKLIST_JSON_BEGIN -->"
END = "<!-- QBOX_SMMUV3_CHECKLIST_JSON_END -->"
FENCE_RE = re.compile(r"^```(?:json)?\n(?P<body>.*)\n```$", re.DOTALL)


@dataclass(frozen=True)
class Result:
    name: str
    status: str
    detail: str


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def extract_manifest(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        raise ValueError(f"missing checklist: {path}")
    if BEGIN not in text or END not in text:
        raise ValueError(f"missing checklist JSON markers in {path}")
    body = text.split(BEGIN, 1)[1].split(END, 1)[0].strip()
    match = FENCE_RE.match(body)
    if match:
        body = match.group("body")
    return json.loads(body)


def has_pattern(repo: Path, path: str, pattern: str | None) -> tuple[bool, str]:
    full = repo / path
    text = read_text(full)
    if not full.exists():
        return False, f"missing path: {path}"
    if pattern and re.search(pattern, text, re.MULTILINE) is None:
        return False, f"missing pattern in {path}: {pattern}"
    return True, f"matched {path}"


def evidence_entries(row: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for key in ("source_evidence", "runtime_evidence", "reference_evidence"):
        for entry in row.get(key, []):
            item = dict(entry)
            item["kind"] = key
            entries.append(item)
    return entries


def validate_rows(repo: Path, manifest: dict[str, Any]) -> list[Result]:
    results: list[Result] = []
    allowed = set(manifest.get("allowed_statuses", []))
    ids: set[str] = set()
    for row in manifest.get("rows", []):
        row_id = row.get("id", "<missing-id>")
        status = row.get("status")
        entries = evidence_entries(row)
        if row_id in ids:
            results.append(Result(f"row:{row_id}", "fail", "duplicate row id"))
        ids.add(row_id)
        if status not in allowed:
            results.append(Result(f"row:{row_id}", "fail", f"invalid status: {status}"))
            continue
        if status == "implemented" and not entries:
            results.append(Result(f"row:{row_id}", "fail", "implemented row has no evidence"))
        title = row.get("title", "")
        if status == "implemented" and re.search(r"full .*compliance", title, re.I):
            results.append(Result(f"row:{row_id}", "fail", "implemented full-compliance claim is not allowed in this checklist"))
        for entry in entries:
            ok, detail = has_pattern(repo, entry["path"], entry.get("pattern"))
            results.append(Result(f"evidence:{row_id}:{entry['kind']}:{entry['path']}", "pass" if ok else "fail", detail))
    return results


def check_known_reference_failures(repo: Path, manifest: dict[str, Any]) -> list[Result]:
    results: list[Result] = []
    for item in manifest.get("known_reference_failures", []):
        ok, detail = has_pattern(repo, item["path"], item.get("pattern"))
        results.append(Result(f"known-reference-failure:{item.get('id')}", "pass" if ok else "fail", detail))
    return results


def check_platform_invariants(repo: Path) -> list[Result]:
    platform = read_text(repo / "sources/qbox/platforms/buildroot/conf_aarch64.lua")
    dts = read_text(repo / "configs/linux/apollo_soc.dts")
    linux_driver = read_text(repo / "sources/linux/drivers/soc/apollo/apollo-hexagon-test.c")
    tbu = read_text(repo / "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h")
    arch_core = read_text(repo / "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_arch_core.h")
    dma = read_text(repo / "sources/qbox/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h")
    stream_ext = read_text(repo / "sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h")
    tests = read_text(repo / "sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc")
    dma_tests = read_text(repo / "sources/qbox/tests/components/apollo_hexagon_dma/apollo-hexagon-dma-tests.cc")
    guest_tools = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools"
    iree_registry = read_text(guest_tools / "apollo_iree_hal_registry.c")
    iree_run_module = read_text(guest_tools / "apollo_iree_run_module.c")
    iree_stage = read_text(repo / "scripts/stage_iree_tiny_cnn_guest_artifacts.sh")
    guest_smoke = read_text(repo / "scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh")
    results: list[Result] = []

    def add(name: str, ok: bool, detail: str) -> None:
        results.append(Result(name, "pass" if ok else "fail", detail))

    add("platform:smmuv3-base", "APOLLO_SMMUV3 = 0x1C200000" in platform, "QBox SMMUv3 base is 0x1C200000")
    add("platform:stream-id", "APOLLO_HEXAGON_STREAM_ID = 0x1" in platform, "Apollo Hexagon StreamID is 0x1")
    add("platform:aux-stream-id", "APOLLO_HEXAGON_AUX_STREAM_ID = 0x2" in platform, "Apollo auxiliary DMA StreamID is 0x2")
    add(
        "platform:tbu-reg-window",
        re.search(
            r"hexagon_smmu_tbu_0\s*=\s*\{.*?regs\s*=\s*\{address=APOLLO_HEXAGON_CTRL \+ 0x1000,\s*size=0x10000,",
            platform,
            re.DOTALL,
        )
        is not None,
        "Apollo TBU MMIO window covers the compatibility registers, SMMUv3 page 0, and SMMU_S_* Secure page",
    )
    add("platform:translated-dma", "translated_dma = {bind = \"&hexagon_smmu_tbu_0.upstream\"}" in platform and "smmu_translated = true" in platform, "Hexagon DMA routes through Apollo TBU translated path")
    add(
        "platform:multi-master-topology",
        "hexagon_dma_1" in platform
        and "hexagon_smmu_tbu_1" in platform
        and "stream_id = APOLLO_HEXAGON_AUX_STREAM_ID" in platform
        and "translated_dma = {bind = \"&hexagon_smmu_tbu_1.upstream\"}" in platform,
        "QBox platform exposes a second SMMU-translated DMA master with StreamID 0x2",
    )
    irq_patterns = {
        "eventq": r"irq_out_0\s*=\s*\{bind = \"&gic_0\.spi_in_560\"\};\s*-- eventq",
        "priq": r"irq_out_1\s*=\s*\{bind = \"&gic_0\.spi_in_563\"\};\s*-- priq",
        "cmdq-sync": r"irq_out_2\s*=\s*\{bind = \"&gic_0\.spi_in_562\"\};\s*-- cmdq-sync",
        "gerror": r"irq_out_3\s*=\s*\{bind = \"&gic_0\.spi_in_561\"\};\s*-- gerror",
    }
    for name, pattern in irq_patterns.items():
        add(f"platform:named-irq:{name}", re.search(pattern, platform) is not None, f"platform named IRQ mapping for {name}")

    add("dts:smmuv3-compatible", "compatible = \"arm,smmu-v3\"" in dts and "reg = <0x00 0x1c200000 0x00 0x20000>" in dts, "DTS exposes arm,smmu-v3 at 0x1c200000")
    for name in ("eventq", "gerror", "cmdq-sync", "priq"):
        add(f"dts:interrupt-name:{name}", re.search(rf'"{re.escape(name)}"', dts) is not None, f"DTS names {name} interrupt")
    add("dts:iommu-stream-id", "iommus = <&smmu 0x1>" in dts and "apollo,smmu-stream-id = <0x1>" in dts, "DTS Hexagon StreamID matches platform StreamID 0x1")
    add("dts:aux-iommu-stream-id", "hexagon-aux@1c300000" in dts and "iommus = <&smmu 0x2>" in dts and "apollo,smmu-stream-id = <0x2>" in dts, "DTS exposes a second Linux-visible DMA master with StreamID 0x2")
    add("dts:dma-path", "apollo,dma-path = \"smmu-translated\"" in dts, "DTS declares smmu-translated DMA path")
    add(
        "tbu:architected-core-owner",
        "class apollo_smmu_arch_core" in arch_core
        and "translation_owner::apollo_systemc" in arch_core
        and "qemu_translation_bridge_enabled = false" in arch_core
        and "COMPATIBILITY_APERTURE_BASE = 0x0000" in arch_core
        and "SMMUV3_APERTURE_BASE = 0x1000" in arch_core
        and "state_ownership_contract" in arch_core
        and "owns_register_queue_state" in arch_core
        and "owns_stream_context_descriptor_state" in arch_core
        and "owns_page_table_walker_state" in arch_core
        and "owns_fault_replay_state" in arch_core
        and "classify_register" in arch_core
        and "struct queue_state" in arch_core
        and "cmdq_state()" in arch_core
        and "eventq_state()" in arch_core
        and "priq_state()" in arch_core
        and "reset_register_queue_state()" in arch_core
        and "stream_context_descriptor_state" in arch_core
        and "stream_context_state()" in arch_core
        and "reset_stream_context_descriptor_state()" in arch_core
        and "page_table_walker_state" in arch_core
        and "walker_state()" in arch_core
        and "reset_page_table_walker_state()" in arch_core
        and "fault_replay_state" in arch_core
        and "fault_replay_state_storage()" in arch_core
        and "reset_fault_replay_state()" in arch_core
        and "struct stall_record" in arch_core
        and "stall_records()" in arch_core
        and "find_stall(uint32_t stream_id" in arch_core
        and "find_stall_by_fault" in arch_core
        and "struct endpoint_replay_record" in arch_core
        and "struct endpoint_replay_transaction" in arch_core
        and "endpoint_replay_records()" in arch_core
        and "find_pending_endpoint_replay" in arch_core
        and "allocate_endpoint_replay_record(" in arch_core
        and "retire_endpoint_replay" in arch_core
        and "begin_endpoint_replay_redrive" in arch_core
        and "prepare_endpoint_replay_segment" in arch_core
        and "complete_endpoint_replay_segment" in arch_core
        and "begin_endpoint_replay_transaction" in arch_core
        and "complete_endpoint_replay_transaction" in arch_core
        and "finish_endpoint_replay_redrive" in arch_core
        and "fail_endpoint_replay_redrive" in arch_core
        and "reset_endpoint_replay_records()" in arch_core
        and "struct event_record_layout" in arch_core
        and "fault_detail_word(uint32_t reason" in arch_core
        and "event_number_for_fault(uint32_t reason)" in arch_core
        and "build_event_record(uint32_t stream_id" in arch_core
        and "endpoint_replay_status() const" in arch_core
        and "early_retry_status() const" in arch_core
        and "queue_entries(uint64_t queue_base)" in arch_core
        and "queue_base_addr(uint64_t queue_base)" in arch_core
        and "queue_index(uint32_t value, uint32_t entries)" in arch_core
        and "walker_page_shift(uint32_t granule)" in arch_core
        and "walker_level_index(uint64_t iova" in arch_core
        and "walker_level_offset_mask(uint32_t granule" in arch_core
        and "struct descriptor_walk_config" in arch_core
        and "struct descriptor_fetch" in arch_core
        and "struct descriptor_memory_read" in arch_core
        and "enum class descriptor_step_kind" in arch_core
        and "begin_descriptor_walk(uint64_t iova" in arch_core
        and "descriptor_fetch_address(uint64_t table_pa" in arch_core
        and "begin_descriptor_fetch(uint64_t table_pa" in arch_core
        and "complete_descriptor_fetch(uint32_t stage" in arch_core
        and "fail_descriptor_fetch(uint32_t stage" in arch_core
        and "begin_descriptor_memory_read(" in arch_core
        and "complete_descriptor_memory_read(" in arch_core
        and "fail_descriptor_memory_read(" in arch_core
        and "evaluate_descriptor_step(uint64_t iova" in arch_core
        and "finish_descriptor_leaf(uint64_t iova" in arch_core
        and "stream_table_log2size(uint32_t cfg)" in arch_core
        and "stream_table_l1_desc_valid" in arch_core
        and "ste_config(uint64_t ste0)" in arch_core
        and "ste_is_s1_enabled(uint64_t ste0)" in arch_core
        and "cd_is_valid(uint64_t cd0)" in arch_core
        and "effective_eats(uint64_t ste0" in arch_core
        and "apollo_smmu_arch_core m_arch_core" in tbu
        and "using arch_queue = apollo::smmuv3::apollo_smmu_arch_core::queue_state" in tbu
        and "using arch_stream_context_state" in tbu
        and "using arch_walker_state" in tbu
        and "m_cmdq(m_arch_core.cmdq_state())" in tbu
        and "m_arch_stream_context(m_arch_core.stream_context_state())" in tbu
        and "m_arch_strtab_base(m_arch_stream_context.strtab_base)" in tbu
        and "m_arch_walker(m_arch_core.walker_state())" in tbu
        and "m_arch_ttbr(m_arch_walker.ttbr)" in tbu
        and "using arch_fault_replay_state" in tbu
        and "m_arch_fault_replay(m_arch_core.fault_replay_state_storage())" in tbu
        and "using arch_stall_record = apollo::smmuv3::apollo_smmu_arch_core::stall_record"
        in tbu
        and "m_arch_stalls(m_arch_core.stall_records())" in tbu
        and "using arch_endpoint_replay_record" in tbu
        and "m_arch_endpoint_replays(m_arch_core.endpoint_replay_records())" in tbu
        and "m_arch_core.find_pending_endpoint_replay(stream_id, stag)" in tbu
        and "m_arch_core.allocate_endpoint_replay_record(" in tbu
        and "m_arch_core.retire_endpoint_replay" in tbu
        and "m_arch_core.begin_endpoint_replay_redrive" in tbu
        and "m_arch_core.prepare_endpoint_replay_segment" in tbu
        and "m_arch_core.begin_endpoint_replay_transaction" in tbu
        and "m_arch_core.complete_endpoint_replay_transaction" in tbu
        and "execute_endpoint_replay_transaction" in tbu
        and "execute_descriptor_memory_read" in tbu
        and "class arch_io_executor" in tbu
        and "class default_arch_io_executor" in tbu
        and "m_arch_io_executor->read_descriptor(*this, read, desc)" in tbu
        and "m_arch_io_executor->replay_transaction(*this, transaction, delay)" in tbu
        and "set_arch_io_executor_for_testing" in tbu
        and "FakeArchIoExecutor" in tests
        and "m_arch_core.finish_endpoint_replay_redrive" in tbu
        and "m_arch_core.reset_endpoint_replay_records()" in tbu
        and "m_arch_fault_reason(m_arch_fault_replay.fault_reason)" in tbu
        and "m_arch_next_stag(m_arch_fault_replay.next_stag)" in tbu
        and "arch_queue& m_eventq" in tbu
        and "m_arch_core.classify_register" in tbu
        and "apollo_smmu_arch_core::queue_entries(queue.base)" in tbu
        and "apollo_smmu_arch_core::queue_base_addr(queue.base)" in tbu
        and "apollo_smmu_arch_core::queue_index(value, entries)" in tbu
        and "apollo_smmu_arch_core::walker_page_shift(granule)" in tbu
        and "apollo_smmu_arch_core::walker_level_index" in tbu
        and "m_arch_core.begin_descriptor_walk" in tbu
        and "m_arch_core.begin_descriptor_fetch" in tbu
        and "m_arch_core.begin_descriptor_memory_read" in tbu
        and "m_arch_core.complete_descriptor_memory_read" in tbu
        and "m_arch_core.fail_descriptor_memory_read" in tbu
        and "m_arch_core.evaluate_descriptor_step" in tbu
        and "const uint64_t request_iova = m_arch_iova" in tbu
        and "apollo_smmu_arch_core::stream_table_log2size" in tbu
        and "apollo_smmu_arch_core::ste_config(ste0)" in tbu
        and "apollo_smmu_arch_core::cd_is_valid(cd0)" in tbu
        and "apollo_smmu_arch_core::effective_eats" in tbu
        and "apollo_smmu_arch_core::fault_detail_word" in tbu
        and "apollo_smmu_arch_core::event_number_for_fault" in tbu
        and "m_arch_core.build_event_record" in tbu
        and "m_arch_core.endpoint_replay_status()" in tbu
        and "ArchitectedCoreOwnsCanonicalTranslationState" in tests,
        "Apollo TBU owns canonical SystemC SMMUv3 register/queue, STE/CD, walker, and replay state through the architected core object while preserving the compatibility adapter, storing CMDQ/EVENTQ/PRIQ plus stream/context selector, walker, fault/replay scalar protocol state, STAG stall-record table storage, and endpoint replay payload record storage in the core, and routing queue geometry, walker geometry, descriptor-walk validation/fetch planning/step classification, descriptor-fetch lifecycle/fault capture, descriptor memory-read request/result wrapping, STE/CD descriptor decode, EVENTQ fault-record layout, replay/status packing, stall-record lookup, endpoint replay record lookup/reset helpers, endpoint replay allocation/retirement transitions, endpoint replay redrive payload/status state transitions, endpoint replay downstream transaction request/result wrapping, and a swappable adapter descriptor/replay I/O executor interface through the core boundary",
    )
    add(
        "tbu:irq-outputs",
        "sc_core::sc_vector<InitiatorSignalSocket<bool>> irq_out" in tbu and "update_irq_outputs" in tbu,
        "Apollo TBU exposes signal-level architected IRQ outputs; full MSI/GIC delivery remains a later gate",
    )
    add(
        "dma:async-fence-irq-signal",
        "InitiatorSignalSocket<bool> irq_out" in dma
        and "update_irq_output" in dma
        and "irq_out = {bind = \"&gic_0.spi_in_564\"}" in platform
        and "irq_out = {bind = \"&gic_0.spi_in_566\"}" in platform
        and "AsyncFenceDrivesIrqSignalUntilAck" in dma_tests,
        "Apollo Hexagon DMA async fence IRQ status now drives a signal-level Linux-visible doorbell until software ACK",
    )
    add(
        "linux:dma-async-irq-wait",
        "platform_get_irq_byname_optional" in linux_driver
        and "\"doorbell\"" in linux_driver
        and "devm_request_irq" in linux_driver
        and "atomic_or(pending, &test->async_irq_pending)" in linux_driver
        and "writel(pending, test->regs + APOLLO_HEXAGON_REG_IRQ_ACK)" in linux_driver
        and "wait_for_completion_timeout" in linux_driver
        and "complete_all(&test->async_fence)" in linux_driver
        and "apollo_hexagon_prepare_async_fence" in linux_driver
        and "async doorbell irq ready irq=%d" in linux_driver
        and "async fence irq wait" in linux_driver,
        "Linux Apollo Hexagon driver binds the doorbell IRQ and waits on interrupt-driven async fence completion before polling fallback",
    )
    add(
        "tbu:irq-msi-cfg",
        "FEATURE_ARCH_IRQ_MSI_CFG" in tbu
        and "ARCH_IDR0_MSI" in tbu
        and "SMMUV3_GERROR_IRQ_CFG0" in tbu
        and "SMMUV3_EVENTQ_IRQ_CFG0" in tbu
        and "SMMUV3_PRIQ_IRQ_CFG0" in tbu
        and "ARCH_GERROR_MSI_CMDQ_ABORT" in tbu
        and "ARCH_GERROR_MSI_EVENTQ_ABORT" in tbu
        and "ARCH_GERROR_MSI_PRIQ_ABORT" in tbu
        and "ARCH_GERROR_MSI_GERROR_ABORT" in tbu
        and "emit_arch_msi" in tbu
        and "MsiIrqCfgRegistersAreMaskedAndGuarded" in tests
        and "MsiWritesAndAbortGerrorBitsFollowIrqSources" in tests
        and "CmdSyncMsiWriteAndAbortAreReported" in tests
        and "APOLLO_TBU_FEATURE_ARCH_IRQ_MSI_CFG" in linux_driver
        and "APOLLO_SMMUV3_ARCH_IDR0\t\t0x098db7cb" in linux_driver
        and "APOLLO_SMMUV3_STATUS\t\t0x0e0" in linux_driver,
        "Apollo TBU models architected MSI IRQ_CFG registers, CMD_SYNC MSI writes, and MSI abort GERROR bits with component and Linux probe gates",
    )
    add(
        "tbu:idr0-ats-pri-advertisement",
        "ARCH_IDR0_ATS" in tbu
        and "ARCH_IDR0_PRI" in tbu
        and "arch_ats_supported" in tbu
        and "arch_pri_supported" in tbu
        and "pri-resp-unsupported" in tbu
        and "atc-inv-unsupported" in tbu
        and "ArchitectedIdr0AdvertisesAtsPri" in tests
        and "APOLLO_SMMUV3_ARCH_IDR0\t\t0x098db7cb" in linux_driver
        and "SMMU-COMP-020/060 IDR0 ATS/PRI advertisement slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-idr0-ats-pri-advertisement-verification-2026-05-11.md"),
        "Apollo TBU and Linux probe advertise IDR0.ATS/PRI for modeled ATC/PRI command support and keep unsupported-command CERROR gates explicit",
    )
    add(
        "tbu:multi-stream-id-isolation",
        "FEATURE_MULTI_STREAM_ID" in tbu
        and "map.stream_id != stream_id" in tbu
        and "clear_ats_cache(uint32_t stream_id)" in tbu
        and "class ApolloSmmuStreamIdExtension" in stream_ext
        and "trans.set_extension(&stream_id_ext)" in dma,
        "Apollo TBU/DMA carry StreamID and isolate dynamic maps/ATS entries per SID; platform/DTS now expose a second Linux-visible master",
    )
    add(
        "tbu:cmdq-invalidation",
        "FEATURE_ARCH_CMD_INVALIDATION" in tbu
        and "handle_cmdq_cfgi" in tbu
        and "handle_cmdq_tlbi" in tbu
        and "handle_cmdq_atc_inv" in tbu
        and "clear_ats_cache_page(uint32_t stream_id, uint64_t page)" in tbu
        and "CmdqInvalidationCommandsClearAtsBySidPageAndGlobal" in tests,
        "Apollo TBU component-tests command-driven CFGI/TLBI/ATC invalidation of modeled ATS entries by SID/page/global scope",
    )
    add(
        "tbu:cmdq-cfgi-vms-pidm",
        "FEATURE_ARCH_CFGI_VMS_PIDM" in tbu
        and "ARCH_CMD_CFGI_VMS_PIDM = 0x07" in tbu
        and "handle_cmdq_cfgi_vms_pidm" in tbu
        and "clear_modeled_vms_state_for_vmid" in tbu
        and "CmdqCfgiVmsPidmInvalidatesModeledVmsState" in tests,
        "Apollo TBU component-tests CMD_CFGI_VMS_PIDM invalidation of the modeled VMID-indexed VMS/PARTID_MAP cache state without ATS/TLB flushing",
    )
    add(
        "linux:cmdq-invalidation-probe",
        "APOLLO_TBU_FEATURE_ARCH_CMD_INVALIDATION" in linux_driver
        and "APOLLO_SMMUV3_ARCH_CMD_ATC_INV" in linux_driver
        and "APOLLO_SMMUV3_ARCH_CMD_TLBI_NH_ALL" in linux_driver
        and "SMMUv3 command invalidation selftest ok" in linux_driver,
        "Apollo Linux probe drives guest-visible CMDQ ATC_INV/TLBI_NH_ALL invalidation and verifies the TBU invalidation counter",
    )
    add(
        "linux:ril-range-stress",
        "ARCH_IDR3_RIL = 1u << 10" in tbu
        and "ARCH_IDR3_MPAM | ARCH_IDR3_RIL" in tbu
        and "APOLLO_SMMUV3_ARCH_IDR3_RIL" in linux_driver
        and "APOLLO_SMMUV3_ARCH_CMD_TLBI_NH_VA" in linux_driver
        and "apollo_hexagon_issue_ril_tlbi" in linux_driver
        and "APOLLO_SMMUV3_ARCH_CMDQ_RANGE_TG_4K" in linux_driver
        and "SMMUv3 RIL TLBI_NH_VA range selftest ok" in linux_driver
        and "SMMUv3 RIL TLBI_NH_VA range selftest ok" in guest_smoke,
        "Apollo TBU advertises IDR3.RIL and the Linux guest DMA-stress path issues a TLBI_NH_VA range command through CMDQ after >64KB SG traffic, validating guest-visible range invalidation",
    )
    add(
        "tbu:cr0-queue-enable-gates",
        "FEATURE_ARCH_CR0_QUEUE_GATES" in tbu
        and "ARCH_CR0_PRIQEN" in tbu
        and "ARCH_CR0_EVENTQEN" in tbu
        and "ARCH_CR0_CMDQEN" in tbu
        and "ARCH_CR0_ATSCHK" in tbu
        and "arch_cmdq_enabled" in tbu
        and "arch_eventq_enabled" in tbu
        and "arch_priq_enabled" in tbu
        and "Cr0QueueEnableGatesCmdEventAndPriQueues" in tests,
        "Apollo TBU enforces spec-position CR0 SMMUEN/PRIQEN/EVENTQEN/CMDQEN gates for memory-backed queues",
    )
    add(
        "tbu:output-queue-ovflg-ovack",
        "FEATURE_ARCH_QUEUE_OVERFLOW_FLAGS" in tbu
        and "ARCH_QUEUE_OVFLG" in tbu
        and "queue_prod_reg" in tbu
        and "queue_cons_reg" in tbu
        and "set_arch_queue_overflow" in tbu
        and "write_arch_output_queue_cons" in tbu
        and "EventAndPriQueueOverflowFlagsToggleAndAck" in tests,
        "Apollo TBU component-tests EVENTQ/PRIQ OVFLG/OVACKFLG toggle and acknowledgement semantics for output queue overflow",
    )
    add(
        "tbu:queue-write-abort-gerror",
        "ARCH_GERROR_EVENTQ_ABORT" in tbu
        and "ARCH_GERROR_PRIQ_ABORT" in tbu
        and "set_arch_gerror(abort_gerror)" in tbu
        and "EventAndPriQueueWriteAbortUseArchitectedGerrorBits" in tests
        and "APOLLO_SMMUV3_ARCH_GERROR_EVENTQ_ABORT" in linux_driver
        and "APOLLO_SMMUV3_ARCH_GERROR_PRIQ_ABORT" in linux_driver,
        "Apollo TBU component-tests architected EVENTQ_ABT_ERR and PRIQ_ABT_ERR GERROR bits on output queue write abort",
    )
    add(
        "tbu:irq-ctrl-reserved-mask",
        "ARCH_IRQ_CTRL_WRITABLE_MASK" in tbu
        and "m_arch_irq_ctrl = value & ARCH_IRQ_CTRL_WRITABLE_MASK" in tbu
        and "IrqCtrlReservedBitsAreMaskedInCtrlAck" in tests,
        "Apollo TBU component-tests IRQ_CTRL reserved bits are masked in IRQ_CTRL and IRQ_CTRLACK",
    )
    add(
        "tbu:gerrorn-active-toggle",
        "read_arch_gerror_raw" in tbu
        and "read_arch_gerror" in tbu
        and "set_arch_gerror" in tbu
        and "ack_arch_gerror" in tbu
        and "GerrorRegisterExposesRawToggleStateAndGerrornAcknowledgesActiveBits" in tests,
        "Apollo TBU component-tests raw GERROR toggle exposure, GERRORN active-bit acknowledgement, and repeated error retoggle behavior",
    )
    add(
        "linux:gerror-active-xor",
        "apollo_smmuv3_gerror_active" in linux_driver
        and "APOLLO_SMMUV3_ARCH_GERROR_KNOWN_MASK" in linux_driver
        and "gerrorn=0x%x active=0x%x" in linux_driver,
        "Apollo Linux probe computes active global errors as GERROR xor GERRORN while the TBU exposes raw GERROR toggle state",
    )
    add(
        "linux:cr0-queue-enable-probe",
        "APOLLO_TBU_FEATURE_ARCH_CR0_QUEUE_GATES" in linux_driver
        and "APOLLO_SMMUV3_CR0_ENABLE_QUEUES" in linux_driver
        and "APOLLO_SMMUV3_CR0_CMDQEN" in linux_driver
        and "APOLLO_SMMUV3_CR0_EVENTQEN" in linux_driver
        and "APOLLO_SMMUV3_CR0_PRIQEN" in linux_driver,
        "Apollo Linux probe enables spec-position CR0 queue gates before using CMDQ/EVENTQ/PRIQ",
    )
    add(
        "tbu:atschk-eats-gates",
        "FEATURE_ARCH_ATSCHK_EATS_GATES" in tbu
        and "ARCH_CTRL_ATS_TRANSLATION_REQUEST" in tbu
        and "ARCH_STE_EATS_SHIFT" in tbu
        and "ARCH_FAULT_BAD_ATS_TREQ" in tbu
        and "run_arch_ats_translation_request" in tbu
        and "AtsTranslationRequestHonorsCr0AtschkAndSteEats" in tests,
        "Apollo TBU component-tests CR0.ATSCHK plus STE.EATS gating for ATS Translation Requests",
    )
    add(
        "linux:atschk-eats-probe",
        "APOLLO_TBU_FEATURE_ARCH_ATSCHK_EATS_GATES" in linux_driver
        and "APOLLO_TBU_ARCH_CTRL_ATS_TREQ" in linux_driver
        and "APOLLO_TBU_ARCH_STE_EATS" in linux_driver
        and "SMMUv3 ATSCHK/EATS translation request selftest ok" in linux_driver,
        "Apollo Linux probe validates ATS Translation Request UR gating for EATS disabled/split-without-ATSCHK and success for Full ATS",
    )
    add(
        "tbu:rec-cfg-ats-gates",
        "FEATURE_ARCH_REC_CFG_ATS_GATES" in tbu
        and "ARCH_CR2_REC_CFG_ATS" in tbu
        and "ARCH_CR2_RECINVSID" in tbu
        and "arch_record_smmuen_disabled_ats_treq" in tbu
        and "arch_record_bad_streamid_ats_treq" in tbu
        and "AtsTranslationRequestHonorsCr2RecCfgAtsAndRecInvsid" in tests,
        "Apollo TBU component-tests CR2.REC_CFG_ATS/RECINVSID event-recording gates for ATS Translation Requests",
    )
    add(
        "tbu:bad-streamid-recinvsid-gate",
        "arch_record_bad_streamid_event" in tbu
        and "ARCH_CR2_RECINVSID" in tbu
        and "ARCH_FAULT_BAD_STREAM_ID" in tbu
        and "ARCH_EVENT_C_BAD_STREAMID" in tbu
        and "BadStreamIdHonorsCr2RecInvsidForEventRecording" in tests,
        "Apollo TBU suppresses normal C_BAD_STREAMID EVENTQ records until CR2.RECINVSID permits recording",
    )
    add(
        "linux:rec-cfg-ats-probe",
        "APOLLO_TBU_FEATURE_ARCH_REC_CFG_ATS_GATES" in linux_driver
        and "APOLLO_SMMUV3_CR2_REC_CFG_ATS" in linux_driver
        and "SMMUv3 REC_CFG_ATS translation request selftest ok" in linux_driver,
        "Apollo Linux probe validates SMMUEN-disabled ATS Translation Request recording is suppressed until CR2.REC_CFG_ATS is set",
    )
    add(
        "tbu:dpti-unsupported-commands",
        "FEATURE_ARCH_DPTI_UNSUPPORTED" in tbu
        and "FEATURE_ARCH_CMDQ_CERROR" in tbu
        and "ARCH_IDR3_DPT = 1u << 15" in tbu
        and "ARCH_IDR3_PTWNNC" in tbu
        and "ARCH_CMD_DPTI_ALL" in tbu
        and "ARCH_CMD_DPTI_PA" in tbu
        and "ARCH_CMDQ_CONS_ERR_SHIFT" in tbu
        and "ARCH_CMDQ_CERROR_ILL" in tbu
        and "handle_cmdq_dpti_unsupported" in tbu
        and "DptiCommandsSetGerrorWhenDptUnsupported" in tests,
        "Apollo TBU component-tests CMD_DPTI_ALL/CMD_DPTI_PA rejection with IDR3.DPT=0, CMDQ_CONS.CERROR_ILL, and GERROR signaling",
    )
    add(
        "tbu:cmdq-cerror-abt",
        "FEATURE_ARCH_CMDQ_CERROR" in tbu
        and "ARCH_CMDQ_CERROR_ABT" in tbu
        and "set_cmdq_cerror(ARCH_CMDQ_CERROR_ABT" in tbu
        and "CmdqUnconfiguredQueueSetsCerrorAbt" in tests,
        "Apollo TBU component-tests CMDQ_CONS.CERROR_ABT and GERROR signaling for an enabled but unconfigured command queue",
    )
    add(
        "tbu:cmdq-cerror-atc-inv-sync",
        "FEATURE_ARCH_CMDQ_CERROR" in tbu
        and "ARCH_CMDQ_CERROR_ATC_INV_SYNC" in tbu
        and "m_arch_atc_inv_sync_error_pending" in tbu
        and "CmdSyncAfterFailedAtcInvSetsCerrorAtcInvSync" in tests,
        "Apollo TBU component-tests CMD_SYNC reporting CMDQ_CONS.CERROR_ATC_INV_SYNC after a modeled failed CMD_ATC_INV completion",
    )
    add(
        "tbu:cmdq-cerror-atc-inv-sync-multi",
        "m_arch_atc_inv_sync_pending_count" in tbu
        and "m_arch_atc_inv_sync_force_fail_count" in tbu
        and "CmdSyncCoalescesOutstandingAtcInvFailuresAndPauses" in tests,
        "Apollo TBU component-tests multiple outstanding failed CMD_ATC_INV completions coalescing into one CMD_SYNC CERROR and pausing the queue until software recovery",
    )
    add(
        "linux:dpti-unsupported-probe",
        "APOLLO_TBU_FEATURE_ARCH_DPTI_UNSUPPORTED" in linux_driver
        and "APOLLO_TBU_FEATURE_ARCH_CMDQ_CERROR" in linux_driver
        and "APOLLO_SMMUV3_ARCH_IDR3" in linux_driver
        and "APOLLO_SMMUV3_ARCH_CMD_DPTI_ALL" in linux_driver
        and "APOLLO_SMMUV3_ARCH_CERROR_ILL" in linux_driver
        and "dpti_cerror" in linux_driver
        and "SMMUv3 DPTI unsupported command selftest ok" in linux_driver,
        "Apollo Linux probe validates CMD_DPTI_ALL is rejected through guest-visible CMDQ_CONS.CERROR_ILL when IDR3.DPT=0",
    )
    add(
        "tbu:dpt-unsupported-registers-res0",
        "ARCH_IDR3_DPT" in tbu
        and "ARCH_IDR3_MPAM | ARCH_IDR3_RIL" in tbu
        and "SMMUV3_DPT_BASE_LO = 0x200" in tbu
        and "SMMUV3_DPT_BASE_CFG = 0x208" in tbu
        and "SMMUV3_DPT_CFG_FAR_LO = 0x210" in tbu
        and "ARCH_DPT_UNSUPPORTED_RES0" in tbu
        and "IDR3.DPT=0: unsupported DPT registers are RES0/WI" in tbu
        and "DptUnsupportedRegistersAreRes0" in tests
        and "SMMU-COMP-020/050/060 DPT unsupported-register RES0 slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-dpt-register-res0-verification-2026-05-11.md"),
        "Apollo TBU exposes DPT_BASE/DPT_BASE_CFG/DPT_CFG_FAR as RES0/WI while IDR3.DPT is clear",
    )
    add(
        "tbu:ecmdq-unsupported-registers-res0",
        "ARCH_IDR1_ECMDQ = 1u << 31" in tbu
        and "ARCH_S_IDR0_ECMDQ = 1u << 31" in tbu
        and "SMMUV3_IDR6 = 0x190" in tbu
        and "SMMUV3_CMDQ_CONTROL_PAGE_BASE_LO = 0x4000" in tbu
        and "SMMUV3_CMDQ_CONTROL_PAGE_CFG = 0x4008" in tbu
        and "SMMUV3_CMDQ_CONTROL_PAGE_STATUS = 0x400c" in tbu
        and "SMMUV3_S_CMDQ_CONTROL_PAGE_BASE_LO" in tbu
        and "ARCH_ECMDQ_UNSUPPORTED_RES0" in tbu
        and "IDR1.ECMDQ=0/S_IDR0.ECMDQ=0: unsupported ECMDQ registers are RES0/WI"
        in tbu
        and "EcmdqUnsupportedRegistersAreRes0" in tests
        and "SMMU-COMP-020/060 ECMDQ unsupported-register RES0 slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-ecmdq-register-res0-verification-2026-05-11.md"),
        "Apollo TBU exposes SMMU_IDR6/SMMU_S_IDR6 and first ECMDQ control-page discovery registers as RES0/WI while ECMDQ is clear",
    )
    add(
        "tbu:idr1-discovery-limits",
        "ARCH_IDR0_ST_LEVEL_2LVL" in tbu
        and "ARCH_IDR1_SIDSIZE = 8" in tbu
        and "ARCH_IDR1_SSIDSIZE = 20" in tbu
        and "ARCH_IDR1_QUEUE_LOG2_MAX = 15" in tbu
        and "ARCH_IDR1_ATTR_PERMS_OVR = 1u << 26" in tbu
        and "ARCH_IDR1_ATTR_TYPES_OVR = 1u << 27" in tbu
        and "ARCH_IDR1 = (ARCH_IDR1_SIDSIZE << ARCH_IDR1_SIDSIZE_SHIFT)" in tbu
        and "ARCH_S_IDR1 = ARCH_S_IDR1_SECURE_IMPL | ARCH_S_IDR1_SEL2" in tbu
        and "ARCH_S_IDR1_S_SIDSIZE = ARCH_IDR1_SIDSIZE" in tbu
        and "ArchitectedRegisterMmioSurface" in tests
        and "ARCH_IDR1_ATTR_PERMS_OVR" in tests
        and "APOLLO_SMMUV3_ARCH_IDR0\t\t0x098db7cb" in linux_driver
        and "APOLLO_SMMUV3_ARCH_IDR1\t\t0x0def7d08" in linux_driver
        and "SMMU-COMP-020/030/050/060 IDR1 discovery/limits slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-idr1-discovery-limits-verification-2026-05-11.md"),
        "Apollo TBU advertises modeled IDR1 SID/SSID, queue-depth, attribute-override limits and keeps Secure IDR1 RES0 fields masked",
    )
    add(
        "tbu:idr0-stage-ttf-cd2l-discovery",
        "ARCH_IDR0_S1P = 1u << 1" in tbu
        and "ARCH_IDR0_S2P = 1u << 0" in tbu
        and "ARCH_IDR0_TTF_AARCH64 = 0x2u << ARCH_IDR0_TTF_SHIFT" in tbu
        and "ARCH_IDR0_CD2L = 1u << 19" in tbu
        and "ARCH_IDR0_ST_LEVEL_2LVL" in tbu
        and "ARCH_IDR0 = ARCH_IDR0_S2P | ARCH_IDR0_S1P" in tbu
        and "ARCH_IDR0_TTF_AARCH64" in tests
        and "ARCH_IDR0_CD2L" in tests
        and "APOLLO_SMMUV3_ARCH_IDR0\t\t0x098db7cb" in linux_driver
        and "SMMU-COMP-020/030/040 IDR0 S1P/TTF/CD2L discovery slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-idr0-stage-ttf-cd2l-verification-2026-05-11.md"),
        "Apollo TBU advertises stage-1/stage-2, AArch64 translation format, two-level stream tables, and two-level context descriptors to match modeled walkers",
    )
    add(
        "tbu:idr0-asid16-vmid16-discovery",
        "ARCH_IDR0_ASID16 = 1u << 12" in tbu
        and "ARCH_IDR0_VMID16 = 1u << 18" in tbu
        and "ARCH_CD_ASID_MASK = 0xffffULL << ARCH_CD_ASID_SHIFT" in tbu
        and "ARCH_STE_S2VMID_MASK = 0xffff" in tbu
        and "constexpr uint16_t asid_a = 0x1234" in tests
        and "constexpr uint16_t asid_b = 0x9234" in tests
        and "constexpr uint16_t vmid_a = 0x5678" in tests
        and "constexpr uint16_t vmid_b = 0xd678" in tests
        and "APOLLO_SMMUV3_ARCH_IDR0\t\t0x098db7cb" in linux_driver
        and "SMMU-COMP-020/040/060 IDR0 ASID16/VMID16 discovery slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-idr0-asid16-vmid16-verification-2026-05-11.md"),
        "Apollo TBU advertises ASID16/VMID16 and validates high-bit ASID/VMID retention through tagged invalidation tests",
    )
    add(
        "tbu:secure-idr3-sams-res0",
        "ARCH_S_IDR3_SAMS = 1u << 6" in tbu
        and "ARCH_S_IDR3 = 0x00000000" in tbu
        and "case SMMUV3_IDR3:\n            return ARCH_S_IDR3;" in tbu
        and "ARCH_IDR3_MPAM |" in tests
        and "ARCH_S_IDR3_SAMS" in tests
        and "SecureRegisterBankConfiguresStrtabCmdqAndEventq" in tests
        and "SMMU-COMP-020/060 Secure IDR3 SAMS/RES0 slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-secure-idr3-sams-res0-verification-2026-05-11.md"),
        "Apollo TBU exposes Secure SMMU_S_IDR3 as SAMS/RES0-only instead of mirroring Non-secure MPAM/RIL/DPT discovery bits",
    )
    add(
        "tbu:secure-idr0-msi-stall-res0",
        "ARCH_S_IDR0_MSI = 1u << 13" in tbu
        and "ARCH_S_IDR0_STALL_MODEL_MASK = 0x3u << 24" in tbu
        and "ARCH_S_IDR0_STALL_MODEL_TERMINATE_ONLY = 0x1u << 24" in tbu
        and "ARCH_S_IDR0 = ARCH_S_IDR0_MSI |" in tbu
        and "case SMMUV3_IDR0:\n            return ARCH_S_IDR0;" in tbu
        and "ARCH_S_IDR0_STALL_MODEL_MASK" in tests
        and "ARCH_S_IDR0_ECMDQ" in tests
        and "SMMU-COMP-020/070 Secure IDR0 MSI/stall/RES0 slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-secure-idr0-msi-stall-res0-verification-2026-05-11.md"),
        "Apollo TBU exposes Secure SMMU_S_IDR0 as the bounded MSI/stall/ECMDQ discovery surface instead of mirroring Non-secure IDR0 feature bits",
    )
    add(
        "tbu:aidr-v33-idr3-mandatory-discovery",
        "ARCH_AIDR_SMMUV3_3 = 0x00000003" in tbu
        and "ARCH_IDR3_HAD = 1u << 2" in tbu
        and "ARCH_IDR3_XNX = 1u << 4" in tbu
        and "ARCH_IDR3_FWB = 1u << 8" in tbu
        and "ARCH_IDR3_STT = 1u << 9" in tbu
        and "ARCH_IDR3_BBML_LEVEL_2 = 0x2u << ARCH_IDR3_BBML_SHIFT" in tbu
        and "ARCH_IDR3_E0PD = 1u << 13" in tbu
        and "ARCH_IDR3_PTWNNC = 1u << 14" in tbu
        and "ARCH_AIDR_SMMUV3_3" in tests
        and "ARCH_IDR3_BBML_LEVEL_2" in tests
        and "APOLLO_SMMUV3_ARCH_AIDR\t\t0x00000003" in linux_driver
        and "APOLLO_SMMUV3_ARCH_IDR3\t\t0x00007794" in linux_driver
        and "SMMU-COMP-020/040/060 AIDR v3.3 and IDR3 mandatory discovery slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-aidr-v33-idr3-mandatory-verification-2026-05-11.md"),
        "Apollo TBU reports an AIDR SMMUv3.3 discovery surface and the mandatory v3.2/v3.3 IDR3 HAD/XNX/FWB/STT/BBML/E0PD/PTWNNC bits required by the already-advertised MPAM/RIL/SEL2/ATSRECERR slices",
    )
    add(
        "tbu:e0pd-ptwnnc-behavior",
        "ARCH_CD_E0PD0 = 1ULL << 2" in tbu
        and "ARCH_CD_E0PD1 = 1ULL << 2" in tbu
        and "arch_cd_e0pd_blocks_access" in tbu
        and "m_arch_last_e0pd_fault" in tbu
        and "arch_desc_s2_memattr_is_device" in tbu
        and "m_arch_last_ptwnnc_normalized" in tbu
        and "PTWNNC normalizes" in tbu
        and "CdE0pdBlocksUnprivilegedTtb0Access" in tests
        and "PtwnncNormalizesNestedStage1FetchDeviceMemory" in tests
        and "SMMU-COMP-040/050/060 E0PD/PTWNNC behavior slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-e0pd-ptwnnc-behavior-verification-2026-05-11.md"),
        "Apollo TBU blocks unprivileged CD.E0PD stage-1 accesses and records PTWNNC normalization for nested stage-1 descriptor fetches through Device-mapped stage-2 memory",
    )
    add(
        "tbu:s2ptw-device-fetch-permission",
        "ARCH_STE_S2PTW = 1ULL << 54" in tbu
        and "arch_ste_s2ptw" in tbu
        and "arch_s2ptw_reject_device_fetch" in tbu
        and "m_arch_last_s2ptw_fault" in tbu
        and "STE.S2PTW blocks Device-mapped" in tbu
        and "S2ptwBlocksNestedCdFetchDeviceMemory" in tests
        and "S2ptwBlocksNestedTtFetchDeviceMemory" in tests
        and "ARCH_FAULT_PERMISSION" in tests
        and "SMMU-COMP-040/050/060 STE.S2PTW Device fetch permission slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-s2ptw-device-fetch-verification-2026-05-11.md"),
        "Apollo TBU terminates nested CD and stage-1 translation-table descriptor fetches through Device-mapped stage-2 pages when STE.S2PTW is set and reports stage-2 Permission faults",
    )
    add(
        "tbu:idr3-had-xnx-bbml2-behavior",
        "ARCH_IDR3_HAD = 1u << 2" in tbu
        and "ARCH_IDR3_XNX = 1u << 4" in tbu
        and "ARCH_IDR3_BBML_LEVEL_2 = 0x2u << ARCH_IDR3_BBML_SHIFT" in tbu
        and "ARCH_CD_HAD0 = 1ULL << 1" in tbu
        and "arch_cd_had_disables_hier_attrs" in tbu
        and "m_arch_last_had_disabled_hier_attrs" in tbu
        and "IDR3.XNX stage-2" in tbu
        and "execute-never permission fault" in tbu
        and "CdHadDisablesHierarchicalStage1Attrs" in tests
        and "Idr3XnxBlocksUnprivilegedStage2Execute" in tests
        and "APOLLO_SMMUV3_ARCH_IDR3		0x00007794" in linux_driver
        and "SMMU-COMP-020/040/050/060 IDR3 HAD/XNX/BBML2 behavior slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-idr3-had-xnx-bbml2-verification-2026-05-11.md"),
        "Apollo TBU reports mandatory v3.1/v3.2 IDR3 HAD/XNX/BBML2 discovery and component-tests bounded CD.HAD hierarchical-attribute disable plus stage-2 XNX execute-never permission behavior",
    )
    add(
        "tbu:bbml2-nt-block-descriptor",
        "ARCH_DESC_NT = 1ULL << 16" in tbu
        and "WALKER_DESC_NT = 1ULL << 16" in arch_core
        and "bool block_nt = false" in arch_core
        and "m_arch_last_bbml2_nt_ignored" in tbu
        and "IDR3.BBML level-2" in tbu
        and "ignores block descriptor nT" in tbu
        and "Idr3Bbml2IgnoresBlockNt" in tests
        and "ARCH_DESC_NT" in tests
        and "SMMU-COMP-040/050 BBML level-2 nT block descriptor slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-bbml2-nt-verification-2026-05-11.md"),
        "Apollo TBU explicitly models the SMMUv3.2 BBML level-2 rule that block-descriptor nT is ignored and does not create a modeled F_TLB_CONFLICT",
    )
    add(
        "tbu:httu-af-dirty-leaf-updates",
        "ARCH_IDR0_HTTU_ACCESS_DIRTY = 0x2u << ARCH_IDR0_HTTU_SHIFT" in tbu
        and "ARCH_DESC_DBM = 1ULL << 51" in tbu
        and "WALKER_DESC_DBM = 1ULL << 51" in arch_core
        and "ARCH_CD_HA = 1ULL << 43" in tbu
        and "ARCH_CD_HD = 1ULL << 42" in tbu
        and "ARCH_STE_S2HA = 1ULL << 56" in tbu
        and "ARCH_STE_S2HD = 1ULL << 55" in tbu
        and "arch_apply_httu_leaf_update" in tbu
        and "m_arch_last_httu_af_update" in tbu
        and "m_arch_last_httu_dirty_update" in tbu
        and "HTTU descriptor update" in tbu
        and "HttuStage1AccessAndDirtyUpdatesLeaf" in tests
        and "HttuStage2AccessAndDirtyUpdatesLeaf" in tests
        and "APOLLO_SMMUV3_ARCH_IDR0\t\t0x098db7cb" in linux_driver
        and "SMMU-COMP-040/050/060 HTTU AF/Dirty leaf-update slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-httu-af-dirty-verification-2026-05-11.md"),
        "Apollo TBU advertises bounded IDR0.HTTU AF/Dirty support and updates stage-1 CD.HA/HD plus stage-2 STE.S2HA/S2HD leaf descriptors instead of raising access/permission faults",
    )
    add(
        "tbu:httu-haft-table-updates",
        "ARCH_IDR0_HTTU_ACCESS_DIRTY_TABLE" in tbu
        and "ARCH_CD_HAFT = 1ULL << 3" in tbu
        and "ARCH_STE_S2HAFT = 1ULL << 59" in tbu
        and "arch_httu_table_access_enabled" in tbu
        and "arch_apply_httu_table_update" in tbu
        and "m_arch_last_httu_table_af_update" in tbu
        and "HTTU table descriptor AF update" in tbu
        and "HttuHaftStage1UpdatesTableAccessFlag" in tests
        and "HttuHaftStage2UpdatesTableAccessFlag" in tests
        and "ARCH_IDR0_HTTU_ACCESS_DIRTY_TABLE" in tests
        and "APOLLO_SMMUV3_ARCH_IDR0\t\t0x098db7cb" in linux_driver
        and "SMMU-COMP-040/050/060 HTTU HAFT table-descriptor slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-httu-haft-verification-2026-05-11.md"),
        "Apollo TBU advertises IDR0.HTTU==0b11 and updates stage-1 CD.HAFT plus stage-2 STE.S2HAFT table-descriptor Access flags before descriptor-step evaluation",
    )
    add(
        "tbu:idr4-implementation-defined-zero",
        "SMMUV3_IDR4 = 0x010" in tbu
        and "ARCH_IDR4 = 0x00000000" in tbu
        and "ARCH_S_IDR4 = 0x00000000" in tbu
        and "return ARCH_IDR4" in tbu
        and "return ARCH_S_IDR4" in tbu
        and "SMMUV3_IDR4" in tests
        and "ARCH_S_IDR4" in tests
        and "SMMU-COMP-020 IDR4 implementation-defined zero slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-idr4-implementation-defined-zero-verification-2026-05-11.md"),
        "Apollo TBU explicitly exposes Non-secure and Secure implementation-defined IDR4 registers as zero-valued RO discovery fields",
    )
    add(
        "tbu:iidr-aidr-register-slots",
        "SMMUV3_IIDR = 0x018" in tbu
        and "SMMUV3_AIDR = 0x01c" in tbu
        and "APOLLO_SMMUV3_AIDR\t\t0x01c" in linux_driver
        and "ARCH_IIDR" in tbu
        and "ARCH_AIDR" in tbu
        and "ArchitectedRegisterMmioSurface" in tests
        and "SMMU-COMP-020 IIDR/AIDR register-slot correction slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-iidr-aidr-register-slots-verification-2026-05-11.md"),
        "Apollo TBU exposes SMMU_IIDR at 0x0018 and SMMU_AIDR at 0x001c instead of aliasing AIDR onto IIDR",
    )
    add(
        "tbu:idr5-granule-oas-discovery",
        "ARCH_IDR5_OAS_48 = 0x5" in tbu
        and "ARCH_IDR5_GRAN4K = 1u << 4" in tbu
        and "ARCH_IDR5_GRAN16K = 1u << 5" in tbu
        and "ARCH_IDR5_GRAN64K = 1u << 6" in tbu
        and "ARCH_IDR5 = ARCH_IDR5_OAS_48" in tbu
        and "ARCH_DESC_OUTPUT_MASK = 0x0000fffffffff000ULL" in tbu
        and "ArchitectedRegisterMmioSurface" in tests
        and "ArchitectedWalkerGranuleBlockAndFaultMatrix" in tests
        and "SMMU-COMP-020/040/050 IDR5 granule/OAS discovery slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-idr5-granule-oas-verification-2026-05-11.md"),
        "Apollo TBU advertises IDR5 4K/16K/64K granules and 48-bit OAS to match its modeled walker/output-address aperture",
    )
    add(
        "tbu:tagged-invalidation",
        "FEATURE_ARCH_TAGGED_INVALIDATION" in tbu
        and "ARCH_CD_ASID_MASK" in tbu
        and "ARCH_CMDQ_TLBI_ASID_SHIFT" in tbu
        and "clear_ats_cache_asid" in tbu
        and "clear_ats_cache_page_vmid" in tbu
        and "clear_ats_cache_page_ssid" in tbu
        and "CmdqTaggedInvalidationHonorsAsidVmidAndSsid" in tests,
        "Apollo TBU component-tests ASID/VMID tagged TLBI and SSID-scoped ATC invalidation of modeled ATS entries",
    )
    add(
        "tbu:cmdq-additional-tlbi-opcodes",
        "ARCH_CMD_TLBI_EL3_ALL = 0x18" in tbu
        and "ARCH_CMD_TLBI_EL3_VA = 0x1a" in tbu
        and "ARCH_CMD_TLBI_EL2_ALL = 0x20" in tbu
        and "ARCH_CMD_TLBI_EL2_ASID = 0x21" in tbu
        and "ARCH_CMD_TLBI_EL2_VA = 0x22" in tbu
        and "ARCH_CMD_TLBI_EL2_VAA = 0x23" in tbu
        and "ARCH_CMD_TLBI_S12_VMALL = 0x28" in tbu
        and "ARCH_CMD_TLBI_S2_IPA = 0x2a" in tbu
        and "ARCH_CMD_TLBI_NSNH_ALL = 0x30" in tbu
        and "cmdq_opcode_is_address_tlbi" in tbu
        and "TLBI_NSNH_ALL" in tbu
        and "TLBI_EL2_ASID" in tbu
        and "TLBI_EL2_VAA" in tbu
        and "TLBI_S12_VMALL" in tbu
        and "TLBI_S2_IPA" in tbu
        and "clear_ats_cache_vmid" in tbu
        and "clear_ats_cache_range_vmid" in tbu
        and "CmdqAdditionalTlbiOpcodesInvalidateModeledAts" in tests,
        "Apollo TBU component-tests modeled additional TLBI opcode coverage for NSNH/EL2/EL3/S12/S2 command forms and their ASID/VMID/range ATS invalidation side effects",
    )
    add(
        "tbu:cmdq-tlbi-nsnh-scope",
        "ARCH_TLBI_REGIME_NSNH" in tbu
        and "ARCH_TLBI_REGIME_EL2" in tbu
        and "ats_tlbi_regime_is_nsnh" in tbu
        and "clear_ats_cache_nsnh" in tbu
        and "CmdqTlbiNsnhAllPreservesEl2RegimeEntries" in tests,
        "Apollo TBU models TLBI_NSNH_ALL as a Non-secure Non-Hyp invalidation scope and preserves explicitly tagged EL2-regime ATS entries",
    )
    add(
        "tbu:secure-tlbi-opcodes",
        "ARCH_CMD_TLBI_S_EL2_ALL = 0x50" in tbu
        and "ARCH_CMD_TLBI_S_EL2_ASID = 0x51" in tbu
        and "ARCH_CMD_TLBI_S_EL2_VA = 0x52" in tbu
        and "ARCH_CMD_TLBI_S_EL2_VAA = 0x53" in tbu
        and "ARCH_CMD_TLBI_S_S12_VMALL = 0x58" in tbu
        and "ARCH_CMD_TLBI_S_S2_IPA = 0x5a" in tbu
        and "ARCH_CMD_TLBI_SNH_ALL = 0x60" in tbu
        and "cmdq_opcode_is_secure_tlbi" in tbu
        and "nonsecure-secure-tlbi" in tbu
        and "TLBI_S_EL2_ASID" in tbu
        and "TLBI_S_S2_IPA" in tbu
        and "TLBI_SNH_ALL" in tbu
        and "SecureOnlyTlbiOpcodesRequireSecureCmdqAndTargetSecureState" in tests,
        "Apollo TBU component-tests Secure-only TLBI opcode coverage for S-EL2/S-S12/S-S2/SNH commands, Secure CMDQ targeting, and Non-secure CMDQ CERROR_ILL rejection",
    )
    add(
        "tbu:cmdq-tlbi-range-invalidation",
        "ARCH_CMDQ_RANGE_TG_4K" in tbu
        and "cmdq_tlbi_range_bytes" in tbu
        and "cmdq_tlbi_range_encoding_reserved" in tbu
        and "tlbi-range-reserved" in tbu
        and "clear_ats_cache_range_asid" in tbu
        and "clear_ats_cache_range_vmid" in tbu
        and "m_arch_last_cmd_range_bytes" in tbu
        and "CmdqTlbiRangeInvalidatesModeledAtsSpan" in tests
        and "CmdqTlbiRangeReservedEncodingIsIllegal" in tests
        and "ARCH_CMDQ_RANGE_NUM_SHIFT" in tests
        and "ARCH_CMDQ_RANGE_TG_SHIFT" in tests,
        "Apollo TBU decodes modeled TLBI_NH_VA/TLBI_NH_VAA range fields, rejects reserved NUM/SCALE/TG encodings with CERROR_ILL, and invalidates ATS/TLB cache entries across the selected 4K/16K/64K span instead of only the base page",
    )
    add(
        "tbu:cmdq-tlbi-ttl-leaf-hints",
        "ARCH_CMDQ_TTL_SHIFT" in tbu
        and "ARCH_CMDQ_LEAF" in tbu
        and "cmdq_tlbi_ttl" in tbu
        and "cmdq_tlbi_leaf" in tbu
        and "m_arch_last_cmd_ttl" in tbu
        and "m_arch_last_cmd_leaf" in tbu
        and "m_arch_last_cmd_tg" in tbu
        and "CmdqTlbiTtlLeafHintsFollowRangeTg" in tests,
        "Apollo TBU decodes modeled TLBI TTL/Leaf hints, records TG/TTL/Leaf state, and suppresses TTL hint accounting when TG==0",
    )
    add(
        "tbu:cmdq-tlbi-ttl-leaf-level-aware",
        "leaf_level" in tbu
        and "granule_bytes" in tbu
        and "ats_tlbi_level_matches" in tbu
        and "m_arch_last_cmd_table_invalidated" in tbu
        and "m_arch_cmd_table_invalidations" in tbu
        and "table-invalidated" in tbu
        and "apollo_smmu_tbu::ARCH_SECURITY_NONSECURE, 2," in tests
        and "apollo_smmu_tbu::ARCH_SECURITY_NONSECURE, 3," in tests
        and "m_arch_last_cmd_table_invalidated" in tests
        and "m_arch_cmd_table_invalidations" in tests,
        "Apollo TBU applies modeled TLBI TTL/TG leaf-level filtering to cached ATS translations and records Leaf=0 table-walk cache invalidation accounting",
    )
    add(
        "tbu:endpoint-substream-id",
        "FEATURE_ENDPOINT_SUBSTREAM_ID" in tbu
        and "transaction_substream_id" in tbu
        and "substream_id_valid" in stream_ext
        and "CAP_ENDPOINT_PASID" in dma
        and "substream_id = 0x3" in platform
        and "EndpointSubstreamIdTagsAtsAndFaultEvents" in tests,
        "Apollo DMA endpoint propagates PASID/SSID through the TLM extension and Apollo TBU tags ATS/event records with endpoint substream IDs",
    )
    add(
        "tbu:unsupported-security-state-gate",
        "security_state" in stream_ext
        and "transaction_security_state" in tbu
        and "ARCH_SECURITY_NONSECURE" in tbu
        and "ARCH_SECURITY_SECURE" in tbu
        and "ARCH_SECURITY_REALM" in tbu
        and "ARCH_SECURITY_ROOT" in tbu
        and "arch_security_state_supported" in tbu
        and "security_state == ARCH_SECURITY_SECURE" in tbu
        and "security_state == ARCH_SECURITY_REALM" in tbu
        and "security_state == ARCH_SECURITY_ROOT" in tbu
        and "transport_dbg" in tbu
        and "REG_ARCH_SECURITY_STATUS" in tbu
        and "stream_dbg_read32_security" in tests
        and "supported_states" in tests
        and "unsupported_states" in tests
        and "SecureRealmRootEndpointAcceptedInvalidRejectedBeforeTranslation" in tests,
        "Apollo TBU accepts modeled Secure, Realm, and Root endpoint transactions on the existing translation path and explicitly rejects invalid security-state transactions before translation",
    )
    add(
        "tbu:realm-root-endpoint-acceptance",
        "security_state == ARCH_SECURITY_REALM" in tbu
        and "supported_states" in tests
        and "apollo_smmu_tbu::ARCH_SECURITY_REALM" in tests
        and "apollo_smmu_tbu::ARCH_SECURITY_ROOT" in tests
        and "EXPECT_EQ(0u, m_tbu.m_arch_eventq_realm_records)" in tests
        and "EXPECT_EQ(1u, m_tbu.m_arch_eventq_root_records)" in tests
        and "SecureRealmRootEndpointAcceptedInvalidRejectedBeforeTranslation" in tests,
        "Apollo TBU accepts modeled Realm and Root endpoint data/debug transactions on the existing translation path while keeping complete RME/GPT/GPC behavior out of scope",
    )
    add(
        "tbu:security-strtab-bank-selection",
        "arch_security_strtab_bank" in tbu
        and "m_arch_security_strtab_banks" in tbu
        and "configure_arch_security_strtab_bank" in tbu
        and "arch_security_strtab_uses_bank" in tbu
        and "arch_active_stream_table_configured" in tbu
        and "SecureStreamTableBankSelectsSecureSte" in tests
        and "secure_strtab_base" in tests
        and "EXPECT_EQ(secure_ste, m_tbu.m_arch_last_ste)" in tests
        and "EXPECT_EQ(nonsecure_ste, m_tbu.m_arch_last_ste)" in tests,
        "Apollo TBU can select a configured Secure stream-table bank for modeled Secure descriptor probes while preserving the Non-secure STRTAB path",
    )
    add(
        "tbu:secure-register-bank-strtab-cmdq-eventq",
        "SMMUV3_SECURE_PAGE = 0x8000" in tbu
        and "SMMUV3_APERTURE_SIZE = 0x40000" in arch_core
        and "ARCH_S_IDR1_SECURE_IMPL" in tbu
        and "ARCH_S_IDR1_SEL2" in tbu
        and "read_smmuv3_secure_reg" in tbu
        and "write_smmuv3_secure_reg" in tbu
        and "secure_strtab_bank()" in tbu
        and "secure_eventq_bank()" in tbu
        and "m_arch_secure_cmdq" in tbu
        and "reg_s_write64" in tests
        and "SecureRegisterBankConfiguresStrtabCmdqAndEventq" in tests
        and "smmu_s_reg(apollo_smmu_tbu::SMMUV3_STRTAB_BASE_CFG)" in tests
        and "smmu_s_reg(apollo_smmu_tbu::SMMUV3_EVENTQ_PROD)" in tests
        and "size=0x10000" in platform,
        "Apollo TBU exposes a guest-visible SMMU_S_* Secure register page with independent Secure STRTAB, CMDQ, and EVENTQ bank state while preserving Non-secure register state",
    )
    add(
        "tbu:secure-cmdq-memory-backed-lifecycle",
        "process_secure_cmdq" in tbu
        and "arch_secure_cmdq_enabled" in tbu
        and "read_secure_cmdq_cons" in tbu
        and "write_secure_cmdq_cons" in tbu
        and "set_secure_cmdq_cerror" in tbu
        and "m_arch_secure_cmdq_cerror" in tbu
        and "architected S_CMDQ op" in tbu
        and "handle_cmdq_atc_inv(word0, word1)" in tbu
        and "SecureCmdqProducerConsumesMemoryBackedCommands" in tests
        and "smmu_s_reg(apollo_smmu_tbu::SMMUV3_CMDQ_PROD)" in tests
        and "EXPECT_FALSE(m_tbu.ats_lookup(stream_id, iova_page))" in tests
        and "EXPECT_EQ(1u, m_tbu.m_arch_cmd_atc_invs)" in tests,
        "Apollo TBU fetches and consumes memory-backed SMMU_S_CMDQ entries when Secure CR0 enables the queue, reusing modeled invalidation and sync command handlers while keeping Non-secure CMDQ state isolated",
    )
    add(
        "tbu:secure-cmdq-ssec-cfgi-routing",
        "ARCH_CMDQ_SSEC" in tbu
        and "cmdq_ssec" in tbu
        and "secure_cmdq_ssec_state" in tbu
        and "m_arch_last_cmd_security_state" in tbu
        and "clear_config_cache_security_state" in tbu
        and "handle_cmdq_cfgi(word0, false, command_security_state)" in tbu
        and "nonsecure-cmdq-ssec" in tbu
        and "SecureCmdqSsecCfgiTargetsSelectedSecurityState" in tests
        and "NonSecureCmdqSsecCfgiIsIllegal" in tests
        and "m_tbu.m_arch_last_cmd_ssec" in tests,
        "Apollo TBU decodes the architected SSec bit for modeled CFGI commands, lets S_CMDQ target Secure versus Non-secure configuration-cache state, and reports CERROR_ILL when Non-secure CMDQ uses SSec=1",
    )
    add(
        "tbu:secure-cmdq-ssec-tlbi-atc-routing",
        "ARCH_SECURITY_ANY" in tbu
        and "ats_security_matches" in tbu
        and "handle_cmdq_tlbi(opcode, word0, word1,\n                                  command_security_state)" in tbu
        and "handle_cmdq_atc_inv(word0, word1, command_security_state)" in tbu
        and "case ARCH_CMD_TLBI_NH_VA:" in tbu
        and "case ARCH_CMD_ATC_INV:" in tbu
        and "NonSecureCmdqSsecTlbiAtcAreIllegal" in tests
        and "SecureCmdqSsecTlbiAtcTargetsSelectedSecurityState" in tests
        and "ARCH_SECURITY_SECURE)" in tests,
        "Apollo TBU extends SSec routing to modeled TLBI_NH_* and ATC_INV commands, tags ATS/TLB cache entries by security state, lets S_CMDQ target Secure versus Non-secure ATS state, and rejects SSec=1 on Non-secure TLBI/ATC commands",
    )
    add(
        "tbu:secure-cmdq-atc-inv-sync-cerror-recovery",
        "set_secure_cmdq_cerror(ARCH_CMDQ_CERROR_ATC_INV_SYNC" in tbu
        and "secure-atc-inv-sync" in tbu
        and "m_arch_atc_inv_sync_error_pending" in tbu
        and "SecureCmdqAtcInvSyncCerrorPausesAndRecovers" in tests
        and "m_tbu.m_arch_atc_inv_sync_force_fail_count = 2" in tests
        and "smmu_s_reg(apollo_smmu_tbu::SMMUV3_CMDQ_CONS), 3" in tests
        and "EXPECT_EQ(4u, reg_read32(smmu_s_reg(apollo_smmu_tbu::SMMUV3_CMDQ_CONS)))" in tests,
        "Apollo TBU reports failed Secure ATC_INV completion on the following S_CMD_SYNC as S_CMDQ_CONS.CERROR_ATC_INV_SYNC, pauses the Secure CMDQ, and recovers after software skips the failed sync with S_CMDQ_CONS",
    )
    add(
        "tbu:secure-cmd-sync-msi-ordering",
        "emit_secure_cmdq_sync_msi" in tbu
        and "set_secure_gerror" in tbu
        and "ack_secure_gerror" in tbu
        and "read_secure_gerror" in tbu
        and "set_arch_irq_status(ARCH_IRQ_CMDQ_SYNC)" in tbu
        and "ARCH_GERROR_MSI_CMDQ_ABORT" in tbu
        and "SecureCmdSyncMsiWriteAndAbortAreReported" in tests
        and "reg_read_secure_gerror_active" in tests
        and "EXPECT_EQ(1u, m_tbu.m_arch_msi_writes)" in tests
        and "EXPECT_EQ(1u, m_tbu.m_arch_msi_aborts)" in tests
        and "smmu_s_reg(apollo_smmu_tbu::SMMUV3_GERRORN)" in tests,
        "Apollo TBU models Secure CMD_SYNC CS=IRQ MSI success/abort ordering, raises Secure MSI_CMDQ_ABORT through S_GERROR, and acknowledges it through S_GERRORN without touching Non-secure GERROR",
    )
    add(
        "tbu:secure-cmd-sync-irq-bank-route",
        "m_arch_cmdq_sync_irq_security_state" in tbu
        and "set_arch_irq_status_for_security_state(ARCH_IRQ_CMDQ_SYNC" in tbu
        and "m_arch_secure_irq_ctrl" in tbu
        and "SecureCmdSyncIrqUsesSecureCtrlBank" in tests
        and "smmu_s_reg(apollo_smmu_tbu::SMMUV3_IRQ_CTRL)" in tests
        and "ARCH_SECURITY_SECURE" in tests
        and "m_tbu.m_arch_irq_lines" in tests,
        "Apollo TBU routes Secure S_CMD_SYNC completion IRQ visibility through S_IRQ_CTRL/S_IRQ_CTRLACK instead of the Non-secure IRQ_CTRL bank",
    )
    add(
        "tbu:secure-eventq-msi-bank-route",
        "m_arch_eventq_irq_security_state" in tbu
        and "m_arch_gerror_irq_security_state" in tbu
        and "arch_secure_irq_cfg_writable" in tbu
        and "emit_secure_arch_msi" in tbu
        and "m_arch_secure_eventq_msi" in tbu
        and "set_arch_irq_status_for_security_state(ARCH_IRQ_EVENTQ" in tbu
        and "set_secure_gerror(abort_gerror)" in tbu
        and "SecureEventqMsiAndAbortUseSecureBank" in tests
        and "smmu_s_reg(apollo_smmu_tbu::SMMUV3_EVENTQ_IRQ_CFG1)" in tests
        and "ARCH_GERROR_MSI_EVENTQ_ABORT" in tests
        and "reg_read_secure_gerror_active" in tests,
        "Apollo TBU routes Secure EVENTQ IRQ/MSI notification through S_EVENTQ_IRQ_CFG and reports Secure EVENTQ MSI aborts through S_GERROR while preserving Non-secure EVENTQ/GERROR isolation",
    )
    add(
        "tbu:secure-priq-msi-bank-route",
        "m_arch_secure_priq" in tbu
        and "m_arch_priq_irq_security_state" in tbu
        and "m_arch_secure_priq_msi" in tbu
        and "arch_priq_for_security_state" in tbu
        and "arch_priq_enabled_for_security_state" in tbu
        and "ARCH_GERROR_MSI_PRIQ_ABORT" in tbu
        and "SecurePriqMsiAndAbortUseSecureBank" in tests
        and "smmu_s_reg(apollo_smmu_tbu::SMMUV3_PRIQ_IRQ_CFG1)" in tests
        and "ARCH_GERROR_MSI_PRIQ_ABORT" in tests
        and "m_tbu.m_arch_secure_priq.prod" in tests,
        "Apollo TBU routes Secure PRIQ records and IRQ/MSI notification through S_PRIQ/S_PRIQ_IRQ_CFG and reports Secure PRIQ MSI aborts through S_GERROR while preserving Non-secure PRIQ/GERROR isolation",
    )
    add(
        "tbu:secure-gerror-msi-bank-route",
        "m_arch_gerror_irq_security_state" in tbu
        and "emit_secure_arch_msi" in tbu
        and "m_arch_secure_gerror_msi" in tbu
        and "ARCH_GERROR_MSI_GERROR_ABORT" in tbu
        and "set_arch_irq_status_for_security_state(ARCH_IRQ_GERROR" in tbu
        and "SecureGerrorMsiAndAbortUseSecureBank" in tests
        and "smmu_s_reg(apollo_smmu_tbu::SMMUV3_GERROR_IRQ_CFG1)" in tests
        and "ARCH_GERROR_MSI_GERROR_ABORT" in tests
        and "reg_read_secure_gerror_active" in tests,
        "Apollo TBU routes Secure GERROR IRQ/MSI notification through S_GERROR_IRQ_CFG and reports failed Secure GERROR MSI writes through S_GERROR.MSI_GERROR_ABORT while preserving Non-secure GERROR isolation",
    )
    add(
        "tbu:secure-s2ttb-nscfg-selection",
        "ARCH_STE_NSCFG_SHIFT" in tbu
        and "ARCH_STE_S_S2TTB_WORD_OFFSET" in tbu
        and "select_arch_stage2_table_base" in tbu
        and "m_arch_last_s2_secure_ipa" in tbu
        and "SecureStage2OnlyUsesSS2TtbWhenNscfgSecure" in tests
        and "ARCH_STE_NSCFG_SECURE" in tests
        and "EXPECT_EQ(secure_s2ttb, m_tbu.m_arch_s2ttb)" in tests
        and "EXPECT_EQ(ns_s2ttb, m_tbu.m_arch_s2ttb)" in tests,
        "Apollo TBU models Secure stage-2-only NSCFG selection between S2TTB and S_S2TTB for configured Secure stream-table probes",
    )
    add(
        "tbu:secure-stage1-nsipa-selection",
        "ARCH_DESC_NS" in tbu
        and "ARCH_DESC_NSTABLE" in tbu
        and "ARCH_CD_NSCFG0" in tbu
        and "m_arch_last_s1_output_nonsecure_ipa" in tbu
        and "m_arch_last_s1_table_walk_nonsecure" in tbu
        and "select_arch_stage2_table_base(stream_id, ste_pa, ste1, ste2" in tbu
        and "SecureNestedStage1OutputNsSelectsS2Ttb" in tests
        and "EXPECT_FALSE(m_tbu.m_arch_last_s1_output_nonsecure_ipa)" in tests
        and "EXPECT_TRUE(m_tbu.m_arch_last_s1_output_nonsecure_ipa)" in tests
        and "EXPECT_EQ(secure_s2ttb, m_tbu.m_arch_s2ttb)" in tests
        and "EXPECT_EQ(ns_s2ttb, m_tbu.m_arch_s2ttb)" in tests,
        "Apollo TBU derives Secure nested stage-2 IPA-space selection from modeled stage-1 CD.NSCFG0 and leaf NS output, selecting S_S2TTB for Secure IPA and S2TTB for Non-secure IPA",
    )
    add(
        "tbu:secure-stage1-ttfetch-s2ttb-selection",
        "read_arch_ste_s_s2ttb" in tbu
        and "m_arch_last_s1_tt_fetch_secure_ipa" in tbu
        and "m_arch_last_s1_tt_fetch_s2ttb" in tbu
        and "architectural nested stage-1 TT fetch stage-2 walk" in tbu
        and "fetch_secure_ipa ? secure_s2ttb : s2ttb" in tbu
        and "SecureNestedStage1OutputNsSelectsS2Ttb" in tests
        and "EXPECT_TRUE(m_tbu.m_arch_last_s1_tt_fetch_secure_ipa)" in tests
        and "EXPECT_FALSE(m_tbu.m_arch_last_s1_tt_fetch_secure_ipa)" in tests
        and "EXPECT_EQ(secure_s2ttb, m_tbu.m_arch_last_s1_tt_fetch_s2ttb)" in tests
        and "EXPECT_EQ(ns_s2ttb, m_tbu.m_arch_last_s1_tt_fetch_s2ttb)" in tests,
        "Apollo TBU selects S_S2TTB versus S2TTB for nested Secure stage-1 translation-table descriptor fetches based on CD.NSCFG0/NSTable-derived IPA space",
    )
    add(
        "tbu:security-eventq-routing",
        "ARCH_SECURITY_EVENTQ_STATE_SHIFT" in tbu
        and "m_arch_last_event_security_state" in tbu
        and "m_arch_eventq_secure_records" in tbu
        and "m_arch_eventq_realm_records" in tbu
        and "m_arch_eventq_root_records" in tbu
        and "record_arch_eventq_security_route" in tbu
        and "arch_security_eventq_count" in tbu
        and "m_arch_last_event_security_state" in tests
        and "arch_security_eventq_count(route_state)" in tests,
        "Apollo TBU tags modeled EVENTQ records with the active security state and accounts Secure faults plus invalid-state events routed by masked Root event-state accounting",
    )
    add(
        "tbu:security-stall-event-buffer-route",
        "arch_stall_event_buffer_record" in tbu
        and "buffer_stall_event_record(words, m_arch_last_security_state)" in tbu
        and "record_arch_eventq_security_route(buffered.security_state, buffered.words" in tbu
        and "FaultReplayFullEventQueueBuffersAndRedrivesStall" in tests
        and "m_arch_last_security_state = apollo_smmu_tbu::ARCH_SECURITY_REALM" in tests
        and "arch_security_eventq_count(\n                      apollo_smmu_tbu::ARCH_SECURITY_REALM)" in tests,
        "Apollo TBU preserves the original security-state route for buffered stalled EVENTQ records and accounts the redriven record against that state",
    )
    add(
        "tbu:security-eventq-bank-mirror",
        "arch_security_eventq_bank" in tbu
        and "m_arch_security_eventq_banks" in tbu
        and "arch_security_eventq_bank_state" in tbu
        and "bank.last_record = words" in tbu
        and "bank.last_guest_record_addr = guest_record_addr" in tbu
        and "arch_queue_next_record_addr" in tbu
        and "arch_security_eventq_bank_state(state)" in tests
        and "realm_bank.last_guest_record_addr" in tests,
        "Apollo TBU mirrors committed EVENTQ records into per-security-state logical banks with record words, guest address, and producer/consumer snapshots",
    )
    add(
        "tbu:security-eventq-separate-bank-route",
        "arch_security_eventq_uses_separate_bank" in tbu
        and "arch_eventq_for_security_state" in tbu
        and "configure_arch_security_eventq_bank" in tbu
        and "queue_configured" in tbu
        and "routed_to_separate_queue" in tbu
        and "SecureEventsUseConfiguredEventqBank" in tests
        and "secure_eventq_base" in tests
        and "EXPECT_EQ(0u, m_tbu.m_eventq.prod)" in tests
        and "EXPECT_EQ(1u, bank.queue.prod)" in tests,
        "Apollo TBU can route modeled Secure EVENTQ records into a separately configured per-security-state Event queue bank instead of the Non-secure EVENTQ",
    )
    add(
        "tbu:cd-table-ssid-index",
        "FEATURE_ARCH_CD_TABLE_INDEX" in tbu
        and "REG_ARCH_SSID" in tbu
        and "REG_ARCH_CD_DETAIL" in tbu
        and "ARCH_STE_S1CDMAX_SHIFT" in tbu
        and "ARCH_STE_S1DSS_MASK" in tbu
        and "ARCH_STE_S1DSS_BYPASS" in tbu
        and "m_arch_last_cd_bypass" in tbu
        and "no-SSID context descriptor bypass" in tbu
        and "architectural nested CD fetch stage-2 walk" in tbu
        and "architectural nested L1CD fetch stage-2 walk" in tbu
        and "stage2_translate_descriptor_fetch" in tbu
        and "architectural nested S1DSS bypass stage-2 walk" in tbu
        and "ARCH_STE_S1FMT_64K_L2" in tbu
        and "arch_cd_address" in tbu
        and "ArchitectedContextDescriptorTableIndexesSelectedSsid" in tests
        and "ARCH_STE_S1DSS_TERMINATE" in tests
        and "ARCH_STE_S1DSS_BYPASS" in tests
        and "bypass_s2ttb" in tests,
        "Apollo TBU component-tests S1CDMax-bounded SSID selection plus no-substream S1DSS terminate/bypass through linear and 64K L2 context descriptor tables, including nested CD/L1CD fetch, nested TT descriptor-fetch, and S1DSS bypass stage-2 walks",
    )
    add(
        "tbu:ste-cd-reserved-encoding",
        "FEATURE_ARCH_RESERVED_ENCODING_CHECKS" in tbu
        and "ARCH_STE0_MODELED_MASK" in tbu
        and "arch_reject_reserved_ste" in tbu
        and "illegal STE.Config encoding" in tbu
        and "reserved STE encoding" in tbu
        and "reserved CD encoding" in tbu
        and "reserved CD L1 encoding" in tbu
        and "illegal S1DSS encoding" in tbu
        and "ArchitectedSteCdReservedEncodingFaults" in tests,
        "Apollo TBU component-tests modeled STE/CD reserved-bit and illegal-encoding faults",
    )
    add(
        "tbu:architected-strtab-stream-selection",
        "REG_ARCH_STREAM_ID" in tbu
        and "ARCH_STRTAB_FMT_2LVL" in tbu
        and "arch_ste_address" in tbu
        and "ARCH_FAULT_BAD_STREAM_ID" in tbu
        and "ArchitectedLinearStreamTableUsesSelectedStreamId" in tests
        and "ArchitectedTwoLevelStreamTableSelectsL2Ste" in tests,
        "Apollo TBU decodes selected StreamID through bounded linear/2-level STRTAB and component-tests invalid SID replay",
    )
    add(
        "tbu:walker-granule-stage-matrix",
        "ARCH_GRANULE_16K" in tbu
        and "ARCH_GRANULE_64K" in tbu
        and "ARCH_DESC_BLOCK" in tbu
        and "ARCH_FAULT_PERMISSION" in tbu
        and "ARCH_STE_CFG_S2_TRANS" in tbu
        and "ARCH_STE_CFG_NESTED" in tbu
        and "architectural nested CD fetch stage-2 walk" in tbu
        and "architectural nested L1CD fetch stage-2 walk" in tbu
        and "stage2_translate_descriptor_fetch" in tbu
        and "architectural nested S1DSS bypass stage-2 walk" in tbu
        and "ArchitectedWalkerGranuleBlockAndFaultMatrix" in tests
        and "ArchitectedWalkerStage2AndNestedMatrix" in tests
        and "ArchitectedNestedL1CdFetchStage2Walks" in tests
        and "bypass_s2ttb" in tests,
        "Apollo TBU component-tests selected granule, block/page, AF/permission, stage-2, nested CD/L1CD/TT-fetch/S2, nested, and nested S1DSS-bypass/S2 walker vectors",
    )
    add(
        "tbu:ats-pri-protocol-matrix",
        "REG_ARCH_ATS_DETAIL" in tbu
        and "ARCH_ATS_RESP_UR" in tbu
        and "ARCH_ATS_RESP_CA" in tbu
        and "complete_prg" in tbu
        and "push_pri_protocol_record" in tbu
        and "ArchitectedAtsPriProtocolMatrixAndPriResp" in tests
        and "CmdPriRespUnknownPrgIsAccounted" in tests,
        "Apollo TBU distinguishes ATS success/UR/CA outcomes and component-tests PRG-tagged PRI response handling",
    )
    add(
        "tbu:pri-ppr-stop-marker",
        "ARCH_PRIQ_PPR_SSV" in tbu
        and "ARCH_PRIQ_PPR_LAST" in tbu
        and "ARCH_PRIQ_PPR_SSID_SHIFT" in tbu
        and "arch_priq_ppr_word0" in tbu
        and "arch_priq_ppr_word3" in tbu
        and "arch_priq_ppr_is_stop_marker" in tbu
        and "architected PRI Stop PASID Marker" in tbu
        and "architected PRI non-last PPR" in tbu
        and "m_arch_pri_discarded_nonlast" in tbu
        and "PriProtocolPprFieldsStopMarkerAndNonLastDiscard" in tests
        and "SMMU-COMP-060 PRI PPR/Stop Marker slice" in read_text(repo / "doc/verification/qbox-smmuv3-pri-ppr-stop-marker-verification-2026-05-11.md"),
        "Apollo TBU models PRI PPR SSV/Last/R/W/X/Priv metadata, Stop PASID Marker no-response handling, and non-last overflow discard without auto-response",
    )
    add(
        "tbu:pri-auto-response",
        "FEATURE_ARCH_PRI_AUTO_RESPONSE" in tbu
        and "ARCH_PRI_RESP_FAILURE" in tbu
        and "record_pri_auto_response" in tbu
        and "arch_pri_overflow_auto_response" in tbu
        and "arch_pri_secure_stream_auto_failure" in tbu
        and "record_pri_ppar_lookup_fault" in tbu
        and "last_pri_response_stream_id" in tbu
        and "ARCH_STE_PPAR" in tbu
        and "m_arch_last_auto_response_ssv" in tbu
        and "arch_priq_abort_active" in tbu
        and "PriProtocolAutoRespondsOnOverflowDisabledAndAbort" in tests
        and "PriProtocolOverflowUsesStePparForPasidAutoResponse" in tests
        and "PriProtocolSecureStreamAutoFailsWithoutQueueing" in tests
        and "PriProtocolPparLookupFaultHonorsRecCfgAts" in tests
        and "PriProtocolPparBadStreamIdHonorsRecInvsid" in tests
        and "CmdPriRespRequiresHeadPrgOrdering" in tests
        and "CmdPriRespHonorsStreamIdQualifier" in tests
        and "CmdPriRespHonorsSsidQualifier" in tests
        and "APOLLO_TBU_FEATURE_ARCH_PRI_AUTO_RESPONSE" in linux_driver,
        "Apollo TBU auto-responds with PRI success for no-PASID Last PPR overflow, matches CMD_PRI_RESP against the head pending PRG plus optional StreamID/PASID qualifier, uses STE.PPAR for PASID-prefixed overflow responses, records REC_CFG_ATS/RECINVSID-gated STE.PPAR lookup faults, and fails Secure-stream, disabled PRIQ, and active PRIQ_ABT_ERR cases",
    )
    add(
        "tbu:pri-response-head-ordered-exact-prg",
        "last_pri_response_stream_id" in tbu
        and "last_pri_response_code" in tbu
        and "last_pri_response_ats_status" in tbu
        and "last_pri_response_unknown" in tbu
        and "last_pri_response_stream_mismatch" in tbu
        and "last_pri_response_ssid_mismatch" in tbu
        and "last_pri_response_order_mismatch" in tbu
        and "last_pri_response_head_prg" in tbu
        and "advance_priq_cons_after_response" in tbu
        and "CmdPriRespAdvancesPriqConsForHeadRequest" in tests
        and "arch_pri_response_valid" in tbu
        and "CmdPriRespRequiresHeadPrgOrdering" in tests
        and "CmdPriRespHonorsStreamIdQualifier" in tests
        and "CmdPriRespHonorsSsidQualifier" in tests
        and "CmdPriRespReservedResponseSetsCerrorIll" in tests
        and "SMMU-COMP-060 PRI response head-ordered exact-PRG slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-pri-response-head-order-verification-2026-05-11.md"),
        "Apollo TBU records CMD_PRI_RESP completion metadata, retires only the head pending PRI response by exact PRG plus optional StreamID/PASID qualifier, advances PRIQ_CONS for a retired head PPR, and rejects reserved PRI response codes with CERROR_ILL",
    )
    add(
        "tbu:pri-response-smmuen-disabled-noop",
        "arch_cmdq_enabled" in tbu
        and "ARCH_CR0_SMMUEN | ARCH_CR0_CMDQEN" in tbu
        and "CmdPriRespIgnoredWhenSmmuenDisabled" in tests
        and "SMMU-COMP-060 PRI response SMMUEN-disabled no-op slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-pri-response-smmuen-disabled-verification-2026-05-11.md"),
        "Apollo TBU component-tests that CMD_PRI_RESP is silently ignored while SMMUEN is clear, preserving pending PRG state, PRIQ_CONS, and CERROR state",
    )
    add(
        "tbu:pri-response-streamid-qualifier",
        "last_pri_response_stream_mismatch" in tbu
        and "last_pri_response_cmd_stream_id" in tbu
        and "cmdq_stream_id(word0) != 0" in tbu
        and "CmdPriRespHonorsStreamIdQualifier" in tests
        and "SMMU-COMP-060 PRI response StreamID qualifier slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-pri-response-streamid-qualifier-verification-2026-05-11.md"),
        "Apollo TBU honors a modeled StreamID qualifier on CMD_PRI_RESP before clearing the head pending PRG",
    )
    add(
        "tbu:pri-response-ssid-qualifier",
        "last_pri_response_ssid_mismatch" in tbu
        and "last_pri_response_cmd_ssid" in tbu
        and "last_pri_response_ssid_valid" in tbu
        and "cmdq_ssid_valid(word0)" in tbu
        and "CmdPriRespHonorsSsidQualifier" in tests
        and "SMMU-COMP-060 PRI response SSID qualifier slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-pri-response-ssid-qualifier-verification-2026-05-11.md"),
        "Apollo TBU honors a modeled PASID/SSID qualifier on CMD_PRI_RESP before clearing the head pending PRG",
    )
    add(
        "tbu:pri-response-reserved-code",
        "arch_pri_response_valid" in tbu
        and "pri-resp-reserved-response" in tbu
        and "secure-pri-resp-reserved-response" in tbu
        and "CmdPriRespReservedResponseSetsCerrorIll" in tests
        and "SecureCmdPriRespReservedResponseSetsCerrorIll" in tests
        and "SMMU-COMP-060 PRI response reserved-code slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-pri-response-reserved-code-verification-2026-05-11.md")
        and "SMMU-COMP-060 Secure PRI response reserved-code slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-secure-pri-response-reserved-code-verification-2026-05-11.md"),
        "Apollo TBU rejects Non-secure and Secure CMD_PRI_RESP reserved response codes with CERROR_ILL without clearing the pending PRG",
    )
    add(
        "tbu:secure-pri-response-nonsecure-stream",
        "secure_cmdq_command_security_state" in tbu
        and "opcode == ARCH_CMD_PRI_RESP" in tbu
        and "SecureCmdPriRespIgnoresSsecAndTargetsNonSecure" in tests
        and "SMMU-COMP-060 Secure CMD_PRI_RESP Non-secure StreamID slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-secure-pri-response-nonsecure-stream-verification-2026-05-11.md"),
        "Apollo TBU treats an accepted Secure CMDQ CMD_PRI_RESP StreamID as Non-secure and ignores the RES0 SSec bit for PRI responses",
    )
    add(
        "tbu:pri-ppr-ignores-atschk-eats",
        "Incoming PRI Page Request messages are a PRI-side protocol input" in tbu
        and "not gated by CR0.ATSCHK" in tbu
        and "only consult STE.PPAR on the" in tbu
        and "PriProtocolPprIgnoresAtschkAndSteEats" in tests
        and "ARCH_CR0_ALL_QUEUES & ~apollo_smmu_tbu::ARCH_CR0_ATSCHK" in tests
        and "m_tbu.m_arch_pri_auto_ste_ppar_checks" in tests
        and "SMMU-COMP-060 PRI PPR ATSCHK/EATS independence slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-pri-ppr-atschk-eats-independence-verification-2026-05-11.md"),
        "Apollo TBU documents and component-tests that incoming PRI Page Request enqueue is independent of CR0.ATSCHK and STE.EATS; STE.PPAR is consulted only for overflow auto-response",
    )
    add(
        "tbu:pri-prg-index-nine-bit",
        "ARCH_PRIQ_PPR_PRG_MASK = 0x1ff" in tbu
        and "arch_prg_index" in tbu
        and "complete_prg(arch_prg_index(word1)" in tbu
        and "pri_prg_pending" in tbu
        and "PriProtocolPrgIndexIsNineBitsAndWraps" in tests
        and "m_tbu.m_arch_next_prg = apollo_smmu_tbu::ARCH_PRIQ_PPR_PRG_MASK" in tests
        and "(last_prg | (1u << 9))" in tests
        and "SMMU-COMP-060 PRI PRGIndex 9-bit slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-pri-prg-index-nine-bit-verification-2026-05-11.md"),
        "Apollo TBU constrains modeled PRI PRGIndex allocation, PPR record encoding, and CMD_PRI_RESP matching to the architected 9-bit PRGIndex field",
    )
    add(
        "tbu:pri-response-unknown-diagnostic",
        "last_pri_response_unknown" in tbu
        and "last_pri_response_valid" in tbu
        and "last_pri_response_code" in tbu
        and "last_pri_response_unknown" in tests
        and "CmdPriRespUnknownPrgIsAccounted" in tests
        and "SMMU-COMP-060 PRI response unknown-PRG diagnostic slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-pri-response-unknown-prg-verification-2026-05-11.md"),
        "Apollo TBU preserves a diagnostic state for CMD_PRI_RESP commands that target an unknown PRG",
    )
    add(
        "tbu:pri-ppar-bad-stream-recinvsid",
        "record_pri_ppar_lookup_fault" in tbu
        and "arch_record_bad_streamid_ats_treq" in tbu
        and "ARCH_FAULT_BAD_STREAM_ID" in tbu
        and "ARCH_EVENT_C_BAD_STREAMID" in tbu
        and "PriProtocolPparBadStreamIdHonorsRecInvsid" in tests
        and "SMMU-COMP-060 PRI STE.PPAR bad StreamID RECINVSID slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-pri-ppar-bad-streamid-recinvsid-verification-2026-05-11.md"),
        "Apollo TBU gates PRI STE.PPAR bad-StreamID lookup EVENTQ records on CR2.REC_CFG_ATS plus CR2.RECINVSID",
    )
    add(
        "tbu:fault-replay-matrix",
        "FEATURE_ARCH_EVENT_RECORD_LAYOUT" in tbu
        and "REG_ARCH_FAULT_DETAIL" in tbu
        and "REG_ARCH_STALL_STATUS" in tbu
        and "ARCH_EVENT_C_BAD_CD" in tbu
        and "ARCH_EVENT_F_TRANSLATION" in tbu
        and "arch_event_number_for_fault" in tbu
        and "architected EVENTQ record layout" in tbu
        and "ARCH_CMD_STALL_TERM" in tbu
        and "ARCH_FAULT_CLASS_CD" in tbu
        and "ARCH_FAULT_ATTR_STALL" in tbu
        and "complete_stall" in tbu
        and "terminate_stalls_for_stream" in tbu
        and "FaultReplayRecordsSyndromeAndResumeState" in tests
        and "ArchitectedEventRecordLayoutCarriesSubstream" in tests
        and "CmdStallTermTerminatesPendingStalls" in tests
        and "FaultReplayFullEventQueueBuffersAndRedrivesStall" in tests,
        "Apollo TBU emits architected common EVENTQ event numbers/substream fields and component-tests stall resume/STALL_TERM plus overflow retention",
    )
    add(
        "tbu:stall-stag-resume",
        "arch_stall_record" in tbu
        and "ARCH_CMD_RESUME_STAG_MASK" in tbu
        and "ARCH_EVENT_STAG_MASK" in tbu
        and "ARCH_EVENT_STALL" in tbu
        and "allocate_stall_record" in tbu
        and "find_stall" in tbu
        and "m_arch_last_resume_stag" in tbu
        and "CmdResumeMatchesStreamIdAndStag" in tests,
        "Apollo TBU allocates nonzero STAGs for stalled EVENTQ records and matches CMD_RESUME by StreamID+STAG",
    )
    add(
        "tbu:negative-fault-replay-suite",
        "ARCH_CTRL_NEGATIVE_REPLAY_WRITE" in tbu
        and "arch_event_number_for_fault" in tbu
        and "ARCH_EVENT_F_ACCESS" in tbu
        and "ARCH_EVENT_F_PERMISSION" in tbu
        and "NegativeFaultReplayMatrixRecordsArchitectedEvents" in tests,
        "Apollo TBU component-tests a negative replay matrix across StreamID, STE, CD, access, and permission faults",
    )
    add(
        "tbu:endpoint-replay-accounting",
        "arch_endpoint_replay_record" in tbu
        and "REG_ARCH_ENDPOINT_REPLAY_STATUS" in tbu
        and "allocate_endpoint_replay_record" in tbu
        and "complete_endpoint_replay" in tbu
        and "EndpointTransactionReplayRetriesAfterCmdResume" in tests,
        "Apollo TBU accounts stalled endpoint transactions and retries translation after matching CMD_RESUME",
    )
    add(
        "tbu:endpoint-replay-redrive",
        "redrive_endpoint_replay" in tbu
        and "m_arch_endpoint_replay_redriven" in tbu
        and "payload.assign" in arch_core
        and "prepare_endpoint_replay_segment" in arch_core
        and "begin_endpoint_replay_transaction" in arch_core
        and "complete_endpoint_replay_transaction" in arch_core
        and "m_arch_core.begin_endpoint_replay_transaction" in tbu
        and "m_arch_core.complete_endpoint_replay_transaction" in tbu
        and "execute_endpoint_replay_transaction(transaction, delay)" in tbu
        and "trans.set_address(transaction.pa)" in tbu
        and "trans.set_data_ptr(transaction.payload)" in tbu
        and "downstream->b_transport(trans, delay)" in tbu
        and "EndpointTransactionReplayRedrivesWritePayload" in tests,
        "Apollo TBU re-drives held endpoint replay payloads downstream after matching CMD_RESUME retry",
    )
    add(
        "tbu:endpoint-replay-blocking",
        "ARCH_ENDPOINT_REPLAY_BLOCKING_ENABLE" in tbu
        and "wait_endpoint_replay_resume" in tbu
        and "m_arch_endpoint_replay_resume_event" in tbu
        and "REG_ARCH_ENDPOINT_BLOCK_STATUS" in tbu
        and "EndpointTransactionReplayBlocksCallerUntilCmdResume" in tests,
        "Apollo TBU can caller-block an endpoint access until matching CMD_RESUME retry resumes the transaction",
    )
    add(
        "tbu:stall-early-retry",
        "ARCH_ENDPOINT_REPLAY_EARLY_RETRY" in tbu
        and "early_retry_endpoint_replays" in tbu
        and "REG_ARCH_EARLY_RETRY_STATUS" in tbu
        and "early_retry_succeeded" in tbu
        and "EndpointEarlyRetryDoesNotDuplicateFaultAndRequiresResume" in tests,
        "Apollo TBU can early-retry a pending stalled endpoint transaction without adding another EVENTQ record and still requires CMD_RESUME acknowledgement",
    )
    add(
        "tbu:stall-early-retry-discard",
        "discard_uncommitted_early_retry" in tbu
        and "discard_buffered_stall_event" in tbu
        and "event_committed" in tbu
        and "m_arch_early_retry_discarded" in tbu
        and "EndpointEarlyRetryDiscardsUncommittedStaleEvent" in tests,
        "Apollo TBU can discard an uncommitted stale stalled EVENTQ record after successful early retry before the event becomes visible",
    )
    add(
        "tbu:event-record-common-access-attrs",
        "ARCH_EVENT_PNU_SHIFT" in tbu
        and "ARCH_EVENT_IND_SHIFT" in tbu
        and "ARCH_EVENT_CLASS_IN" in tbu
        and "transaction_privileged" in tbu
        and "transaction_instruction" in tbu
        and "privileged" in stream_ext
        and "instruction" in stream_ext
        and "ArchitectedEventRecordCommonAccessAttributesAreEncoded" in tests
        and "EndpointAccessAttributesPropagateToFaultEvent" in tests,
        "Apollo TBU encodes modeled EVENTQ PnU/InD/RnW and CLASS=IN common access attributes for stalled translation faults",
    )
    add(
        "tbu:event-record-class-selector",
        "arch_event_class_for_fault" in tbu
        and "m_arch_fault_event_class" in tbu
        and "ARCH_EVENT_CLASS_TT" in tbu
        and "ArchitectedEventRecordClassDistinguishesTableFaults" in tests,
        "Apollo TBU selects CLASS=TT for modeled translation-table faults instead of forcing CLASS=IN for every stalled translation event",
    )
    add(
        "tbu:event-record-stage2-cd-class",
        "m_arch_fault_event_class" in tbu
        and "ARCH_EVENT_CLASS_CD" in tbu
        and "ArchitectedEventRecordStage2CdFaultUsesClassCd" in tests,
        "Apollo TBU can encode modeled stage-2 CD-originated translation faults with CLASS=CD and IPA word3 data",
    )
    add(
        "tbu:nested-cd-fetch-stage2-fault",
        "architectural nested CD fetch stage-2 walk" in tbu
        and "m_arch_fault_event_class = ARCH_EVENT_CLASS_CD" in tbu
        and "m_arch_last_ipa = cd_pa" in tbu
        and "ArchitectedNestedCdFetchStage2FaultRecordsClassCd" in tests,
        "Apollo TBU translates nested CD fetch IPAs through stage 2 and records failing CD fetch translations as S2 CLASS=CD events",
    )
    add(
        "tbu:nested-l1cd-fetch-stage2-fault",
        "architectural nested L1CD fetch stage-2 walk" in tbu
        and "stage2_translate_l1cd_fetch" in tbu
        and "m_arch_fault_event_class = ARCH_EVENT_CLASS_CD" in tbu
        and "ArchitectedNestedL1CdFetchStage2FaultRecordsClassCd" in tests,
        "Apollo TBU translates nested 64K-L2 L1CD fetch IPAs through stage 2 and records failing L1CD fetch translations as S2 CLASS=CD events",
    )
    add(
        "tbu:nested-tt-fetch-stage2-fault",
        "stage2_translate_descriptor_fetch" in tbu
        and "ARCH_EVENT_CLASS_TT" in tbu
        and "m_arch_fault_event_class = ARCH_EVENT_CLASS_TT" in tbu
        and "ArchitectedNestedTtFetchStage2FaultRecordsClassTt" in tests,
        "Apollo TBU translates nested stage-1 translation-table descriptor fetch IPAs through stage 2 and records failing TT fetch translations as S2 CLASS=TT events",
    )
    add(
        "tbu:event-record-stage2-ipa",
        "ARCH_EVENT_IPA_MASK" in tbu
        and "arch_event_record_word3" in tbu
        and "ARCH_EVENT_FETCH_ADDR_MASK" in tbu
        and "ArchitectedEventRecordStage2IpaIsEncoded" in tests,
        "Apollo TBU uses EVENTQ word3 for stage-2 IPA/fetch-address layout data instead of private syndrome detail",
    )
    add(
        "tbu:event-record-nsipa",
        "ARCH_EVENT_NSIPA_SHIFT" in tbu
        and "m_arch_fault_nsipa" in tbu
        and "ArchitectedEventRecordNsipaBitIsEncoded" in tests,
        "Apollo TBU models the EVENTQ NSIPA bit for supplied stalled stage-2 records",
    )
    add(
        "tbu:event-record-fetch-address",
        "m_arch_last_fetch_addr" in tbu
        and "set_arch_fetch_fault" in tbu
        and "ARCH_EVENT_FETCH_ADDR_MASK" in tbu
        and "ArchitectedEventRecordFetchAddressIsEncoded" in tests,
        "Apollo TBU records modeled F_STE_FETCH/F_CD_FETCH fetch addresses in EVENTQ word3",
    )
    add(
        "tbu:event-record-fetch-reason-gpcf",
        "arch_event_record_has_fetch_reason" in tbu
        and (
            "m_arch_fault_gpcf ? (1ULL << ARCH_EVENT_GPCF_SHIFT) : 0" in tbu
            or "m_fault_replay_state.fault_gpcf ? (1ULL << EVENT_GPCF_SHIFT) : 0"
            in arch_core
        )
        and "EXPECT_EQ(0u, ste_word1)" in tests
        and "EXPECT_EQ(1ULL << apollo_smmu_tbu::ARCH_EVENT_GPCF_SHIFT, cd_word1)" in tests,
        "Apollo TBU encodes non-stall fetch-fault EVENTQ word1 as implementation-defined Reason=0 plus modeled GPCF, not InputAddr",
    )
    add(
        "tbu:event-record-walk-eabt",
        "ARCH_EVENT_F_WALK_EABT" in tbu
        and "ARCH_FAULT_WALK_EABT" in tbu
        and "FAULT_WALK_EABT" in arch_core
        and "fail_descriptor_fetch" in arch_core
        and "m_arch_core.fail_descriptor_memory_read" in tbu
        and "ArchitectedEventRecordWalkEabtCarriesFetchAddress" in tests,
        "Apollo TBU models F_WALK_EABT for descriptor-fetch external aborts with fetch-address EVENTQ word3 data",
    )
    add(
        "tbu:event-record-vms-fetch",
        "ARCH_EVENT_F_VMS_FETCH" in tbu
        and "ARCH_FAULT_VMS_FETCH" in tbu
        and "ARCH_EVENT_F_VMS_FETCH = 0x25" in tbu
        and "ArchitectedEventRecordVmsFetchCarriesFetchAddress" in tests,
        "Apollo TBU models the architected F_VMS_FETCH event number and fetch-address EVENTQ word3 data",
    )
    add(
        "tbu:vms-partid-map-fetch",
        "ARCH_VMS_PARTID_MAP_WORDS = 8" in tbu
        and "m_arch_last_vms_partid_map" in tbu
        and "m_arch_last_vms_partid_map.size()" in tbu
        and "VmsFetchCachesFullPartidMap" in tests,
        "Apollo TBU component-tests a full 64-byte VMS PARTID_MAP fetch/cache fill through STE.VMSPtr",
    )
    add(
        "tbu:event-record-gpcf",
        "ARCH_EVENT_GPCF_SHIFT" in tbu
        and "m_arch_fault_gpcf" in tbu
        and "set_arch_fetch_fault" in tbu
        and "ArchitectedEventRecordFetchGpcfBitIsEncoded" in tests,
        "Apollo TBU models the EVENTQ GPCF bit for fetch-event records when a modeled GPC fault is supplied",
    )
    add(
        "tbu:event-record-stream-substream",
        "ARCH_EVENT_F_STREAM_DISABLED" in tbu
        and "ARCH_EVENT_C_BAD_SUBSTREAMID" in tbu
        and "ARCH_FAULT_STREAM_DISABLED" in tbu
        and "ARCH_FAULT_BAD_SUBSTREAMID" in tbu
        and "ArchitectedStreamDisabledAndBadSubstreamEvents" in tests,
        "Apollo TBU maps modeled S1DSS/substream descriptor faults to F_STREAM_DISABLED and C_BAD_SUBSTREAMID EVENTQ records",
    )
    add(
        "tbu:event-record-c-bad-substreamid-layout",
        "ARCH_EVENT_C_BAD_SUBSTREAMID" in tbu
        and "arch_event_record_has_res0_payload" in tbu
        and "C_BAD_SUBSTREAMID has an architected InputAddr payload" in tests,
        "Apollo TBU component-tests C_BAD_SUBSTREAMID SSV/SubstreamID plus InputAddr payload layout instead of RES0 payload handling",
    )
    add(
        "tbu:config-disabled-no-event",
        "FEATURE_ARCH_CONFIG_DISABLED_NO_EVENT" in tbu
        and "m_arch_fault_record_suppressed" in tbu
        and "arch_ste_config(ste0) == 0" in tbu
        and "ArchitectedConfigDisabledSuppressesEvents" in tests
        and "AtsConfigDisabledReturnsUrWithoutEvent" in tests,
        "Apollo TBU terminates modeled STE.Config==0 traffic without an EVENTQ record and returns UR/no-event for ATS Translation Requests",
    )
    add(
        "tbu:ste-s2r-s2s-stage2-policy",
        "ARCH_STE_S2R" in tbu
        and "ARCH_STE_S2S" in tbu
        and "apply_arch_stage2_fault_policy" in tbu
        and "m_arch_fault_stage2_stall" in tbu
        and "Stage2SteS2rS2sControlsRecordAndStall" in tests,
        "Apollo TBU applies modeled STE.S2R/STE.S2S policy to stage-2 fault recording and stall-vs-terminate behavior",
    )
    add(
        "tbu:ste-s2s-stall-model-validation",
        "ARCH_STALL_MODEL_TERMINATE_ONLY" in tbu
        and "m_arch_stall_model" in tbu
        and "arch_stall_model_terminates_stage2_stalls" in tbu
        and "arch_ste_stage2_enabled" in tbu
        and "illegal STE.S2S for terminate-only STALL_MODEL" in tbu
        and "SteS2sRejectedWhenStallModelTerminateOnly" in tests,
        "Apollo TBU rejects stage-2 STE.S2S when modeled STALL_MODEL is terminate-only while preserving non-stage-2 S2S compatibility",
    )
    add(
        "tbu:ste-bypass-output-attrs",
        "ARCH_STE_MTCFG" in tbu
        and "arch_ste_memattr" in tbu
        and "record_arch_ste_output_attrs" in tbu
        and "populate_arch_output_attrs_extension" in tbu
        and "output_attrs_valid" in stream_ext
        and "SteBypassOutputAttributesPropagateOnContextBypass" in tests,
        "Apollo TBU applies modeled STE output attributes to bypass translations and propagates them on the SMMU TLM extension",
    )
    add(
        "tbu:ste-config-bypass-output-attrs",
        "ARCH_STE_CFG_BYPASS" in tbu
        and "arch_ste_all_bypass" in tbu
        and "ste-config-bypass" in tbu
        and "architectural STE.Config all-bypass" in tbu
        and "SteConfigBypassOutputAttributesPropagate" in tests,
        "Apollo TBU implements modeled STE.Config all-bypass identity translation while applying STE output attributes to downstream TLM transactions",
    )
    add(
        "tbu:ats-translated-output-attrs",
        "ats-translated" in tbu
        and "preserve_output_attrs_state" in tbu
        and "stage1-translation" in tbu
        and "stage2-translation" in tbu
        and "AtsTranslatedSteOutputAttributesPropagateWhenAtschkEnabled" in tests,
        "Apollo TBU preserves modeled STE output attributes across ATS Translated checks and propagates them to downstream TLM transactions",
    )
    add(
        "tbu:gatos-par-output-attrs",
        "ARCH_CTRL_GATOS_TRANSLATE" in tbu
        and "REG_ARCH_PAR_LO" in tbu
        and "arch_gatos_success_par" in tbu
        and "arch_gatos_fault_code" in tbu
        and "architectural GATOS translation" in tbu
        and "GatosParReportsSteOutputAttributes" in tests
        and "GatosParFaultCodeForUnmappedPage" in tests,
        "Apollo TBU exposes a modeled GATOS_PAR register command that returns STE output ATTR/SH on successful translation and FAULTCODE/REASON on translation faults",
    )
    add(
        "tbu:smmuv3-gatos-registers",
        "SMMUV3_GATOS_CTRL" in tbu
        and "SMMUV3_GATOS_SID_LO" in tbu
        and "SMMUV3_GATOS_ADDR_LO" in tbu
        and "SMMUV3_GATOS_PAR_LO" in tbu
        and "ARCH_GATOS_CTRL_RUN" in tbu
        and "run_arch_gatos_register_translate" in tbu
        and "record_fault_event" in tbu
        and "architectural SMMU_GATOS register translation" in tbu
        and "Smmuv3GatosRegistersRunAndClear" in tests
        and "Smmuv3GatosFaultDoesNotRecordEvent" in tests,
        "Apollo TBU exposes the architected non-secure SMMU_GATOS register group with RUN-to-PAR completion and no EVENTQ/PRI side effects for ATOS faults",
    )
    add(
        "tbu:smmuv3-secure-gatos-registers",
        "m_arch_secure_gatos_ctrl" in tbu
        and "m_arch_secure_gatos_sid" in tbu
        and "m_arch_secure_gatos_addr" in tbu
        and "m_arch_secure_gatos_par" in tbu
        and "arch_smmu_enabled_for_security_state" in tbu
        and "SMMU_S_GATOS" in tbu
        and "run_arch_gatos_register_translate(true)" in tbu
        and "ARCH_ATOS_SID_SECURE_STREAM" in tbu
        and "SecureSmmuv3GatosRegistersUseSecureBank" in tests
        and "SecureSmmuv3GatosFaultDoesNotRecordEvent" in tests,
        "Apollo TBU exposes the Secure SMMU_S_GATOS register group with Secure CR0 gating, Secure STRTAB selection, RUN-to-PAR completion, and no EVENTQ side effects for ATOS faults",
    )
    add(
        "tbu:smmuv3-secure-gatos-ssec-selection",
        "ARCH_ATOS_SID_SECURE_STREAM" in tbu
        and "secure_stream_lookup" in tbu
        and "SSEC Non-secure stream lookup blocked by Secure SMMUEN" in tbu
        and "lookup-security" in tbu
        and "SecureSmmuv3GatosSsecSelectsNonsecureStream" in tests
        and "ARCH_SECURITY_NONSECURE" in tests
        and "SMMU-COMP-030/080 S_GATOS.SSEC stream-selection slice" in read_text(repo / "doc/verification/qbox-smmuv3-secure-gatos-ssec-verification-2026-05-11.md"),
        "Apollo TBU decodes SMMU_S_GATOS_SID.SSEC so the Secure ATOS interface can select Secure versus Non-secure StreamID lookup, including the required Secure-CR0 gate for Non-secure stream queries",
    )
    add(
        "tbu:smmuv3-gatos-atos-addr-type",
        "ARCH_ATOS_ADDR_TYPE_STAGE1_STAGE2" in tbu
        and "ARCH_ATOS_ADDR_ADDR_MASK" in tbu
        and "ARCH_ATOS_SID_SSID_VALID" in tbu
        and "arch_atos_validate_ste_config" in tbu
        and "ARCH_FAULT_ATOS_INV_REQ" in tbu
        and "ARCH_FAULT_ATOS_INV_STAGE" in tbu
        and "atos-stage1-translation" in tbu
        and "atos-stage2-translation" in tbu
        and "Smmuv3GatosAddrTypeReservedAndInvStage" in tests
        and "Smmuv3GatosAddrTypeNestedStageSelection" in tests
        and "SMMU-COMP-030/080 ATOS_ADDR.TYPE matrix slice" in read_text(repo / "doc/verification/qbox-smmuv3-atos-addr-type-verification-2026-05-11.md"),
        "Apollo TBU decodes ATOS_ADDR.TYPE/RnW for SMMU_GATOS, returns INV_REQ for reserved TYPE, INV_STAGE for absent stages, and component-tests nested stage-1-only/stage-2-only/stage-1+stage-2 register translations",
    )
    add(
        "tbu:smmuv3-gatos-atos-access-fields",
        "ARCH_ATOS_ADDR_PNU" in tbu
        and "ARCH_ATOS_ADDR_IND" in tbu
        and "m_arch_last_atos_privileged" in tbu
        and "m_arch_last_atos_instruction" in tbu
        and "m_arch_last_atos_ste_attrs_ignored" in tbu
        and "STE output attributes ignored for ATOS" in tbu
        and "pnu=" in tbu
        and "ind=" in tbu
        and "rnw=" in tbu
        and "Smmuv3GatosAddrAccessFieldsIgnoreSteOverrides" in tests
        and "ARCH_ATOS_ADDR_PNU" in tests
        and "ARCH_ATOS_ADDR_IND" in tests
        and "SMMU-COMP-030/080 ATOS_ADDR access-field attribute slice" in read_text(repo / "doc/verification/qbox-smmuv3-atos-access-fields-verification-2026-05-11.md"),
        "Apollo TBU decodes ATOS_ADDR.PnU/InD/RnW for architected GATOS requests and suppresses STE output-attribute overrides from architected ATOS_PAR success ATTR/SH",
    )
    add(
        "tbu:smmuv3-internal-vatos-stage1",
        "ARCH_IDR0_VATOS" in tbu
        and "SMMUV3_VATOS_PAGE" in tbu
        and "SMMUV3_S_VATOS_PAGE" in tbu
        and "SMMUV3_VATOS_CTRL" in tbu
        and "SMMUV3_VATOS_SEL" in tbu
        and "m_arch_vatos_par" in tbu
        and "m_arch_secure_vatos_par" in tbu
        and "m_arch_gatos_par" in tbu
        and "m_arch_atos_virtual_interface = true" in tbu
        and "run_arch_vatos_register_translate" in tbu
        and "architectural SMMU_VATOS register translation" in tbu
        and "IDR0.VATOS clear" in tbu
        and "Smmuv3VatosStage1OnlyRegisterPath" in tests
        and "ARCH_IDR0_VATOS" in tests
        and "SMMU-COMP-020/030/080 internal VATOS stage-1 slice" in read_text(repo / "doc/verification/qbox-smmuv3-internal-vatos-verification-2026-05-11.md"),
        "Apollo TBU now has a non-advertised internal VATOS/S_VATOS register-page model for stage-1-only ATOS lookups, with independent GATOS/VATOS PAR state and IDR0.VATOS/SEL no-overclaiming until a non-overlapping guest-visible platform map exists",
    )
    add(
        "tbu:smmuv3-vatos-vmid-scope",
        "ARCH_STE_S2VMID_SHIFT" in tbu
        and "ARCH_STE2_S2VMID_FIELD" in tbu
        and "arch_ste_s2vmid" in tbu
        and "arch_active_vatos_sel" in tbu
        and "arch_validate_vatos_vmid_scope" in tbu
        and "architectural VATOS VMID scope reject" in tbu
        and "m_arch_current_vmid = arch_ste_s2vmid(ste2)" in tbu
        and "m_arch_vatos_sel" in tbu
        and "m_arch_secure_vatos_sel" in tbu
        and "foreign_vmid" in tests
        and "m_tbu.m_arch_vatos_sel = vmid" in tests
        and "Smmuv3VatosStage1OnlyRegisterPath" in tests
        and "SMMU-COMP-020/030/080 VATOS VMID-scope slice" in read_text(repo / "doc/verification/qbox-smmuv3-vatos-vmid-scope-verification-2026-05-11.md"),
        "Apollo TBU decodes STE.S2VMID from STE word 2, tags nested/stage-2 walks with that VMID, and rejects internal VATOS requests whose SMMU_VATOS_SEL VMID does not match the selected STE",
    )
    add(
        "tbu:ats-translated-forbidden-event",
        "ARCH_FAULT_TRANSL_FORBIDDEN" in tbu
        and "ARCH_EVENT_F_TRANSL_FORBIDDEN" in tbu
        and "transaction_translated" in tbu
        and "allow_arch_translated_transaction" in tbu
        and "translated = false" in stream_ext
        and "AtsTranslatedTransactionForbiddenRecordsEvent" in tests,
        "Apollo TBU records F_TRANSL_FORBIDDEN for modeled ATS Translated transactions rejected by ATSCHK/EATS",
    )
    add(
        "tbu:ats-translated-rec-cfg-ats-gate",
        "arch_record_translated_config_fault" in tbu
        and "record_or_suppress_arch_translated_config_fault" in tbu
        and "ARCH_CR2_REC_CFG_ATS" in tbu
        and "AtsTranslatedConfigFaultsHonorCr2RecCfgAts" in tests,
        "Apollo TBU gates ATS Translated configuration-fault EVENTQ records with CR2.REC_CFG_ATS and records Translated C_BAD_STREAMID without RECINVSID",
    )
    add(
        "tbu:ats-translated-smmuen-atschk-gates",
        "ats-translated-smmu-disabled" in tbu
        and "ATS translated transaction bypasses" in tbu
        and "configuration lookup because ATSCHK is disabled" in tbu
        and "AtsTranslatedTransactionsHonorSmmuenAndAtschk" in tests,
        "Apollo TBU aborts ATS Translated traffic while SMMUEN is disabled and bypasses configuration lookup while ATSCHK is disabled",
    )
    add(
        "tbu:ats-translated-address-size-no-event",
        "arch_translated_addr_in_oas" in tbu
        and "ATS translated address-size abort" in tbu
        and "AtsTranslatedAddressSizeAbortIsNoEvent" in tests,
        "Apollo TBU implements a spec-permitted no-event abort for ATS Translated addresses above the modeled PA size",
    )
    add(
        "tbu:ats-translated-split-stage-unsupported",
        "arch_translated_eats_unsupported_by_protocol" in tbu
        and "ATS translated split-stage unsupported" in tbu
        and "AtsTranslatedSplitStageUnsupportedRecordsForbidden" in tests,
        "Apollo TBU records implementation-defined F_TRANSL_FORBIDDEN for unsupported non-stage2/non-nested EATS_SPLIT ATS Translated traffic while modeled split-stage IPA walks are covered separately",
    )
    add(
        "tbu:ats-translated-split-stage-s2-walk",
        "arch_translated_split_stage_supported(uint32_t ste_cfg)" in tbu
        and "ste_cfg == ARCH_STE_CFG_S2_TRANS" in tbu
        and "AtsTranslatedSplitStageStage2OnlyWalksIpa" in tests
        and "SMMU-COMP-050/060 ATS Translated split-stage stage-2-only slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-ats-translated-split-stage-s2-verification-2026-05-11.md"),
        "Apollo TBU permits EATS_SPLIT ATS Translated traffic for the modeled stage-2-only stream case and validates the incoming IPA through the existing stage-2 walker",
    )
    add(
        "tbu:ats-translated-split-stage-nested-s2-walk",
        "m_arch_translated_split_stage2_request_active" in tbu
        and "ste_cfg == ARCH_STE_CFG_NESTED" in tbu
        and "ATS translated split-stage stage-2-only walk" in tbu
        and "AtsTranslatedSplitStageNestedWalksIpaWithStage2Only" in tests
        and "SMMU-COMP-050/060 architected nested ATS Translated split-stage IPA walk slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-ats-translated-split-stage-nested-verification-2026-05-11.md"),
        "Apollo TBU permits architected Nested STE EATS_SPLIT ATS Translated traffic and bypasses stage 1 so the incoming IPA is translated through stage 2 only",
    )
    add(
        "tbu:ats-treq-split-stage-nested-s2-walk",
        "m_arch_ats_treq_split_stage2_request_active" in tbu
        and "ATS translation request split-stage stage-2-only walk" in tbu
        and "ats-translation-request-split-stage2" in tbu
        and "AtsTranslationRequestSplitStageNestedWalksIpaWithStage2Only" in tests
        and "SMMU-COMP-060 architected nested ATS Translation Request split-stage IPA walk slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-ats-treq-split-stage-nested-verification-2026-05-11.md"),
        "Apollo TBU permits architected Nested STE EATS_SPLIT ATS Translation Requests and bypasses stage 1 so the incoming IPA is translated through stage 2 only",
    )
    add(
        "tbu:ats-treq-translation-fault-success-no-event",
        "arch_ats_treq_translation_fault_has_no_smmu_event" in tbu
        and "R==W==0" in tbu
        and "ATS translation request translation fault completed R==W==0" in tbu
        and "AtsTranslationRequestTranslationFaultReturnsSuccessNoEvent" in tests
        and "SMMU-COMP-050/060 ATS Translation Request translation-fault success/no-event slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-ats-treq-translation-fault-success-verification-2026-05-11.md"),
        "Apollo TBU returns modeled ATS Translation Request translation faults as Success with R==W==0 and suppresses SMMU fault/event recording",
    )
    add(
        "tbu:ats-treq-config-response-codes",
        "arch_ats_treq_response_code" in tbu
        and "log_arch_ats_treq_response" in tbu
        and "ats-config-abort" in tbu
        and "AtsTranslationRequestConfigFaultsUseArchitectedResponses" in tests
        and "SMMU-COMP-050/060 ATS Translation Request config-response slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-ats-treq-config-response-verification-2026-05-11.md"),
        "Apollo TBU returns Completer Abort for modeled ATS Translation Request configuration lookup faults and Unsupported Request plus F_BAD_ATS_TREQ for STE.Config abort",
    )
    add(
        "tbu:ats-treq-httu-write-intent",
        "ARCH_CTRL_ATS_TRANSLATION_REQUEST_WRITE" in tbu
        and "m_arch_last_ats_treq_write" in tbu
        and "run_arch_ats_translation_request(bool write = false)" in tbu
        and "nw=\" << (write ? 0 : 1)" in tbu
        and "httu-dirty=\" << (m_arch_last_httu_dirty_update ? 1 : 0)" in tbu
        and "AtsTranslationRequestWriteIntentUpdatesHttuDirty" in tests
        and "ARCH_CD_HD" in tests
        and "ARCH_DESC_DBM" in tests
        and "SMMU-COMP-040/050/060 ATS Translation Request HTTU write-intent slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-ats-treq-httu-write-intent-verification-2026-05-11.md"),
        "Apollo TBU routes ATS Translation Request write intent (NW==0) through the HTTU walker so CD.HA/CD.HD can mark DBM writable-clean pages writable-dirty before a success response, while HA-only write intent stays on the modeled W==0/no-event path",
    )
    add(
        "tbu:ats-translated-split-stage-access-overrides",
        "arch_ste_effective_privileged" in tbu
        and "arch_ste_effective_instruction" in tbu
        and "m_arch_translated_effective_access_valid" in tbu
        and "AtsTranslatedSplitStageNestedAppliesAccessOverrides" in tests
        and "SMMU-COMP-050/060 ATS Translated split-stage access-override slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-ats-translated-split-stage-access-overrides-verification-2026-05-11.md"),
        "Apollo TBU applies STE.PRIVCFG/INSTCFG effective access overrides before routing modeled EATS_SPLIT ATS Translated IPA traffic through the nested stage-2-only path",
    )
    add(
        "tbu:ats-translated-config-abort-forbidden",
        "ARCH_STE_CFG_ABORT" in tbu
        and "ATS translated STE.Config abort" in tbu
        and "AtsTranslatedConfigAbortRecordsForbidden" in tests,
        "Apollo TBU records F_TRANSL_FORBIDDEN for ATS Translated traffic targeting STE.Config==0b100",
    )
    add(
        "tbu:ats-translated-dpt-unsupported-disabled",
        "arch_dpt_supported" in tbu
        and "IDR3.DPT clear" in tbu
        and "AtsTranslatedDptUnsupportedActsAsDisabled" in tests
        and "SMMU-COMP-050/060 ATS DPT unsupported-as-disabled slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-ats-dpt-unsupported-as-disabled-verification-2026-05-11.md"),
        "Apollo TBU folds STE.EATS==DPT to EATS disabled while IDR3.DPT is clear, instead of reporting a modeled DPT lookup failure",
    )
    add(
        "tbu:ats-translated-pasidtt-disabled-prefix-clear",
        "arch_pasidtt_supported" in tbu
        and "ATS translated PASIDTT disabled" in tbu
        and "AtsTranslatedPasidttDisabledClearsPrefixAttrs" in tests,
        "Apollo TBU clears SSV/PnU/InD-derived event attributes for ATS Translated traffic while SMMU_IDR3.PASIDTT is 0",
    )
    add(
        "tbu:ats-translated-priority-config-before-forbidden",
        "AtsTranslatedPriorityChecksConfigBeforeForbidden" in tests
        and "C_BAD_STREAMID is checked before forbidden EATS" in tests
        and "C_BAD_STE is checked before F_TRANSL_FORBIDDEN" in tests,
        "Apollo TBU component-tests ATS Translated priority for config faults before F_TRANSL_FORBIDDEN while ATSCHK is enabled",
    )
    add(
        "tbu:ats-translated-priority-ste-fetch",
        "AtsTranslatedSteFetchRecordsBeforeSteDecode" in tests
        and "F_STE_FETCH is checked before STE decode/EATS" in tests
        and "ARCH_EVENT_F_STE_FETCH" in tests
        and "ARCH_CR2_REC_CFG_ATS" in tests,
        "Apollo TBU component-tests ATS Translated F_STE_FETCH priority before STE decode/EATS and REC_CFG_ATS-gated recording",
    )
    add(
        "tbu:ats-translated-priority-vms-fetch",
        "FEATURE_ARCH_VMS_FETCH" in tbu
        and "ARCH_STE_VMSPTR_MASK" in tbu
        and "arch_fetch_vms_if_enabled" in tbu
        and "ats-translated-vms-fetch" in tbu
        and "AtsTranslatedVmsFetchRecordsBeforeForbidden" in tests
        and "F_VMS_FETCH is checked before F_TRANSL_FORBIDDEN" in tests,
        "Apollo TBU component-tests ATS Translated F_VMS_FETCH from an actual modeled STE.VMSPtr fetch path before F_TRANSL_FORBIDDEN and under REC_CFG_ATS recording policy",
    )
    add(
        "tbu:mpam-vms-discovery",
        "ARCH_IDR3_MPAM = 1u << 7" in tbu
        and "ARCH_IDR3_MPAM | ARCH_IDR3_RIL" in tbu
        and "SMMUV3_MPAMIDR = 0x130" in tbu
        and "ARCH_MPAMIDR_PARTID_MAX = 31" in tbu
        and "MpamDiscoveryAdvertisesVmsPrerequisites" in tests
        and "APOLLO_SMMUV3_ARCH_IDR3\t\t0x00007794" in linux_driver,
        "Apollo TBU and Linux probe advertise MPAM/VMS prerequisites coherently through IDR3.MPAM and SMMU_MPAMIDR while leaving IDR3.DPT clear",
    )
    add(
        "tbu:mpam-partid-map-remap",
        "ARCH_CD_MPAM_WORD_OFFSET" in tbu
        and "ARCH_CD_VIRTUAL_PARTID_MASK = 0x1f" in tbu
        and "record_arch_mpam_from_cd" in tbu
        and "arch_vms_partid_map_entry" in tbu
        and "REG_ARCH_MPAM_STATUS" in tbu
        and "mpam_partid" in stream_ext
        and "mpam_pmg" in stream_ext
        and "VmsPartidMapRemapsCdPartidToMpamExtension" in tests,
        "Apollo TBU decodes CD.PARTID/PMG, remaps nested virtual PARTID through VMS.PARTID_MAP, and carries the resolved MPAM PARTID/PMG on the downstream TLM extension",
    )
    add(
        "tbu:ste-mpam-attributes",
        "ARCH_STE_MPAM_WORD4_OFFSET" in tbu
        and "ARCH_STE_PARTID_SHIFT = 16" in tbu
        and "ARCH_STE_PMG_SHIFT = 0" in tbu
        and "record_arch_mpam_from_ste" in tbu
        and "arch_ste_partid" in tbu
        and "arch_ste_pmg" in tbu
        and "mpam_partid" in stream_ext
        and "mpam_pmg" in stream_ext
        and "SteMpamAttributesPropagateWhenS1MpamDisabled" in tests,
        "Apollo TBU assigns STE.PARTID/PMG to downstream transactions when STE.S1MPAM is clear, preserving the architectural MPAM fallback path",
    )
    add(
        "tbu:mpam-range-unknown",
        "ARCH_MPAMIDR_PMG_MAX = 7" in tbu
        and "ARCH_MPAM_UNKNOWN_PARTID" in tbu
        and "ARCH_MPAM_UNKNOWN_PMG" in tbu
        and "arch_mpam_pmg_supported" in tbu
        and "apply_arch_mpam_range" in tbu
        and "MpamRangeOverflowMarksUnknownAttributes" in tests,
        "Apollo TBU bounds modeled MPAM PARTID/PMG against MPAMIDR and marks unsupported values as UNKNOWN on downstream TLM attributes",
    )
    add(
        "tbu:mpam-gbpmpam-global-bypass",
        "SMMUV3_GBPMPAM = 0x13c" in tbu
        and "ARCH_MPAM_UPDATE" in tbu
        and "write_arch_mpam_update_reg" in tbu
        and "record_arch_mpam_from_gbp" in tbu
        and "arch_mpam_reg_partid" in tbu
        and "GlobalBypassUsesGbpmpamAttributes" in tests,
        "Apollo TBU models SMMU_GBPMPAM Update writes and uses GBP_PARTID/PMG for client transactions while SMMU_CR0.SMMUEN is clear",
    )
    add(
        "tbu:gbpa-global-bypass-attrs-abort",
        "ARCH_GBPA_ABORT" in tbu
        and "record_arch_gbpa_output_attrs" in tbu
        and "architectural GBPA abort" in tbu
        and "GlobalBypassUsesGbpaOutputAttributes" in tests
        and "GlobalBypassGbpaAbortSuppressesEvent" in tests
        and "SMMU-COMP-020/030/080 GBPA global-bypass attribute/abort slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-gbpa-global-bypass-verification-2026-05-11.md"),
        "Apollo TBU applies SMMU_GBPA output attributes while SMMUEN is clear and honors GBPA.ABORT as a no-event disabled-SMMU abort",
    )
    add(
        "tbu:agbpa-unsupported-res0",
        "SMMUV3_AGBPA = 0x048" in tbu
        and "ARCH_AGBPA_UNSUPPORTED_RES0" in tbu
        and "Unsupported implementation-defined AGBPA field: RES0/WI" in tbu
        and "AgbpaUnsupportedRegistersAreRes0" in tests
        and "SMMU-COMP-020/030/080 AGBPA unsupported-RES0 slice"
        in read_text(repo / "doc/verification/qbox-smmuv3-agbpa-res0-verification-2026-05-11.md"),
        "Apollo TBU exposes SMMU_AGBPA/SMMU_S_AGBPA as RES0/WI when the implementation-defined alternate bypass tag field is unsupported",
    )
    add(
        "tbu:mpam-gmpam-originated-writes",
        "SMMUV3_GMPAM = 0x138" in tbu
        and "populate_arch_mpam_extension" in tbu
        and "m_arch_gmpam" in tbu
        and "write_downstream_u64" in tbu
        and "write_downstream_u32" in tbu
        and "GmpamAttributesPropagateOnEventqWrites" in tests,
        "Apollo TBU propagates SMMU_GMPAM PARTID/PMG on modeled SMMU-originated queue/MSI writes",
    )
    add(
        "tbu:mpam-gmpam-originated-fetches",
        "bool apply_gmpam = false" in tbu
        and "bool apply_current_mpam = false" in tbu
        and "populate_arch_mpam_extension" in tbu
        and "read_downstream_u64(entry_pa, word0, true)" in tbu
        and "read_downstream_u64(ste_pa, ste0, true)" in tbu
        and "read_downstream_u64(partid_pa, m_arch_last_vms_partid_map[i], true)" in tbu
        and "GmpamAttributesPropagateOnCmdqFetches" in tests
        and "GmpamAttributesPropagateOnSteAndVmsFetches" in tests,
        "Apollo TBU propagates SMMU_GMPAM PARTID/PMG on modeled SMMU-originated CMDQ, STE, L1STD, and VMS fetches",
    )
    add(
        "tbu:mpam-ste-cd-fetches",
        "populate_arch_mpam_extension_from_state" in tbu
        and "apply_current_mpam" in tbu
        and "read_downstream_u64(cd_fetch_pa, cd0, false, true)" in tbu
        and "read_downstream_u64(l1_fetch_pa, l1_desc, false, true)" in tbu
        and "SteMpamAttributesPropagateOnCdFetches" in tests,
        "Apollo TBU propagates resolved STE MPAM PARTID/PMG on modeled L1CD/CD fetches",
    )
    add(
        "tbu:mpam-client-tt-fetches",
        "populate_arch_mpam_extension_from_state" in tbu
        and "execute_descriptor_memory_read(desc_read, desc)" in tbu
        and "read_downstream_u64(read.transaction_pa, desc, false, true)" in tbu
        and "SteMpamAttributesPropagateOnS1TtFetches" in tests
        and "SteMpamAttributesPropagateOnS2TtFetches" in tests,
        "Apollo TBU propagates current client MPAM PARTID/PMG on modeled stage-1 and stage-2 translation-table descriptor fetches",
    )
    add(
        "tbu:mpam-s1mpam-helper-walks",
        "m_arch_last_ste5 = ste5" in tbu
        and "record_arch_mpam_from_cd(stream_id, cd5, nested_stage2, arch_ste_s1mpam(ste1))" in tbu
        and "SteMpamAttributesPropagateOnS1MpamCdFetches" in tests
        and "NestedS1MpamAttributesPropagateOnStage2HelperWalks" in tests,
        "Apollo TBU uses STE MPAM for S1MPAM CD fetch/helper walks before overriding client traffic with CD/VMS-remapped MPAM",
    )
    add(
        "tbu:mpam-ats-translated-gbp-ste",
        "preserve_mpam_state" in tbu
        and "record_arch_mpam_from_gbp(stream_id)" in tbu
        and "AtsTranslatedAtschkDisabledUsesGbpmpamAttributes" in tests
        and "AtsTranslatedSteMpamAttributesPropagateWhenAtschkEnabled" in tests,
        "Apollo TBU propagates modeled MPAM attributes on ATS Translated traffic for ATSCHK-disabled GBPMPAM and ATSCHK-enabled STE-sourced cases",
    )
    add(
        "tbu:mpam-ats-translated-cd",
        "translated_s1mpam_from_cd" in tbu
        and "record_arch_mpam_from_cd(stream_id, translated_cd5, false, true)" in tbu
        and "AtsTranslatedCdMpamAttributesPropagateWhenS1MpamEnabled" in tests,
        "Apollo TBU propagates modeled CD-derived MPAM attributes on ATS Translated traffic when STE.S1MPAM is enabled for the modeled S1 path",
    )
    add(
        "tbu:mpam-partid-space-nonsecure",
        "mpam_partid_space" in stream_ext
        and "ARCH_MPAM_SPACE_NONSECURE" in tbu
        and "m_arch_last_mpam_partid_space" in tbu
        and "arch_mpam_status" in tbu
        and "MpamAttributesCarryNonSecurePartidSpace" in tests,
        "Apollo TBU and TLM extension explicitly tag modeled MPAM attributes with the current Non-secure PARTID-space",
    )
    add(
        "tbu:mpam-security-partid-space",
        "arch_mpam_partid_space_for_security_state" in tbu
        and "ARCH_MPAM_SPACE_SECURE" in tbu
        and "ARCH_MPAM_SPACE_REALM" in tbu
        and "ARCH_MPAM_SPACE_ROOT" in tbu
        and "MpamAttributesCarrySecurityPartidSpace" in tests,
        "Apollo TBU derives modeled MPAM PARTID-space from Non-secure, Secure, Realm, and Root endpoint security states",
    )
    add(
        "tbu:secure-mpam-register-bank-attributes",
        "arch_gbpmpam_for_security_state" in tbu
        and "arch_gmpam_for_security_state" in tbu
        and "m_arch_secure_gbpmpam" in tbu
        and "m_arch_secure_gmpam" in tbu
        and "SecureMpamRegisterBanksDriveAttributes" in tests,
        "Apollo TBU uses the Secure SMMU_S GBPMPAM/GMPAM register bank for modeled Secure client and SMMU-originated MPAM attributes",
    )
    add(
        "tbu:event-record-conflict-events",
        "ARCH_EVENT_F_TLB_CONFLICT" in tbu
        and "ARCH_EVENT_F_CFG_CONFLICT" in tbu
        and "ARCH_FAULT_TLB_CONFLICT" in tbu
        and "ARCH_FAULT_CFG_CONFLICT" in tbu
        and "ArchitectedConflictEventsAreMapped" in tests,
        "Apollo TBU maps modeled implementation-defined TLB/config conflicts to F_TLB_CONFLICT and F_CFG_CONFLICT EVENTQ records",
    )
    add(
        "tbu:event-record-conflict-diagnostics",
        "EVENT_CONFLICT_REASON_TLB_TAG_MISMATCH" in arch_core
        and "EVENT_CONFLICT_REASON_CFG_STE_CONT" in arch_core
        and "event_record_has_conflict_reason" in arch_core
        and "ARCH_EVENT_CONFLICT_REASON_TLB_TAG_MISMATCH" in tbu
        and "ARCH_EVENT_CONFLICT_REASON_CFG_STE_CONT" in tbu
        and "ARCH_EVENT_CONFLICT_REASON_TLB_TAG_MISMATCH" in tests
        and "ARCH_EVENT_CONFLICT_REASON_CFG_STE_CONT" in tests,
        "Apollo TBU records implementation-defined Reason payloads in EVENTQ word3 for modeled F_TLB_CONFLICT and F_CFG_CONFLICT records",
    )
    add(
        "tbu:ats-cache-conflict-recovery",
        "ARCH_CTRL_TLB_CONFLICT" in tbu
        and "ats_cache_conflict_present" in tbu
        and "record_ats_cache_conflict_if_present" in tbu
        and "m_arch_tlb_conflict_recoveries" in tbu
        and "AtsCacheConflictProbeRecordsAndRecovers" in tests,
        "Apollo TBU component-tests modeled ATS/TLB cache-conflict detection, F_TLB_CONFLICT recording, and stale-entry recovery",
    )
    add(
        "tbu:config-cache-conflict-recovery",
        "ARCH_CTRL_CFG_CONFLICT" in tbu
        and "arch_config_cache_entry" in tbu
        and "config_cache_conflict_present" in tbu
        and "record_config_cache_conflict_if_present" in tbu
        and "m_arch_cfg_conflict_recoveries" in tbu
        and "ConfigCacheConflictProbeRecordsAndRecovers" in tests,
        "Apollo TBU component-tests modeled STE configuration-cache conflict detection, F_CFG_CONFLICT recording, stale-entry recovery, and security-state isolation",
    )
    add(
        "tbu:event-record-f-uut",
        "FEATURE_ARCH_F_UUT_EVENT" in tbu
        and "ARCH_EVENT_F_UUT" in tbu
        and "ARCH_FAULT_UNSUPPORTED_UPSTREAM" in tbu
        and "ARCH_CTRL_RECORD_F_UUT" in tbu
        and "ArchitectedUnsupportedUpstreamEventCanBeInjected" in tests,
        "Apollo TBU can inject a modeled F_UUT unsupported-upstream EVENTQ record with architected event number 0x01 and zero reason",
    )
    add(
        "tbu:event-record-config-res0-payload",
        "arch_event_record_has_res0_payload" in tbu
        and "ARCH_EVENT_C_BAD_STREAMID" in tbu
        and "ARCH_EVENT_C_BAD_STE" in tbu
        and "ARCH_EVENT_C_BAD_CD" in tbu
        and "ARCH_EVENT_F_STREAM_DISABLED" in tbu
        and "ArchitectedConfigEventPayloadsAreRes0" in tests
        and "BadStreamIdHonorsCr2RecInvsidForEventRecording" in tests,
        "Apollo TBU encodes non-stall C_BAD_STREAMID/C_BAD_STE/C_BAD_CD/F_STREAM_DISABLED payload words as RES0",
    )
    add(
        "tbu:stall-suppression-merge",
        "find_stall_by_fault" in tbu
        and "m_arch_stall_suppressed" in tbu
        and "REG_ARCH_STALL_MERGE_STATUS" in tbu
        and "StalledFaultsSuppressDuplicateEventRecords" in tests,
        "Apollo TBU suppresses duplicate stalled fault records and merges them onto the pending STAG",
    )
    add(
        "tbu:eventq-stall-buffer-redrive",
        "FEATURE_ARCH_STALL_BUFFER_REDRIVE" in tbu
        and "buffer_stall_event_record" in tbu
        and "drain_stall_event_buffer" in tbu
        and "stall-buffer" in tbu
        and "stall-redrive" in tbu
        and "FaultReplayFullEventQueueBuffersAndRedrivesStall" in tests,
        "Apollo TBU buffers stalled fault EVENTQ records while the queue is full and redrives them when software advances EVENTQ_CONS",
    )
    add(
        "iree:hal-registry-dispatch",
        "apollo_iree_hal_registry_lookup" in iree_registry
        and "CPU fallback device is disabled" in iree_registry
        and "dlopen(plugin_path, RTLD_NOW | RTLD_LOCAL)" in iree_registry
        and "APOLLO_IREE_HEXAGON_PLUGIN_EXPORT_NAME" in iree_registry
        and "dynamically registered C HAL plugin=%s" in iree_run_module
        and "upstream-style HAL registry" in iree_run_module
        and "apollo-iree-run-module" in iree_stage
        and "--device=apollo-hexagon" in iree_stage
        and "--executable_plugin=\"${self_dir}/lib/libapollo_iree_hexagon_hal_plugin.so\"" in iree_stage,
        "IREE run-module dispatch can dynamically register the Apollo Hexagon C HAL plugin through a repo-local upstream-style registry slice and rejects CPU fallback",
    )
    return results


def run_negative_self_test(repo: Path, manifest: dict[str, Any]) -> list[Result]:
    fake = json.loads(json.dumps(manifest))
    fake.setdefault("rows", []).append(
        {
            "id": "NEGATIVE-FAKE-IMPLEMENTED",
            "title": "Fake implemented row without evidence",
            "status": "implemented",
            "owner": "negative-test",
            "claim_scope": "must fail",
        }
    )
    row_results = validate_rows(repo, fake)
    saw_expected = any(r.name == "row:NEGATIVE-FAKE-IMPLEMENTED" and r.status == "fail" for r in row_results)
    return [Result("negative:self-test:implemented-without-evidence", "pass" if saw_expected else "fail", "fake implemented row without evidence is rejected")]


def summarize(results: list[Result]) -> dict[str, int]:
    out: dict[str, int] = {}
    for result in results:
        out[result.status] = out.get(result.status, 0) + 1
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument("--checklist", default=Path("doc/spec/qbox-smmuv3-compliance-checklist.md"), type=Path)
    parser.add_argument("--json", dest="json_path", type=Path, help="write JSON report")
    parser.add_argument("--self-test-negative", action="store_true", help="run built-in negative validation self-test")
    args = parser.parse_args()

    repo = args.repo.resolve()
    checklist = args.checklist if args.checklist.is_absolute() else repo / args.checklist
    manifest = extract_manifest(checklist)
    results = validate_rows(repo, manifest)
    results.extend(check_known_reference_failures(repo, manifest))
    results.extend(check_platform_invariants(repo))
    if args.self_test_negative:
        results.extend(run_negative_self_test(repo, manifest))

    payload = {
        "repo": str(repo),
        "checklist": str(checklist),
        "summary": summarize(results),
        "results": [result.__dict__ for result in results],
        "classification": {
            "smmu_comp_000": "implemented: checklist/checker/no-overclaiming gate is present and validated",
            "smmu_comp_010": "functional-slice: Apollo TBU now owns an architected core contract that records the canonical SystemC translation-state owner, compatibility-adapter contract, register/queue, STE/CD, walker, and replay state ownership, routes the SMMUv3 register aperture through that core, stores CMDQ/EVENTQ/PRIQ, stream/context selector, walker state, fault/replay scalar protocol state, STAG stall-record table storage, and endpoint replay payload record storage in the core, and factors queue helpers, walker geometry helpers, descriptor-walk validation/fetch planning/step classification, descriptor-fetch lifecycle/fault capture, descriptor memory-read request/result wrapping, STE/CD descriptor decode helpers, EVENTQ fault-record layout, replay/status packing helpers, stall-record lookup helpers, endpoint replay record lookup/reset helpers, endpoint replay allocation/retirement state transitions, endpoint replay redrive payload/status transitions, downstream transaction request/result wrapping, and a swappable adapter descriptor/replay I/O executor interface behind the core boundary; default executor still performs the physical descriptor memory reads and downstream b_transport replay I/O effects in the adapter, and QEMU bridge extraction remains open",
            "smmu_comp_020": "functional-slice: Apollo TBU exposes a guest-visible, compatibility-preserving SMMUv3 register/queue aperture including the architected non-secure SMMU_GATOS register group RUN/PAR completion path with ATOS_ADDR.TYPE/RnW/PnU/InD decode plus architected ATOS_PAR STE-output-override suppression, plus a non-advertised internal VATOS/S_VATOS stage-1-only register-page model with independent PAR state, STE.S2VMID-derived VMID tagging, SMMU_VATOS_SEL VMID-scope rejection, and IDR0.VATOS kept clear until a collision-free guest-visible map exists, and SMMU_S_* Secure page with Secure SMMU_S_GATOS RUN/PAR completion through S_GATOS_SID.SSEC Secure-vs-Non-secure stream selection and the Secure CR0/STRTAB bank with independent Secure STRTAB/CMDQ/EVENTQ/PRIQ bank state and memory-backed Secure CMDQ fetch/consume for selected commands plus modeled CFGI/TLBI/ATC SSec security-state routing, Non-secure SSec misuse CERROR_ILL, Secure ATC_INV_SYNC CERROR pause/skip/recovery ordering, Secure CMD_SYNC MSI success/abort/GERRORN acknowledgement plus Secure CMD_SYNC S_IRQ_CTRL visibility, and Secure EVENTQ/PRIQ/GERROR MSI bank routing/abort reporting, with component and Linux guest selftest coverage plus CFGI/TLBI/ATC invalidation side effects, ASID/VMID/SSID-tagged modeled invalidation, modeled TLBI_NH_VA/TLBI_NH_VAA range invalidation plus reserved NUM/SCALE/TG CERROR_ILL rejection, IDR0.ATS/PRI advertisement for modeled ATC/PRI command support, IDR3.RIL advertisement with Linux >64KB SG-DMA TLBI_NH_VA range-command stress, modeled additional TLBI opcode coverage for NSNH/EL2/EL3/S12/S2 with scoped NSNH invalidation preserving modeled EL2-regime entries, Secure-only S-EL2/S-S12/S-S2/SNH TLBI opcode coverage, TTL/Leaf hint accounting, modeled TTL/TG leaf-level filtering, and Leaf=0 table-walk cache invalidation accounting, IDR3.MPAM/MPAMIDR VMS discovery, CD.PARTID/PMG VMS PARTID_MAP remap plus STE.PARTID/PMG fallback assignment into downstream TLM MPAM attributes with MPAMIDR range-to-UNKNOWN handling, GBPA disabled-SMMU output attributes plus abort policy, unsupported AGBPA RES0/WI policy, and GBPMPAM global-bypass assignment plus GMPAM queue/MSI write, CMDQ/STE/VMS fetch attributes, STE-sourced CD fetch attributes, S1MPAM CD/helper-walk STE attributes before CD/VMS override, client-derived TT fetch attributes, and ATS Translated ATSCHK-disabled GBPMPAM plus ATSCHK-enabled STE/CD-sourced MPAM attributes, explicit security-state-derived MPAM PARTID-space tagging plus Secure GBPMPAM/GMPAM register-bank attribute selection in TLM/status, CMD_CFGI_VMS_PIDM modeled VMS/PARTID_MAP invalidation, guest-driven ATC_INV/TLBI_NH_ALL and RIL TLBI_NH_VA range-command stress plus component-tested additional and Secure-only TLBI opcode coverage, spec-position CR0 CMDQ/EVENTQ/PRIQ enable gates, EVENTQ/PRIQ OVFLG/OVACKFLG overflow flags, architected EVENTQ_ABT_ERR/PRIQ_ABT_ERR queue-write abort bits, IDR3.DPT=0 DPT register RES0/WI policy plus DPTI command rejection with CMDQ_CONS.CERROR_ILL, unconfigured queue abort reporting with CMDQ_CONS.CERROR_ABT, and modeled failed CMD_ATC_INV completion reporting through CMDQ_CONS.CERROR_ATC_INV_SYNC on CMD_SYNC, including multi-outstanding coalescing plus queue pause/skip/recovery coverage; full command/event/PRI compliance remains open, including remaining Realm/RME command encodings and security-state parameters beyond modeled Secure CFGI/TLBI/ATC SSec/Secure-only TLBI slices and remaining Secure IRQ/MSI ordering parity beyond the modeled CMD_SYNC/EVENTQ/PRIQ/GERROR paths",
            "smmu_comp_030": "functional-slice: Apollo TBU now selects architected StreamIDs through bounded linear/2-level STRTAB, indexes linear/64K-L2 context descriptor tables by S1CDMax-bounded SSID, propagates endpoint PASID/SSID metadata into ATS/event tagging, stage-2-translates nested CD, L1CD, and stage-1 TT descriptor-fetch IPAs, maps modeled S1DSS/substream descriptor faults to F_STREAM_DISABLED/C_BAD_SUBSTREAMID, accepts modeled Secure, Realm, and Root endpoint transactions on the existing translation path and explicitly rejects invalid security-state transactions before translation, models configured Secure stream-table bank selection through guest-visible SMMU_S_STRTAB_BASE registers, Secure stage-2-only NSCFG/S_S2TTB selection, Secure nested stage-1-derived NSIPA-to-S2TTB/S_S2TTB selection, Secure nested stage-1 TT-fetch S2TTB/S_S2TTB selection in component probes, and STE.S2R/STE.S2S stage-2 fault record/stall policy plus terminate-only STALL_MODEL validation, suppresses EVENTQ records for valid STE.Config==0 disabled streams, and component-tests no-substream S1DSS terminate/bypass plus modeled STE output-attribute propagation for context-bypass, STE.Config all-bypass, stage-1/stage-2/nested translation, ATS Translated payload paths, the bounded GATOS_PAR register return path, the architected non-secure SMMU_GATOS register group RUN/PAR/no-event ATOS path, the Secure SMMU_S_GATOS RUN/PAR/no-event ATOS path with S_GATOS_SID.SSEC Secure-vs-Non-secure stream selection, bounded ATOS_ADDR.TYPE reserved/INV_STAGE/nested stage-selection coverage plus ATOS_ADDR.PnU/InD access-field decode and architected ATOS_PAR STE-output-override suppression, an internal non-advertised VATOS/S_VATOS stage-1-only register-page model with GATOS/VATOS PAR isolation and SMMU_VATOS_SEL-to-STE.S2VMID scope rejection, plus modeled reserved/illegal STE/CD encodings including nested S2 after bypass; full PCIe PASID/CD invalidation parity, guest-visible complete VATOS/S_VATOS, remaining ATOS_ADDR fields beyond TYPE/RnW/PnU/InD and full attribute parity, and partial ATOS register parity beyond the modeled non-secure/Secure GATOS slices, remaining Secure command lifecycle parity beyond the modeled memory-backed S_CMDQ fetch/sync/invalidation/error-recovery/MSI slice, complete Root/Realm RME/GPT/GPC policy, full Arm reserved matrix parity, and true upstream arm-smmu-v3 CD invalidation lifecycle remain open",
            "smmu_comp_040": "functional-slice: Apollo TBU now component-tests selected 4K/16K/64K granules, modeled TLBI_NSNH/EL2/EL3/S12/S2 command forms including scoped NSNH invalidation plus Secure-only S-EL2/S-S12/S-S2/SNH command forms, block/page leaves, AF/permission faults, stage-2-only, nested CD/L1CD/TT-fetch/S2, nested S1+S2 including Secure stage-1-derived IPA-space S2TTB/S_S2TTB selection plus Secure stage-1 TT-fetch S2TTB/S_S2TTB selection, and nested S1DSS-bypass/S2 walks, but full Arm descriptor matrix plus exact TLBI TTL/Leaf reference-vector parity across all encodings and wider reference-vector parity remain open",
            "smmu_comp_050": "functional-slice: Apollo TBU now records architected common EVENTQ event numbers/substream fields including modeled F_STREAM_DISABLED/C_BAD_SUBSTREAMID for S1DSS/substream faults with C_BAD_SUBSTREAMID InputAddr payload validation, F_TRANSL_FORBIDDEN for ATSCHK/EATS rejected Translated transactions plus SMMUEN-disabled Translated traffic, ATS Translated address-size no-event abort behavior, stage-2-only and architected nested split-stage ATS Translated IPA walks plus modeled STE.PRIVCFG/INSTCFG effective access overrides before the nested stage-2-only walk plus implementation-defined rejection for unsupported non-stage2/non-nested split-stage traffic, STE.Config==0b100 F_TRANSL_FORBIDDEN aborts, DPT register RES0/WI policy plus DPT EATS disabled when IDR3.DPT=0 aborts, PASIDTT-disabled SSV/PnU/InD clearing, CR2.REC_CFG_ATS-gated ATS Translated configuration-fault records, partial ATS Translated event-priority validation for C_BAD_STREAMID/F_STE_FETCH/C_BAD_STE/F_VMS_FETCH before F_TRANSL_FORBIDDEN, ATSCHK==0 Translated configuration-lookup bypass, modeled F_TLB_CONFLICT/F_CFG_CONFLICT event-number plus implementation-defined word3 Reason payload plumbing for conflict reports, component-tested modeled ATS/TLB cache-conflict detection/recovery with F_TLB_CONFLICT recording and stale-entry invalidation, modeled STE configuration-cache conflict detection/recovery with F_CFG_CONFLICT recording and security-state isolation, modeled F_UUT unsupported-upstream event-number plus zero-Reason injection, unsupported security-state rejection, and EVENTQ security-state route accounting plus per-state logical bank mirrors and configured Secure-bank routing for modeled Secure fault events plus invalid-state events routed by masked Root event-state accounting, C_BAD_STREAMID CR2.RECINVSID event-recording suppression for normal probes, non-stall C_BAD_STREAMID/C_BAD_STE/C_BAD_CD/F_STREAM_DISABLED RES0 payload encoding, suppresses EVENTQ records for valid STE.Config==0 disabled-stream aborts, STE.S2R/STE.S2S-controlled stage-2 fault record/stall behavior plus terminate-only STALL_MODEL invalid-STE validation, syndrome detail via private status, modeled PnU/InD/RnW plus CLASS=IN/TT/CD access class attributes for stalled translation faults, stage-2 IPA word3 layout including nested CD, L1CD, and TT fetch translation failures, modeled NSIPA bit plumbing for supplied stalled stage-2 records, modeled F_STE_FETCH/F_CD_FETCH/F_WALK_EABT/F_VMS_FETCH fetch-address word3 layout plus actual modeled STE.VMSPtr-triggered F_VMS_FETCH recording, IDR3.MPAM/MPAMIDR VMS discovery, full 64-byte VMS PARTID_MAP fetch/cache fill, CD.PARTID/PMG VMS PARTID_MAP remap plus STE.PARTID/PMG fallback assignment into downstream TLM MPAM attributes with MPAMIDR range-to-UNKNOWN handling, GBPA disabled-SMMU output attributes plus abort policy, unsupported AGBPA RES0/WI policy, and GBPMPAM global-bypass assignment plus GMPAM queue/MSI write, CMDQ/STE/VMS fetch attributes, STE-sourced CD fetch attributes, S1MPAM CD/helper-walk STE attributes before CD/VMS override, client-derived TT fetch attributes, and ATS Translated ATSCHK-disabled GBPMPAM plus ATSCHK-enabled STE/CD-sourced MPAM attributes, explicit security-state-derived MPAM PARTID-space tagging plus Secure GBPMPAM/GMPAM register-bank attribute selection in TLM/status, plus CMD_CFGI_VMS_PIDM invalidation of the modeled VMS/PARTID_MAP state, non-stall fetch-fault Reason/GPCF word1 encoding, modeled GPCF bit plumbing for fetch-event records, stall-pending state, STAG/STALL bits for stalled EVENTQ records, StreamID+STAG matched CMD_RESUME, stream-wide CMD_STALL_TERM, duplicate stalled-fault suppression/merge onto pending STAGs, early retry of pending endpoint replay without duplicate EVENTQ records while preserving CMD_RESUME acknowledgement plus stale uncommitted EVENTQ discard, a negative replay matrix for StreamID/STE/CD/access/permission faults, endpoint replay accounting, downstream replay transaction wrapping plus payload re-drive, and opt-in caller blocking until CMD_RESUME retry, overflow retention, CR0.EVENTQEN gating, EVENTQ OVFLG/OVACKFLG overflow acknowledgement, EVENTQ_ABT_ERR queue-write abort reporting, and full-queue stall-event buffering/redrive with original security-state preservation for buffered records in component tests; full event matrix parity, full Secure event-queue/security-state routing beyond SMMU_S_EVENTQ bank routing, full RME/GPT/GPC, broader real-hardware configuration-cache geometry parity, and upstream arm-smmu-v3 recovery parity remain open",
            "smmu_comp_060": "functional-slice: Apollo TBU distinguishes ATS success/UR/CA outcomes, including STE.Config==0 UR without EVENTQ recording, PRG-tagged PRI pending, CMD_PRI_RESP head-ordered exact-PRG/StreamID/PASID clear/reject/unknown plus SMMUEN-disabled no-op, PRIQ_CONS advancement, and reserved-code CERROR_ILL handling, Secure CMDQ CMD_PRI_RESP Non-secure StreamID treatment, IDR0.ATS/PRI advertisement plus explicit unsupported-command guards, PRIQ OVFLG/OVACKFLG overflow acknowledgement, PRIQ_ABT_ERR queue-write abort reporting, automatic PRI success response for no-PASID Last PPR overflow, STE.PPAR-driven PASID-prefixed overflow response selection with REC_CFG_ATS/RECINVSID-gated lookup-fault recording, plus failure responses for Secure-stream, invalid STE.PPAR lookup, disabled, and abort-active cases, modeled PRI PPR SSV/Last/R/W/X/Priv metadata, PRI PRGIndex 9-bit allocation/encoding/head-ordered response matching plus PRIQ_CONS advancement, Stop PASID Marker no-response handling, non-last overflow discard without auto-response, and incoming PPR enqueue independence from CR0.ATSCHK/STE.EATS, CR0.ATSCHK plus STE.EATS Translation Request gates including architected nested split-stage ATS Translation Request IPA walks, ATS Translation Request translation faults returned as Success with R==W==0 and no SMMU event, ATS Translation Request configuration lookup faults returned as Completer Abort and STE.Config abort returned as Unsupported Request with F_BAD_ATS_TREQ, ATS Translation Request write intent (NW==0) drives HTTU dirty updates for writable-clean DBM pages and HA-only write intent returns modeled W==0/no-event, modeled ATS Translated transaction rejection with F_TRANSL_FORBIDDEN when SMMUEN/EATS forbids it, ATS Translated address-size no-event abort behavior, stage-2-only and architected nested split-stage ATS Translated IPA walks plus modeled STE.PRIVCFG/INSTCFG effective access overrides before the nested stage-2-only walk plus implementation-defined rejection for unsupported non-stage2/non-nested split-stage traffic, STE.Config==0b100 F_TRANSL_FORBIDDEN aborts, DPT register RES0/WI policy plus DPT EATS disabled when IDR3.DPT=0 aborts, PASIDTT-disabled SSV/PnU/InD clearing, ATSCHK==0 Translated configuration-lookup bypass plus GBPMPAM Translated MPAM attributes, ATSCHK-enabled STE/CD-sourced Translated MPAM attributes, CR2.REC_CFG_ATS-gated ATS Translated configuration-fault recording, partial ATS Translated priority validation including F_STE_FETCH before STE decode/EATS and F_VMS_FETCH from a modeled STE.VMSPtr path before F_TRANSL_FORBIDDEN, and CR2.REC_CFG_ATS/RECINVSID event-recording gates in component and Linux probe coverage, but full ATSCHK/EATS/stall/ATC protocol remains open",
            "smmu_comp_070": "functional-slice: Apollo TBU has signal-level EVENTQ/PRIQ/CMDQ_SYNC/GERROR outputs, IRQ_CTRL/IRQ_CTRLACK reserved-bit masking, raw GERROR/GERRORN active-bit toggle acknowledgement, architected queue-abort GERROR bits, MSI IRQ_CFG/CMD_SYNC MSI write plus MSI abort GERROR-bit coverage, Secure CMD_SYNC wired visibility through S_IRQ_CTRL/S_IRQ_CTRLACK, Secure EVENTQ MSI routing through S_EVENTQ_IRQ_CFG/S_GERROR, Secure PRIQ MSI routing through S_PRIQ_IRQ_CFG/S_GERROR.MSI_PRIQ_ABORT, and Secure GERROR MSI routing through S_GERROR_IRQ_CFG/S_GERROR.MSI_GERROR_ABORT, and Apollo Hexagon DMA async fence IRQ status now drives Linux-visible doorbell signals until software ACK with the Linux Apollo Hexagon driver binding the doorbell IRQ and waiting on interrupt-driven async fence completion before polling fallback, but full GIC/MSI ordering and upstream arm-smmu-v3 lifecycle remain open",
            "smmu_comp_080": "functional-slice: translated TLM carries StreamID plus endpoint PASID/SSID metadata and modeled STE output attributes for context-bypass, STE.Config all-bypass, stage-1/stage-2/nested translation, ATS Translated payload paths, the bounded GATOS_PAR register return path, the architected non-secure SMMU_GATOS register group RUN/PAR/no-event ATOS path, the Secure SMMU_S_GATOS RUN/PAR/no-event ATOS path with S_GATOS_SID.SSEC Secure-vs-Non-secure stream selection, bounded ATOS_ADDR.TYPE stage-selection on SMMU_GATOS plus ATOS_ADDR.PnU/InD access-field decode and architected ATOS_PAR STE-output-override suppression, a non-advertised internal VATOS/S_VATOS stage-1-only register-page model with GATOS/VATOS PAR isolation and VMID-scoped VATOS rejection, and Apollo TBU isolates dynamic maps/ATS entries per SID with endpoint SSID tagging plus command-driven SID/page/global and ASID/VMID/SSID-tagged invalidation in component tests plus Linux guest ATC_INV/TLBI_NH_ALL and RIL TLBI_NH_VA range-command stress coverage; platform/DTS now expose a second Linux-visible StreamID 0x2 master, but full PCIe/RID multi-master coverage remains open",
            "smmu_comp_090": "functional-slice: repo-local iree-run-module dispatch routes --device=apollo-hexagon through an upstream-style HAL registry frontend that dynamically dlopens/registers the Apollo Hexagon C HAL plugin and rejects CPU fallback; true upstream IREE source integration remains open",
            "full_smmuv3_compliance": "not_claimed: current QBox remains a functional/compliance-oriented slice until later SMMU-COMP gates pass",
        },
    }
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for result in results:
        print(f"{result.status.upper():5} {result.name}: {result.detail}")
    print("SUMMARY", json.dumps(payload["summary"], sort_keys=True))
    print("CLASSIFICATION", json.dumps(payload["classification"], sort_keys=True))
    return 1 if payload["summary"].get("fail", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
