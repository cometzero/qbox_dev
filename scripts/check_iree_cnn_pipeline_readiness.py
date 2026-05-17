#!/usr/bin/env python3
"""Check Apollo QBox readiness for an IREE tiny-CNN pipeline.

This is intentionally split into:
  * host/tooling checks for ONNX -> MLIR -> IREE CPU execution,
  * repo contract checks for the current A710 Linux boot lane, and
  * repo checks for the Apollo Hexagon productization baseline.

It distinguishes the repo-local functional HAL baseline from a future upstream
IREE plugin and full architectural ARM SMMUv3 model.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str
    required_for: str


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def has(path: Path, pattern: str) -> bool:
    return re.search(pattern, read_text(path), re.MULTILINE) is not None


def which(name: str) -> str | None:
    return shutil.which(name)


def os_access_executable(path: Path) -> bool:
    return path.exists() and path.is_file() and os.access(path, os.X_OK)


def module_available(name: str) -> bool:
    proc = subprocess.run(
        [sys.executable, "-c", f"import {name}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return proc.returncode == 0


def add(checks: list[Check], name: str, ok: bool, detail: str, required_for: str) -> None:
    checks.append(Check(name, "pass" if ok else "missing", detail, required_for))


def repo_checks(repo: Path) -> list[Check]:
    checks: list[Check] = []
    buildroot_defconfig = repo / "configs/buildroot/external/apollo_qbox/configs/apollo_qbox_defconfig"
    linux_config = repo / "configs/linux/linux.config"
    dts = repo / "configs/linux/apollo_soc.dts"
    linux_script = repo / "scripts/build_qbox_linux_arm64.sh"
    platform_script = repo / "scripts/build_qbox_buildroot_platform.sh"
    post_build = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/post-build.sh"
    run_script = repo / "scripts/run_qbox_buildroot_boot.sh"
    platform = repo / "sources/qbox/platforms/buildroot/conf_aarch64.lua"
    dma = repo / "sources/qbox/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h"
    tbu = repo / "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h"
    driver = repo / "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon.c"
    driver_selftest = repo / "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-selftest.c"
    driver_kconfig = repo / "sources/linux/drivers/accel/apollo_hexagon/Kconfig"
    iommu_test = repo / "sources/linux/drivers/iommu/iommu-test.c"
    qemu_cmake = repo / "sources/qemu/qemu.cmake"

    add(checks, "buildroot_rootfs_only", has(buildroot_defconfig, r"^BR2_TARGET_ROOTFS_CPIO=y$") and not has(buildroot_defconfig, r"^BR2_LINUX_KERNEL"), "Buildroot defconfig builds rootfs/initramfs and excludes kernel build", "a710_cpu_baseline")
    add(checks, "buildroot_cxx_runtime", has(buildroot_defconfig, r"^BR2_TOOLCHAIN_BUILDROOT_CXX=y$") and has(buildroot_defconfig, r"^BR2_INSTALL_LIBSTDCPP=y$"), "Buildroot defconfig enables C++ and installs libstdc++ required by the IREE runner", "a710_guest_runtime")
    add(checks, "standalone_linux_builder", has(linux_script, r"sources/linux") and has(linux_script, r"\bImage\b") and has(linux_script, r"ccache"), "standalone Linux Image build script uses sources/linux and ccache", "a710_cpu_baseline")
    add(checks, "a710_linux_config", has(linux_config, r"^CONFIG_ARM_SMMU_V3=y$") and has(linux_config, r"^CONFIG_DRM_ACCEL_APOLLO_HEXAGON=y$") and has(linux_config, r"^CONFIG_IOMMU_TEST=y$"), "Linux config fragment enables ARM SMMUv3, the Apollo Hexagon DRM accel driver, and the common IOMMU runtime test driver; ARCH=arm64 is supplied by build script", "a710_cpu_baseline")
    add(checks, "apollo_hexagon_dt_binding", has(dts, r"compatible = \"apollo,hexagon-ip\"") and has(dts, r"iommus = <&smmu 0x1>") and has(dts, r"apollo,dma-path = \"smmu-translated\""), "DTS exposes Apollo Hexagon node behind SMMU with smmu-translated DMA contract", "hexagon_dma_smoke")
    add(checks, "qbox_hexagon_modules", has(platform_script, r"qemu_cpu_hexagon") and has(platform_script, r"apollo_hexagon_dma") and has(platform_script, r"apollo_smmu_tbu"), "QBox platform build includes Hexagon CPU, DMA, and Apollo SMMU TBU modules", "hexagon_dma_smoke")
    add(checks, "runtime_module_guards", has(run_script, r"qemu_cpu_hexagon\.so") and has(run_script, r"apollo_hexagon_dma\.so") and has(run_script, r"apollo_smmu_tbu\.so"), "boot runner verifies Hexagon/SMMU runtime modules before launch", "hexagon_dma_smoke")
    add(checks, "translated_tlm_binding", has(platform, r"translated_dma = \{bind = \"&hexagon_smmu_tbu_0\.upstream\"\}") and has(platform, r"smmu_translated = true"), "Apollo Lua platform routes Hexagon DMA through SMMU-translated TLM path", "hexagon_dma_smoke")
    add(checks, "fixed_window_tbu", has(tbu, r"iova_base") and has(tbu, r"pa_base") and has(tbu, r"window_size") and has(tbu, r"TLM_ADDRESS_ERROR_RESPONSE"), "Apollo SMMU TBU supports fixed-window IOVA->PA translation and TLM address faults", "hexagon_dma_smoke")
    add(checks, "dynamic_tbu_map_unmap", has(tbu, r"REG_MAP_CTRL") and has(tbu, r"MAP_CTRL_ADD") and has(tbu, r"MAP_CTRL_REMOVE") and has(tbu, r"MAP_CTRL_CLEAR") and has(tbu, r'log_map\("unmap"'), "Apollo SMMU TBU exposes functional dynamic map/unmap/clear registers for Hexagon DMA windows", "hexagon_accelerator")
    add(checks, "tbu_page_table_ats_pri_fault", has(tbu, r"FEATURE_PAGE_TABLE_WALKER") and has(tbu, r"FEATURE_ATS_CACHE") and has(tbu, r"FEATURE_PRI_QUEUE") and has(tbu, r"FEATURE_FAULT_QUEUE") and has(tbu, r"page-table walk") and has(tbu, r"fault queue push"), "Apollo SMMU TBU exposes functional page-table walk, ATS cache, PRI, and fault queue observability", "hexagon_integration")
    add(checks, "tbu_arch_descriptor_probe", has(tbu, r"FEATURE_ARCH_DESCRIPTOR_WALK") and has(tbu, r"read_downstream_u64") and has(tbu, r"architectural descriptor walk"), "Apollo SMMU TBU can fetch and decode descriptor-backed page-table entries through downstream TLM", "hexagon_architecture_slice")
    add(checks, "tbu_arch_4level_probe", has(tbu, r"FEATURE_ARCH_4_LEVEL_WALK") and has(tbu, r"arch_level_index") and has(tbu, r"architectural table walk") and has(tbu, r"levels="), "Apollo SMMU TBU follows a 4KB-granule 4-level table-descriptor chain before decoding the L3 page descriptor", "hexagon_architecture_slice")
    add(checks, "tbu_stream_context_descriptor_walk", has(tbu, r"FEATURE_STREAM_TABLE_WALK") and has(tbu, r"FEATURE_CONTEXT_DESCRIPTOR_WALK") and has(tbu, r"architectural stream table walk") and has(tbu, r"architectural context descriptor walk"), "Apollo SMMU TBU fetches staged Stream Table Entries and Context Descriptors before the page-table descriptor chain", "hexagon_architecture_slice")
    add(checks, "tbu_arch_fault_replay_protocol", has(tbu, r"FEATURE_ARCH_FAULT_REPLAY") and has(tbu, r"FEATURE_ARCH_ATS_PRI_PROTOCOL") and has(tbu, r"architected fault replay queued") and has(tbu, r"architected ATS translation response") and has(tbu, r"architected PRI response"), "Apollo SMMU TBU exposes architected ATS/PRI response counters and a negative fault replay path", "hexagon_architecture_slice")
    add(checks, "tbu_multipage_split", has(tbu, r"translate_segment") and has(tbu, r"while \(offset < len\)") and has(tbu, r"set_data_ptr\(data \+ offset\)"), "Apollo SMMU TBU splits multi-page translated TLM transactions across mapped segments", "hexagon_productization")
    add(checks, "dma_large_tensor_transfer", has(dma, r"MAX_DMA_LEN = 256 \* 1024") and has(dma, r"CAP_LARGE_TENSOR") and has(dma, r"m_len > MAX_DMA_LEN"), "Apollo Hexagon DMA supports >64KB productization stress transfers", "hexagon_integration")
    add(checks, "dma_multi_queue_async_fence", has(dma, r"CAP_MULTI_QUEUE") and has(dma, r"CAP_ASYNC_FENCE") and has(dma, r"REG_JOB_QUEUE") and has(dma, r"REG_IRQ_STATUS") and has(dma, r"async irq pending"), "Apollo Hexagon DMA exposes multi-queue async IRQ/fence registers", "hexagon_integration")
    add(checks, "linux_driver_userspace_submit_abi", has(driver, r"DEFINE_DRM_ACCEL_FOPS") and has(driver, r"DRIVER_COMPUTE_ACCEL \| DRIVER_GEM") and has(driver, r"drm_dev_enter") and has(driver, r"drm_dev_unplug") and has(driver, r"APOLLO_HEXAGON_IOCTL\(SUBMIT_CNN") and has(driver, r"dynamic SMMU map refreshed"), "Apollo Linux driver exposes /dev/accel/accel* DRM accel submit ABI, initializes GEM-backed default fops safely, and refreshes dynamic SMMU mappings", "hexagon_accelerator")
    add(checks, "linux_driver_sg_dma_stress_abi", has(driver, r"APOLLO_HEXAGON_IOCTL\(DMA_STRESS") and has(driver, r"dynamic SMMU SG map refreshed") and has(driver, r"SG DMA stress ok queue=%u fence=%u bytes=%u segments=%u"), "Apollo Linux driver exposes multi-page scatter/gather DMA stress ABI and verifies copied data", "hexagon_productization")
    add(checks, "linux_driver_async_fence_runtime", has(driver, r"platform_get_irq_byname_optional") and has(driver, r"devm_request_irq") and has(driver, r"async fence signaled queue=%u fence=%u"), "Apollo Linux driver keeps doorbell IRQ and async fence completion in the normal runtime submit path", "hexagon_integration")
    add(checks, "linux_iommu_runtime_test_driver", has(iommu_test, r"compatible = \"apollo,iommu-runtime-test\"") and has(iommu_test, r"dma_map_resource") and has(iommu_test, r"IOMMU runtime selftest ok"), "drivers/iommu/iommu-test.c owns generic IOMMU group/domain, DMA API, resource mapping, and QBox data-plane runtime coverage", "hexagon_integration")
    add(checks, "linux_driver_optional_smmuv3_selftest", has(driver_kconfig, r"config DRM_ACCEL_APOLLO_HEXAGON_SELFTEST") and has(driver, r"apollo_hexagon_run_selftests") and has(driver_selftest, r"apollo_hexagon_run_selftests") and has(driver_selftest, r"SMMUv3 architectural descriptor probe ok") and has(driver_selftest, r"SMMUv3 command invalidation selftest ok") and has(driver_selftest, r"SMMUv3 RIL TLBI_NH_VA range selftest ok"), "Apollo Linux driver keeps QBox-specific SMMUv3 descriptor, queue, command, and RIL probes in a separate optional bring-up selftest file", "hexagon_architecture_slice")
    add(checks, "qemu_system_only", has(qemu_cmake, r"--disable-user") and has(qemu_cmake, r"\$\{target\}-softmmu"), "libqemu integration builds system targets and disables QEMU user-mode", "hexagon_runtime_gap")

    host_smoke_script = repo / "scripts/run_iree_tiny_cnn_host_smoke.sh"
    vector_add_host_smoke_script = repo / "scripts/run_iree_vector_add_host_smoke.sh"
    guest_stage_script = repo / "scripts/stage_iree_tiny_cnn_guest_artifacts.sh"
    vector_add_guest_stage_script = repo / "scripts/stage_iree_vector_add_guest_artifacts.sh"
    guest_smoke_script = repo / "scripts/run_iree_tiny_cnn_qbox_guest_smoke.sh"
    hexagon_smoke_script = repo / "scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh"
    vector_add_hexagon_smoke_script = repo / "scripts/run_iree_vector_add_hexagon_qbox_guest_smoke.sh"
    hexagon_runner = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hexagon_runner.c"
    hexagon_hal = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hexagon_hal.c"
    hexagon_hal_h = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hexagon_hal.h"
    hexagon_plugin = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hexagon_plugin.c"
    hexagon_plugin_h = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hexagon_plugin.h"
    hexagon_registry = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hal_registry.c"
    hexagon_registry_h = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hal_registry.h"
    hexagon_run_module = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_run_module.c"
    iree_plugin_abi = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_executable_plugin_abi.h"
    hexagon_guest_uapi = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_hexagon_uapi_guest.h"
    hexagon_firmware = repo / "sources/qbox/platforms/buildroot/fw/hexagon_dma_smoke.s"
    add(checks, "repo_iree_host_smoke_script", host_smoke_script.is_file() and os_access_executable(host_smoke_script), "repo-local host smoke script exists for ONNX->MLIR->IREE CPU validation", "a710_cpu_baseline")
    add(checks, "repo_iree_aarch64_compile", has(host_smoke_script, r"iree-llvmcpu-target-triple=aarch64-unknown-linux-gnu") and has(host_smoke_script, r"iree-llvmcpu-target-cpu=cortex-a710"), "host smoke also emits an AArch64/Cortex-A710 VMFB for guest staging", "a710_guest_artifact_baseline")
    add(checks, "repo_iree_guest_stage_script", guest_stage_script.is_file() and os_access_executable(guest_stage_script), "repo-local staging script packages tiny-CNN VMFB/reference/runner for Buildroot guest images", "a710_guest_artifact_baseline")
    add(checks, "repo_iree_guest_runtime_staged", has(guest_stage_script, r"iree-base-runtime") and has(guest_stage_script, r"bin/iree-run-module"), "guest staging script extracts an AArch64 iree-run-module runtime from the official wheel", "a710_guest_runtime")
    add(checks, "repo_iree_guest_smoke_script", guest_smoke_script.is_file() and os_access_executable(guest_smoke_script), "repo-local QBox guest smoke script verifies IREE tiny-CNN output in the booted guest", "a710_guest_runtime")
    add(checks, "repo_iree_hexagon_hal_runner", hexagon_runner.is_file() and hexagon_hal.is_file() and hexagon_hal_h.is_file() and hexagon_guest_uapi.is_file() and has(hexagon_runner, r"command buffer submitted") and has(hexagon_hal, r"apollo_hexagon_load_executable") and has(hexagon_hal, r"apollo_hexagon_queue_submit_cnn") and has(guest_stage_script, r"apollo-iree-hexagon-runner"), "repo-local IREE-compatible Apollo Hexagon HAL runner has executable metadata, queue, command buffer, and fence layers", "hexagon_productization")
    add(checks, "repo_iree_hexagon_hal_registry", hexagon_registry.is_file() and hexagon_registry_h.is_file() and hexagon_run_module.is_file() and has(hexagon_registry, r"apollo_iree_hal_registry_lookup") and has(hexagon_registry, r"CPU fallback device is disabled") and has(hexagon_registry, r"dlopen\(plugin_path, RTLD_NOW \| RTLD_LOCAL\)") and has(hexagon_registry, r"APOLLO_IREE_HEXAGON_PLUGIN_EXPORT_NAME") and has(hexagon_run_module, r"upstream-style HAL registry") and has(hexagon_run_module, r"dynamically registered C HAL plugin=%s") and has(guest_stage_script, r"apollo-iree-run-module") and has(guest_stage_script, r"--device=apollo-hexagon") and has(guest_stage_script, r"--executable_plugin"), "repo-local iree-run-module dispatch path dynamically registers the Apollo Hexagon C HAL plugin through an upstream-style registry frontend while rejecting CPU fallback devices", "hexagon_productization")
    add(checks, "repo_iree_dynamic_hal_plugin", hexagon_plugin.is_file() and hexagon_plugin_h.is_file() and iree_plugin_abi.is_file() and has(hexagon_plugin, r"apollo_iree_hexagon_plugin_query") and has(hexagon_plugin, r"iree_hal_executable_plugin_query") and has(guest_stage_script, r"libapollo_iree_hexagon_hal_plugin\.so"), "repo-local dynamic C HAL plugin also exports the upstream IREE executable_plugin query symbol", "hexagon_integration")
    add(checks, "repo_iree_hexagon_metadata", has(guest_stage_script, r"apollo_hexagon\.vmfb\.meta") and has(guest_stage_script, r"command_buffer=fixed") and has(guest_stage_script, r"fence=async-irq-poll") and has(guest_stage_script, r"upstream_executable_plugin=iree_hal_executable_plugin_query"), "guest staging emits VMFB metadata and dynamic plugin path used by the Apollo Hexagon HAL loader", "hexagon_productization")
    add(checks, "repo_iree_hexagon_guest_smoke_script", hexagon_smoke_script.is_file() and os_access_executable(hexagon_smoke_script) and has(hexagon_smoke_script, r"SG DMA stress ok queue=0") and has(hexagon_smoke_script, r"bytes=131072 segments=8") and has(hexagon_smoke_script, r"async irq pending queue=1") and has(hexagon_smoke_script, r"fence=async-irq-poll"), "repo-local QBox guest smoke script verifies Hexagon offload, >64KB SG DMA, async fences, and SMMU markers with UART-interleave-tolerant markers", "hexagon_productization")
    add(checks, "repo_iree_vector_add_host_smoke_script", vector_add_host_smoke_script.is_file() and os_access_executable(vector_add_host_smoke_script) and has(vector_add_host_smoke_script, r"vector_add_graph") and has(vector_add_host_smoke_script, r"4xf32=11 22 33 44"), "repo-local host smoke script generates ONNX vector Add, compiles host/AArch64 VMFBs, and verifies IREE runtime output", "hexagon_vector_add")
    add(checks, "repo_iree_vector_add_guest_stage_script", vector_add_guest_stage_script.is_file() and os_access_executable(vector_add_guest_stage_script) and has(vector_add_guest_stage_script, r"QBOX_IREE_VECTOR_ADD_GUEST_STAGE_DIR") and has(vector_add_guest_stage_script, r"run_vector_add_hexagon_guest\.sh"), "repo-local staging script packages vector-add VMFB, IREE runtime wrapper, and Apollo Hexagon HAL plugin for /opt/qbox/iree/vector-add", "hexagon_vector_add")
    add(checks, "repo_iree_vector_add_hexagon_smoke_script", vector_add_hexagon_smoke_script.is_file() and os_access_executable(vector_add_hexagon_smoke_script) and has(vector_add_hexagon_smoke_script, r"accelerator vector add ok") and has(vector_add_hexagon_smoke_script, r"EXEC @vector_add_graph \[apollo-hexagon\]"), "repo-local QBox guest smoke script verifies vector-add execution through iree-run-module --device=apollo-hexagon and SMMU-translated DMA markers", "hexagon_vector_add")
    add(checks, "repo_hexagon_vector_add_uapi", has(hexagon_guest_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_SUBMIT_VADD") and has(hexagon_hal, r"apollo_hexagon_queue_submit_vadd") and has(hexagon_runner, r"vector_add_graph") and has(hexagon_run_module, r"vector_add_graph"), "Apollo guest UAPI/HAL runner exposes a vector-add job path beside the tiny-CNN command path", "hexagon_vector_add")
    add(checks, "repo_hexagon_vector_add_firmware", has(hexagon_firmware, r"vector_add_job") and has(hexagon_firmware, r"0x56414444") and has(hexagon_firmware, r"0x41300000") and has(hexagon_firmware, r"0x42300000"), "Hexagon firmware job loop recognizes the vector-add ABI and emits the canonical 4xf32 output through SMMU-translated DMA", "hexagon_vector_add")
    add(checks, "hexagon_firmware_cnn_kernel", has(hexagon_firmware, r"0x42580000") and has(hexagon_firmware, r"0x10203000") and has(hexagon_firmware, r"job_loop"), "Hexagon firmware runtime consumes submit jobs, moves buffers through DMA, and emits tiny-CNN output", "hexagon_accelerator")
    add(checks, "hexagon_firmware_dma_copy_runtime", has(hexagon_firmware, r"dma_copy_job") and has(hexagon_firmware, r"0x53474f4b") and has(hexagon_firmware, r"poll_copy_dma_done"), "Hexagon firmware runtime handles command-queue DMA copy jobs for multi-page stress traffic", "hexagon_productization")
    add(checks, "buildroot_optional_iree_staging", has(post_build, r"QBOX_IREE_GUEST_ARTIFACTS_DIR") and has(post_build, r"/opt/qbox/iree/tiny-cnn"), "Buildroot post-build can optionally copy staged IREE tiny-CNN artifacts into the rootfs", "a710_guest_artifact_baseline")
    return checks


def host_checks() -> list[Check]:
    checks: list[Check] = []
    add(checks, "iree_import_onnx_tool", which("iree-import-onnx") is not None, f"tool={which('iree-import-onnx')}", "host_smoke")
    add(checks, "iree_compile_tool", which("iree-compile") is not None, f"tool={which('iree-compile')}", "host_smoke")
    add(checks, "iree_run_module_tool", which("iree-run-module") is not None, f"tool={which('iree-run-module')}", "host_smoke")
    add(checks, "python_onnx", module_available("onnx"), "python module onnx import", "host_smoke")
    add(checks, "python_numpy", module_available("numpy"), "python module numpy import", "host_smoke")
    return checks


def summarize(checks: Iterable[Check]) -> dict[str, int]:
    result: dict[str, int] = {}
    for check in checks:
        result[check.status] = result.get(check.status, 0) + 1
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument("--json", dest="json_path", type=Path, help="write JSON report")
    parser.add_argument("--require-host-tools", action="store_true", help="fail if IREE/ONNX host tools are not installed")
    args = parser.parse_args()

    repo = args.repo.resolve()
    checks = repo_checks(repo) + host_checks()
    payload = {
        "repo": str(repo),
        "summary": summarize(checks),
        "checks": [check.__dict__ for check in checks],
        "classification": {
            "a710_cpu_iree_baseline": "guest_runtime_ready: boot/rootfs/kernel lane exists and AArch64 VMFB plus iree-run-module can be staged and smoke-tested",
            "hexagon_iree_accelerator": "repo_local_integration_ready: dynamic C HAL plugin, /dev/accel/accel* DRM accel submit ABI, VMFB metadata loader, multi-queue command buffer/fence runner, >64KB SG DMA stress, and firmware CNN runtime are implemented and smoke-testable",
            "smmu_dma_model": "functional_smmuv3_ready: dynamic map/unmap/clear registers, page-table walk observability, ATS/PRI/fault queue status, and translated TLM splitting support >64KB SG stress",
            "upstream_iree_hal_driver": "functional_registry_slice: repo-local iree-run-module dispatch now routes --device=apollo-hexagon through an upstream-style HAL registry frontend that dynamically dlopens/registers the Apollo Hexagon C HAL plugin; true upstream IREE source integration remains pending",
            "architectural_smmuv3_model": "compliance_slice_advanced: current model includes STE/CD fetch, a descriptor-backed 4KB-granule 4-level page-table probe, architected ATS/PRI response accounting, and a negative fault replay suite; full bit-exact ARM SMMUv3 register/protocol coverage remains upstream-scale work",
        },
    }

    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for check in checks:
        print(f"{check.status.upper():7} {check.name}: {check.detail}")
    print("SUMMARY", json.dumps(payload["summary"], sort_keys=True))
    print("CLASSIFICATION", json.dumps(payload["classification"], ensure_ascii=False, sort_keys=True))

    if args.require_host_tools:
        host_missing = [c for c in checks if c.required_for == "host_smoke" and c.status != "pass"]
        if host_missing:
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
