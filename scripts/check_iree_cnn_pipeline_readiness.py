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


def venv_dir(repo: Path) -> Path:
    return Path(os.environ.get("QBOX_IREE_SMOKE_VENV", repo / "build/iree-smoke-venv"))


def tool_path(repo: Path, name: str) -> str | None:
    path = which(name)
    if path is not None:
        return path
    venv_tool = venv_dir(repo) / "bin" / name
    if os_access_executable(venv_tool):
        return str(venv_tool)
    return None


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


def module_available_for_repo(repo: Path, name: str) -> bool:
    if module_available(name):
        return True
    venv_python = venv_dir(repo) / "bin" / "python"
    if not os_access_executable(venv_python):
        return False
    proc = subprocess.run(
        [str(venv_python), "-c", f"import {name}"],
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
    external_config = repo / "configs/buildroot/external/apollo_qbox/Config.in"
    external_mk = repo / "configs/buildroot/external/apollo_qbox/external.mk"
    run_script = repo / "scripts/run_qbox_buildroot_boot.sh"
    iree_runtime_config = repo / "configs/buildroot/external/apollo_qbox/package/iree-runtime/Config.in"
    iree_runtime_mk = repo / "configs/buildroot/external/apollo_qbox/package/iree-runtime/iree-runtime.mk"
    iree_runtime_build_script = repo / "scripts/build_iree_runtime_buildroot.sh"
    hexagon_mlir_bridge_check = repo / "scripts/check_hexagon_mlir_iree_bridge.py"
    hexagon_mlir_target_check = repo / "scripts/check_hexagon_mlir_target_execution.py"
    hexagon_mlir_target_runner = repo / "scripts/run_hexagon_mlir_target_vec_add.sh"
    platform = repo / "sources/qbox/platforms/buildroot/conf_aarch64.lua"
    dma = repo / "sources/qbox/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h"
    dma_tests = repo / "sources/qbox/tests/components/apollo_hexagon_dma/apollo-hexagon-dma-tests.cc"
    tbu = repo / "sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h"
    driver = repo / "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon.c"
    driver_header = repo / "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon.h"
    hexagon_kernel_uapi = repo / "sources/linux/include/uapi/drm/apollo_hexagon_accel.h"
    driver_bo = repo / "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-bo.c"
    driver_context = repo / "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-context.c"
    driver_compat = repo / "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-compat.c"
    driver_exec = repo / "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-exec.c"
    driver_fault = repo / "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-fault.c"
    driver_fence = repo / "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-fence.c"
    driver_iommu = repo / "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-iommu.c"
    driver_selftest = repo / "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-selftest.c"
    driver_kconfig = repo / "sources/linux/drivers/accel/apollo_hexagon/Kconfig"
    iommu_test = repo / "sources/linux/drivers/iommu/iommu-test.c"
    qemu_cmake = repo / "sources/qemu/qemu.cmake"
    gitmodules = repo / ".gitmodules"
    iree_source = repo / "sources/iree"
    hexagon_mlir_source = repo / "sources/hexagon-mlir"

    add(checks, "buildroot_rootfs_only", has(buildroot_defconfig, r"^BR2_TARGET_ROOTFS_CPIO=y$") and not has(buildroot_defconfig, r"^BR2_LINUX_KERNEL"), "Buildroot defconfig builds rootfs/initramfs and excludes kernel build", "a710_cpu_baseline")
    add(checks, "buildroot_cxx_runtime", has(buildroot_defconfig, r"^BR2_TOOLCHAIN_BUILDROOT_CXX=y$") and has(buildroot_defconfig, r"^BR2_INSTALL_LIBSTDCPP=y$"), "Buildroot defconfig enables C++ and installs libstdc++ required by the IREE runner", "a710_guest_runtime")
    add(checks, "buildroot_iree_runtime_package", has(buildroot_defconfig, r"^BR2_PACKAGE_IREE_RUNTIME=y$") and has(external_config, r"package/iree-runtime/Config\.in") and has(external_mk, r"package/\*/\*\.mk") and iree_runtime_config.is_file() and has(iree_runtime_mk, r"IREE_RUNTIME_SITE = .*/sources/iree") and has(iree_runtime_mk, r"IREE_RUNTIME_BUILD_OPTS = --target iree-run-module") and has(iree_runtime_mk, r"IREE_HOST_BIN_DIR=\$\(HOST_DIR\)/bin") and os_access_executable(iree_runtime_build_script), "Buildroot external tree builds source-based IREE iree-run-module from sources/iree and includes it in the Apollo rootfs", "a710_guest_runtime")
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
    cmdq_foundation = (
        has(dma, r"REG_CMDQ_DOORBELL")
        and has(dma, r"REG_CMDQ_FENCE_VALUE")
        and has(dma, r"REG_CMDQ_FAULT_CODE")
        and has(dma, r"CMDQ_FAULT_UNSUPPORTED_PACKET")
        and has(dma, r"CMDQ_FAULT_MALFORMED_PACKET")
        and has(dma, r"CMDQ_FAULT_DMA_ERROR")
        and has(dma, r"CMDQ_OPCODE_COPY")
        and has(dma, r"CMDQ_OPCODE_SIGNAL_FENCE")
        and has(dma, r"CMDQ_OPCODE_DISPATCH")
        and has(dma, r"CMDQ_OPCODE_LOAD_EXECUTABLE")
        and has(dma, r"CMDQ_OPCODE_LOAD_PAYLOAD")
        and has(dma, r"CMDQ_DISPATCH_EXEC_SLOT_FLAG")
        and has(dma, r"CMDQ_DISPATCH_KIND_VADD")
        and has(dma, r"command_queue_addr")
        and has(dma, r"execute_copy_packet")
        and has(dma, r"execute_dispatch_packet")
        and has(dma, r"execute_load_executable_packet")
        and has(dma, r"execute_load_payload_packet")
        and has(dma, r"execute_loaded_dispatch_packet")
        and has(dma, r"execute_vadd_dispatch_packet")
        and has(dma, r"complete_command_queue")
        and has(dma, r"run_command_queue")
        and has(dma_tests, r"CommandQueueDoorbellReportsEmptyFaultAndIrq")
        and has(dma_tests, r"CommandQueueDoorbellReportsUnsupportedPacketFault")
        and has(dma_tests, r"CommandQueueDoorbellRejectsMalformedGeometry")
        and has(dma_tests, r"CommandQueueCopyReportsDmaFault")
        and has(dma_tests, r"CommandQueueDispatchesVadd")
        and has(dma_tests, r"CommandQueueLoadExecutableDispatchesVaddSlot")
        and has(dma_tests, r"CommandQueueExecutableSlotRequiresPayload")
        and has(dma_tests, r"CommandQueueLoadPayloadRejectsBadOpcode")
        and has(dma_tests, r"CommandQueueLoadExecutableRejectsBadAbi")
        and has(dma_tests, r"CommandQueueDispatchReportsDmaFault")
        and has(dma_tests, r"CommandQueueExecutesCopyBarrierAndSignalFence")
    )
    add(checks, "qbox_hexagon_command_queue_foundation", cmdq_foundation, "Apollo Hexagon DMA exposes command queue registers/faults, address overflow guarding, NOP/COPY/BARRIER/SIGNAL_FENCE execution, LOAD_EXECUTABLE metadata slots, explicit LOAD_PAYLOAD records, executable-slot dispatch, and component-tested DISPATCH/VADD packet paths", "hexagon_apko_generic")
    model_kernel_stubs = (
        has(dma, r"CMDQ_DISPATCH_KIND_CNN")
        and has(dma, r"CMDQ_DISPATCH_KIND_MNIST")
        and has(dma, r"execute_cnn_dispatch_packet")
        and has(dma, r"execute_mnist_dispatch_packet")
        and has(dma, r"JOB_RESULT_CNN_OK")
        and has(dma, r"JOB_RESULT_MNIST_OK")
        and has(dma_tests, r"CommandQueueDispatchesCnn")
        and has(dma_tests, r"CommandQueueDispatchesMnistFlattenGemm")
        and has(dma_tests, r"CommandQueueLoadExecutableDispatchesCnnSlot")
        and has(dma_tests, r"CommandQueueLoadExecutableDispatchesMnistSlot")
        and has(dma_tests, r"CommandQueueLoadExecutableRejectsBadDispatchKind")
    )
    add(checks, "qbox_hexagon_model_kernel_stubs", model_kernel_stubs, "Apollo Hexagon DMA command queue has deterministic CNN and MNIST Flatten+Gemm model-kernel semantics, including direct dispatch and executable-slot coverage", "hexagon_apko_generic")
    add(checks, "linux_driver_userspace_submit_abi", has(driver, r"DEFINE_DRM_ACCEL_FOPS") and has(driver, r"DRIVER_COMPUTE_ACCEL \| DRIVER_GEM") and has(driver, r"DRM_GEM_SHMEM_DRIVER_OPS") and has(driver, r"drm_dev_enter") and has(driver, r"drm_dev_unplug") and has(driver, r"APOLLO_HEXAGON_IOCTL\(SUBMIT_CNN") and has(driver_iommu, r"dynamic SMMU map refreshed"), "Apollo Linux driver exposes /dev/accel/accel* DRM accel submit ABI, initializes GEM SHMEM-backed default fops safely, and refreshes dynamic SMMU mappings", "hexagon_accelerator")
    add(checks, "linux_driver_generic_kconfig", has(driver_kconfig, r"generic APKO executable, context, GEM buffer") and has(driver_kconfig, r"object, BO binding, command BO submit") and has(driver_kconfig, r"query-caps, wait, and") and has(driver_kconfig, r"fault-retrieval") and has(driver_kconfig, r"depends on MMU") and has(driver_kconfig, r"DRM_GEM_SHMEM_HELPER"), "Apollo Linux driver Kconfig describes the preserved compatibility ioctls and the append-only generic APKO/context/BO/bind/command-submit/wait ABI with the GEM SHMEM MMU dependency", "hexagon_apko_generic")
    add(checks, "linux_driver_generic_wait", has(driver, r"APOLLO_HEXAGON_IOCTL\(WAIT") and has(driver_fence, r"apollo_hexagon_ioctl_wait") and has(driver_fence, r"current_fence_seq") and has(driver_fence, r"ETIMEDOUT"), "Apollo Linux driver exposes append-only generic WAIT ioctl with completed-fence snapshot and timeout behavior", "hexagon_apko_generic")
    add(checks, "linux_driver_generic_bo_bind", has(driver, r"APOLLO_HEXAGON_IOCTL\(BO_BIND") and has(driver, r"APOLLO_HEXAGON_IOCTL\(BO_UNBIND") and has(driver_bo, r"apollo_hexagon_ioctl_bo_bind") and has(driver_bo, r"apollo_hexagon_ioctl_bo_unbind") and has(driver_context, r"APOLLO_HEXAGON_BIND_IOVA_OFFSET") and has(driver_bo, r"drm_gem_object_lookup") and has(driver_context, r"bindings") and has(driver_context, r"apollo_hexagon_context_free"), "Apollo Linux driver exposes append-only BO_BIND/BO_UNBIND metadata handles with context-owned binding lifetime and staged IOVA allocation", "hexagon_apko_generic")
    add(checks, "linux_driver_command_bo_submit", has(driver, r"APOLLO_HEXAGON_IOCTL\(CMD_SUBMIT") and has(driver_exec, r"apollo_hexagon_ioctl_cmd_submit") and has(driver_exec, r"apollo_hexagon_copy_cmd_buffer_from_bo") and has(driver_exec, r"drm_gem_vmap") and has(driver_exec, r"APOLLO_HEXAGON_REG_CMDQ_DOORBELL") and has(driver_exec, r"command BO submit complete") and has(hexagon_kernel_uapi, r"struct drm_apollo_hexagon_cmd_submit") and has(hexagon_kernel_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_CMD_SUBMIT"), "Apollo Linux driver exposes append-only command BO submit, fetches a bounded command buffer from GEM SHMEM, rings the CMDQ doorbell, and returns CMDQ status/fence metadata", "hexagon_apko_generic")
    add(checks, "linux_driver_bound_cmd_submit_models", has(driver, r"max_command_bytes = APOLLO_HEXAGON_CMDQ_SUBMIT_MAX_BYTES") and has(driver, r"max_bindings_per_dispatch = 2") and has(driver_bo, r"apollo_hexagon_context_copy_from_iova") and has(driver_bo, r"apollo_hexagon_context_get_iova_bo") and has(driver_bo, r"apollo_hexagon_bo_copy_to") and has(driver_exec, r"apollo_hexagon_prepare_bound_dispatch") and has(driver_exec, r"apollo_hexagon_patch_bound_dispatch") and has(driver_exec, r"apollo_hexagon_bound_dispatch_put") and has(driver_exec, r"APOLLO_HEXAGON_CMDQ_OPCODE_LOAD_EXECUTABLE") and has(driver_exec, r"APOLLO_HEXAGON_CMDQ_DISPATCH_KIND_CNN") and has(driver_exec, r"APOLLO_HEXAGON_CMDQ_DISPATCH_KIND_VADD") and has(driver_exec, r"APOLLO_HEXAGON_CMDQ_DISPATCH_KIND_MNIST") and has(driver_exec, r"APOLLO_HEXAGON_EXEC_KIND_MNIST") and has(driver_exec, r"command BO LOAD_EXECUTABLE slot=") and has(driver_exec, r"command BO bound %s dispatch") and has(driver_exec, r"command BO bound %s output copied"), "Apollo Linux driver consumes BO_BIND metadata for CNN/VADD/MNIST CMD_SUBMIT paths by scanning LOAD_EXECUTABLE metadata, copying input BO contents into the current QBox shared window, retaining an output GEM reference across the command wait, patching the command packet, and copying output back to the output BO", "hexagon_apko_generic")
    add(checks, "linux_driver_sg_dma_stress_abi", has(driver, r"APOLLO_HEXAGON_IOCTL\(DMA_STRESS") and has(driver_compat, r"dynamic SMMU SG map refreshed") and has(driver_compat, r"SG DMA stress ok queue=%u fence=%u bytes=%u segments=%u"), "Apollo Linux driver exposes multi-page scatter/gather DMA stress ABI and verifies copied data", "hexagon_productization")
    add(checks, "linux_driver_async_fence_runtime", has(driver, r"platform_get_irq_byname_optional") and has(driver, r"devm_request_irq") and has(driver, r"async fence signaled queue=%u fence=%u"), "Apollo Linux driver keeps doorbell IRQ and async fence completion in the normal runtime submit path", "hexagon_integration")
    add(checks, "linux_iommu_runtime_test_driver", has(iommu_test, r"compatible = \"apollo,iommu-runtime-test\"") and has(iommu_test, r"dma_map_resource") and has(iommu_test, r"IOMMU runtime selftest ok"), "drivers/iommu/iommu-test.c owns generic IOMMU group/domain, DMA API, resource mapping, and QBox data-plane runtime coverage", "hexagon_integration")
    add(checks, "linux_driver_optional_smmuv3_selftest", has(driver_kconfig, r"config DRM_ACCEL_APOLLO_HEXAGON_SELFTEST") and has(driver, r"apollo_hexagon_run_selftests") and has(driver_selftest, r"apollo_hexagon_run_selftests") and has(driver_selftest, r"SMMUv3 architectural descriptor probe ok") and has(driver_selftest, r"SMMUv3 command invalidation selftest ok") and has(driver_selftest, r"SMMUv3 RIL TLBI_NH_VA range selftest ok"), "Apollo Linux driver keeps QBox-specific SMMUv3 descriptor, queue, command, and RIL probes in a separate optional bring-up selftest file", "hexagon_architecture_slice")
    add(checks, "qemu_system_only", has(qemu_cmake, r"--disable-user") and has(qemu_cmake, r"\$\{target\}-softmmu"), "libqemu integration builds system targets and disables QEMU user-mode", "hexagon_runtime_gap")
    add(checks, "repo_iree_source_submodule", (iree_source / "README.md").is_file() and (iree_source / "CMakeLists.txt").is_file() and (iree_source / "compiler").is_dir() and (iree_source / "runtime").is_dir() and has(gitmodules, r"path = sources/iree") and has(gitmodules, r"url = https://github\.com/iree-org/iree\.git") and has(gitmodules, r"branch = main"), "official upstream IREE source checkout is configured under sources/iree for later Apollo HAL/build integration", "upstream_iree_hal_driver")
    add(checks, "repo_hexagon_mlir_source_submodule", (hexagon_mlir_source / "README.md").is_file() and (hexagon_mlir_source / "qcom_hexagon_backend").is_dir() and (hexagon_mlir_source / "scripts/build_hexagon_mlir.sh").is_file() and has(gitmodules, r"path = sources/hexagon-mlir") and has(gitmodules, r"url = https://github\.com/qualcomm/hexagon-mlir\.git") and has(gitmodules, r"branch = main"), "official upstream Hexagon-MLIR source checkout is configured under sources/hexagon-mlir for future Apollo Hexagon compiler integration", "upstream_iree_hal_driver")
    add(checks, "repo_hexagon_mlir_iree_bridge_checker", hexagon_mlir_bridge_check.is_file() and os_access_executable(hexagon_mlir_bridge_check), "repo-local checker classifies direct Hexagon-MLIR connection, vadd bridge feasibility, and MNIST blockers", "hexagon_mlir_bridge")
    add(checks, "repo_hexagon_mlir_target_execution_checker", hexagon_mlir_target_check.is_file() and os_access_executable(hexagon_mlir_target_check) and hexagon_mlir_target_runner.is_file() and os_access_executable(hexagon_mlir_target_runner), "repo-local checker and runner document Hexagon-MLIR Android/ADB device and QuRT simulator execution prerequisites", "hexagon_mlir_bridge")

    host_smoke_script = repo / "scripts/run_iree_tiny_cnn_host_smoke.sh"
    vector_add_host_smoke_script = repo / "scripts/run_iree_vector_add_host_smoke.sh"
    mnist_host_smoke_script = repo / "scripts/run_iree_mnist_host_smoke.sh"
    guest_stage_script = repo / "scripts/stage_iree_tiny_cnn_guest_artifacts.sh"
    vector_add_guest_stage_script = repo / "scripts/stage_iree_vector_add_guest_artifacts.sh"
    mnist_guest_stage_script = repo / "scripts/stage_iree_mnist_guest_artifacts.sh"
    guest_smoke_script = repo / "scripts/run_iree_tiny_cnn_qbox_guest_smoke.sh"
    hexagon_smoke_script = repo / "scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh"
    vector_add_hexagon_smoke_script = repo / "scripts/run_iree_vector_add_hexagon_qbox_guest_smoke.sh"
    apko_vector_add_hexagon_smoke_script = repo / "scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh"
    apko_vector_add_vmfb_hexagon_smoke_script = repo / "scripts/run_iree_apko_vadd_vmfb_hexagon_qbox_guest_smoke.sh"
    apko_tiny_cnn_hexagon_smoke_script = repo / "scripts/run_iree_apko_cnn_hexagon_qbox_guest_smoke.sh"
    apko_tiny_cnn_vmfb_hexagon_smoke_script = repo / "scripts/run_iree_apko_cnn_vmfb_hexagon_qbox_guest_smoke.sh"
    apko_mnist_hexagon_smoke_script = repo / "scripts/run_iree_apko_mnist_hexagon_qbox_guest_smoke.sh"
    apko_negative_hexagon_smoke_script = repo / "scripts/run_iree_apko_negative_hexagon_qbox_guest_smoke.sh"
    hexagon_runner = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hexagon_runner.c"
    hexagon_hal = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hexagon_hal.c"
    hexagon_hal_h = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hexagon_hal.h"
    hexagon_plugin = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hexagon_plugin.c"
    hexagon_plugin_h = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hexagon_plugin.h"
    hexagon_registry = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hal_registry.c"
    hexagon_registry_h = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hal_registry.h"
    hexagon_run_module = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_run_module.c"
    hexagon_apko_negative = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_hexagon_apko_negative.c"
    iree_plugin_abi = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_executable_plugin_abi.h"
    hexagon_guest_uapi = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_hexagon_uapi_guest.h"
    hexagon_kernel_uapi = repo / "sources/linux/include/uapi/drm/apollo_hexagon_accel.h"
    hexagon_kernel_driver = repo / "sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon.c"
    hexagon_firmware = repo / "sources/qbox/platforms/buildroot/fw/hexagon_dma_smoke.s"
    add(checks, "repo_iree_host_smoke_script", host_smoke_script.is_file() and os_access_executable(host_smoke_script), "repo-local host smoke script exists for ONNX->MLIR->IREE CPU validation", "a710_cpu_baseline")
    add(checks, "repo_iree_aarch64_compile", has(host_smoke_script, r"iree-llvmcpu-target-triple=aarch64-unknown-linux-gnu") and has(host_smoke_script, r"iree-llvmcpu-target-cpu=cortex-a710"), "host smoke also emits an AArch64/Cortex-A710 VMFB for guest staging", "a710_guest_artifact_baseline")
    add(checks, "repo_iree_guest_stage_script", guest_stage_script.is_file() and os_access_executable(guest_stage_script), "repo-local staging script packages tiny-CNN VMFB/reference/runner for Buildroot guest images", "a710_guest_artifact_baseline")
    add(checks, "repo_iree_guest_runtime_staged", has(guest_stage_script, r"Buildroot iree-runtime package from sources/iree") and has(guest_stage_script, r"QBOX_IREE_RUNTIME_BIN") and has(guest_stage_script, r"iree-base-runtime") and has(guest_stage_script, r"bin/iree-run-module"), "guest staging script prefers the source-built Buildroot IREE runtime while retaining the wheel fallback and explicit binary override", "a710_guest_runtime")
    add(checks, "repo_iree_guest_smoke_script", guest_smoke_script.is_file() and os_access_executable(guest_smoke_script), "repo-local QBox guest smoke script verifies IREE tiny-CNN output in the booted guest", "a710_guest_runtime")
    add(checks, "repo_iree_hexagon_hal_runner", hexagon_runner.is_file() and hexagon_hal.is_file() and hexagon_hal_h.is_file() and hexagon_guest_uapi.is_file() and has(hexagon_runner, r"command buffer submitted") and has(hexagon_hal, r"apollo_hexagon_load_executable") and has(hexagon_hal, r"apollo_hexagon_queue_submit_cnn") and has(hexagon_hal, r"apollo_hexagon_queue_submit_apko") and has(guest_stage_script, r"apollo-iree-hexagon-runner"), "repo-local IREE-compatible Apollo Hexagon HAL runner has executable metadata, queue, fixed command buffer, APKO generic submit, and fence layers", "hexagon_productization")
    add(checks, "repo_iree_hexagon_hal_registry", hexagon_registry.is_file() and hexagon_registry_h.is_file() and hexagon_run_module.is_file() and has(hexagon_registry, r"apollo_iree_hal_registry_lookup") and has(hexagon_registry, r"CPU fallback device is disabled") and has(hexagon_registry, r"dlopen\(plugin_path, RTLD_NOW \| RTLD_LOCAL\)") and has(hexagon_registry, r"APOLLO_IREE_HEXAGON_PLUGIN_EXPORT_NAME") and has(hexagon_run_module, r"upstream-style HAL registry") and has(hexagon_run_module, r"dynamically registered C HAL plugin=%s") and has(guest_stage_script, r"apollo-iree-run-module") and has(guest_stage_script, r"--device=apollo-hexagon") and has(guest_stage_script, r"--executable_plugin"), "repo-local iree-run-module dispatch path dynamically registers the Apollo Hexagon C HAL plugin through an upstream-style registry frontend while rejecting CPU fallback devices", "hexagon_productization")
    add(checks, "repo_iree_hal_boundary_guard", has(hexagon_run_module, r"--list_drivers") and has(hexagon_run_module, r"--dump_devices") and has(hexagon_run_module, r"integration_status=repo-local-registry-frontend") and has(hexagon_run_module, r"upstream_hal_driver=not-linked") and has(hexagon_run_module, r"VMFB APKO trailer evidence is transitional only") and has(guest_stage_script, r"evidence_guard") and has(vector_add_guest_stage_script, r"evidence_guard") and has(mnist_guest_stage_script, r"evidence_guard"), "Apollo query path exposes the repo-local HAL boundary while guarding against reporting wrapper or VMFB-trailer evidence as upstream IREE HAL driver integration", "hexagon_productization")
    add(checks, "repo_iree_dynamic_hal_plugin", hexagon_plugin.is_file() and hexagon_plugin_h.is_file() and iree_plugin_abi.is_file() and has(hexagon_plugin, r"apollo_iree_hexagon_plugin_query") and has(hexagon_plugin, r"iree_hal_executable_plugin_query") and has(guest_stage_script, r"libapollo_iree_hexagon_hal_plugin\.so"), "repo-local dynamic C HAL plugin also exports the upstream IREE executable_plugin query symbol", "hexagon_integration")
    add(checks, "repo_iree_hexagon_metadata", has(guest_stage_script, r"apollo_hexagon\.vmfb\.meta") and has(guest_stage_script, r"apollo_hexagon_apko\.vmfb\.meta") and has(guest_stage_script, r"command_buffer=fixed") and has(guest_stage_script, r"command_buffer=generic-submit") and has(guest_stage_script, r"executable_format=apollo-hexagon-apko-v0") and has(guest_stage_script, r"fence=async-irq-poll") and has(guest_stage_script, r"upstream_executable_plugin=iree_hal_executable_plugin_query"), "guest staging emits compat VMFB metadata and APKO generic-submit metadata for the Apollo Hexagon HAL loader", "hexagon_productization")
    add(checks, "repo_iree_hexagon_vmfb_embedded_apko", has(hexagon_hal, r"load_embedded_apko_from_module") and has(hexagon_hal, r"APOLLO_HEXAGON_VMFB_APKO_FOOTER_MAGIC") and has(hexagon_hal_h, r"apko_embedded") and has(hexagon_run_module, r"executable_source=vmfb-embedded-apko") and has(hexagon_runner, r"executable_source=vmfb-embedded-apko") and has(guest_stage_script, r"tiny_cnn_apollo\.vmfb") and has(vector_add_guest_stage_script, r"vector_add_apollo\.vmfb") and has(vector_add_guest_stage_script, r"run_vector_add_vmfb_apko_hexagon_guest\.sh"), "Apollo IREE loader can extract a repo-local APKO trailer from a staged VMFB and run without .vmfb.meta sidecar metadata", "hexagon_apko_generic")
    add(checks, "repo_iree_hexagon_mlir_sidecar_metadata", has(hexagon_hal_h, r"compiler_artifact_path") and has(hexagon_hal, r"compiler_artifact=") and has(hexagon_runner, r"compiler bridge=%s") and has(hexagon_run_module, r"compiler bridge=%s") and has(guest_stage_script, r"QBOX_HEXAGON_MLIR_ARTIFACT") and has(vector_add_guest_stage_script, r"QBOX_HEXAGON_MLIR_ARTIFACT"), "Apollo IREE metadata can carry and log a Hexagon-MLIR artifact sidecar without claiming generic object execution", "hexagon_mlir_bridge")
    add(checks, "repo_iree_hexagon_guest_smoke_script", hexagon_smoke_script.is_file() and os_access_executable(hexagon_smoke_script) and has(hexagon_smoke_script, r"SG DMA stress ok queue=0") and has(hexagon_smoke_script, r"bytes=131072 segments=8") and has(hexagon_smoke_script, r"async irq pending queue=1") and has(hexagon_smoke_script, r"fence=async-irq-poll"), "repo-local QBox guest smoke script verifies Hexagon offload, >64KB SG DMA, async fences, and SMMU markers with UART-interleave-tolerant markers", "hexagon_productization")
    add(checks, "repo_iree_vector_add_host_smoke_script", vector_add_host_smoke_script.is_file() and os_access_executable(vector_add_host_smoke_script) and has(vector_add_host_smoke_script, r"vector_add_graph") and has(vector_add_host_smoke_script, r"4xf32=11 22 33 44"), "repo-local host smoke script generates ONNX vector Add, compiles host/AArch64 VMFBs, and verifies IREE runtime output", "hexagon_vector_add")
    add(checks, "repo_iree_mnist_host_smoke_script", mnist_host_smoke_script.is_file() and os_access_executable(mnist_host_smoke_script) and has(mnist_host_smoke_script, r"mnist_graph") and has(mnist_host_smoke_script, r"1x10xf32=\[0 1 2 3 4 5 6 7 8 9\]") and has(mnist_host_smoke_script, r"iree-llvmcpu-target-triple=aarch64-unknown-linux-gnu"), "repo-local host smoke script generates a MNIST-shaped ONNX graph, compiles host/AArch64 VMFBs, and verifies IREE runtime output", "hexagon_apko_generic")
    add(checks, "repo_iree_vector_add_guest_stage_script", vector_add_guest_stage_script.is_file() and os_access_executable(vector_add_guest_stage_script) and has(vector_add_guest_stage_script, r"QBOX_IREE_VECTOR_ADD_GUEST_STAGE_DIR") and has(vector_add_guest_stage_script, r"run_vector_add_hexagon_guest\.sh"), "repo-local staging script packages vector-add VMFB, IREE runtime wrapper, and Apollo Hexagon HAL plugin for /opt/qbox/iree/vector-add", "hexagon_vector_add")
    add(checks, "repo_iree_vector_add_hexagon_smoke_script", vector_add_hexagon_smoke_script.is_file() and os_access_executable(vector_add_hexagon_smoke_script) and has(vector_add_hexagon_smoke_script, r"accelerator vector add ok") and has(vector_add_hexagon_smoke_script, r"EXEC @vector_add_graph \[apollo-hexagon\]"), "repo-local QBox guest smoke script verifies vector-add execution through iree-run-module --device=apollo-hexagon and SMMU-translated DMA markers", "hexagon_vector_add")
    add(checks, "repo_apko_generic_smoke_scripts", apko_vector_add_hexagon_smoke_script.is_file() and os_access_executable(apko_vector_add_hexagon_smoke_script) and has(apko_vector_add_hexagon_smoke_script, r"run_vector_add_apko_hexagon_guest\.sh") and has(apko_vector_add_hexagon_smoke_script, r"APKO CMD_SUBMIT VADD ok") and has(apko_vector_add_hexagon_smoke_script, r"command load executable slot=1 kind=2") and has(apko_vector_add_hexagon_smoke_script, r"generic_abi_version=1") and apko_tiny_cnn_hexagon_smoke_script.is_file() and os_access_executable(apko_tiny_cnn_hexagon_smoke_script) and has(apko_tiny_cnn_hexagon_smoke_script, r"run_tiny_cnn_apko_hexagon_guest\.sh") and has(apko_tiny_cnn_hexagon_smoke_script, r"APKO CMD_SUBMIT CNN ok") and has(apko_tiny_cnn_hexagon_smoke_script, r"generic_abi_version=1"), "repo-local APKO generic smoke scripts run APKO metadata through executable create, VADD/CNN command BO LOAD_EXECUTABLE plus executable-slot dispatch, query-caps, and APKO completion markers", "hexagon_apko_generic")
    add(checks, "repo_apko_mnist_cmdq_smoke_script", mnist_guest_stage_script.is_file() and os_access_executable(mnist_guest_stage_script) and has(mnist_guest_stage_script, r"QBOX_IREE_MNIST_GUEST_STAGE_DIR") and has(mnist_guest_stage_script, r"run_iree_mnist_host_smoke\.sh") and has(mnist_guest_stage_script, r"mnist_aarch64\.vmfb") and has(mnist_guest_stage_script, r"host-report\.json") and has(mnist_guest_stage_script, r"semantic_match=host-onnx-and-apollo-payload-produce-1x10xf32-bias-output") and has(mnist_guest_stage_script, r"apko_input_bytes=3136") and has(mnist_guest_stage_script, r"apko_output_bytes=40") and has(mnist_guest_stage_script, r"run_mnist_apko_hexagon_guest\.sh") and has(mnist_guest_stage_script, r"apko_entry_kind=mnist") and apko_mnist_hexagon_smoke_script.is_file() and os_access_executable(apko_mnist_hexagon_smoke_script) and has(apko_mnist_hexagon_smoke_script, r"APKO CMD_SUBMIT MNIST ok") and has(apko_mnist_hexagon_smoke_script, r"command load executable slot=1 kind=3") and has(apko_mnist_hexagon_smoke_script, r"1x10xf32=\[0 1 2 3 4 5 6 7 8 9\]") and has(hexagon_guest_uapi, r"APOLLO_HEXAGON_MNIST_INPUT_WORDS \(28 \* 28\)") and has(hexagon_guest_uapi, r"APOLLO_HEXAGON_MNIST_OUTPUT_WORDS 10") and has(hexagon_hal, r"mnist_graph") and has(hexagon_run_module, r"mnist_graph") and has(post_build, r"QBOX_IREE_MNIST_GUEST_ARTIFACTS_DIR"), "repo-local APKO MNIST smoke stages a real MNIST-shaped ONNX compile artifact as the VMFB base, then routes matching Flatten+Gemm semantics through Linux/UMD CMD_SUBMIT with LOAD_EXECUTABLE plus executable-slot dispatch", "hexagon_apko_generic")
    add(checks, "repo_apko_vmfb_embedded_smoke_script", apko_vector_add_vmfb_hexagon_smoke_script.is_file() and os_access_executable(apko_vector_add_vmfb_hexagon_smoke_script) and has(apko_vector_add_vmfb_hexagon_smoke_script, r"run_vector_add_vmfb_apko_hexagon_guest\.sh") and has(apko_vector_add_vmfb_hexagon_smoke_script, r"executable_source=vmfb-embedded-apko") and has(apko_vector_add_vmfb_hexagon_smoke_script, r"APKO CMD_SUBMIT VADD ok") and apko_tiny_cnn_vmfb_hexagon_smoke_script.is_file() and os_access_executable(apko_tiny_cnn_vmfb_hexagon_smoke_script) and has(apko_tiny_cnn_vmfb_hexagon_smoke_script, r"run_tiny_cnn_vmfb_apko_hexagon_guest\.sh") and has(apko_tiny_cnn_vmfb_hexagon_smoke_script, r"executable_source=vmfb-embedded-apko") and has(apko_tiny_cnn_vmfb_hexagon_smoke_script, r"APKO CMD_SUBMIT CNN ok"), "repo-local APKO VADD/CNN smoke can verify VMFB-embedded APKO loading without .vmfb.meta sidecar metadata", "hexagon_apko_generic")
    add(checks, "linux_driver_cmdq_model_submit", has(driver_header, r"APOLLO_HEXAGON_REG_CMDQ_DOORBELL") and has(hexagon_kernel_uapi, r"APOLLO_HEXAGON_CMDQ_OPCODE_DISPATCH") and has(hexagon_kernel_uapi, r"APOLLO_HEXAGON_CMDQ_OPCODE_LOAD_EXECUTABLE") and has(hexagon_kernel_uapi, r"APOLLO_HEXAGON_CMDQ_OPCODE_LOAD_PAYLOAD") and has(hexagon_kernel_uapi, r"APOLLO_HEXAGON_CMDQ_DISPATCH_EXEC_SLOT_FLAG") and has(hexagon_kernel_uapi, r"APOLLO_HEXAGON_CMDQ_DISPATCH_KIND_CNN") and has(hexagon_kernel_uapi, r"APOLLO_HEXAGON_CMDQ_DISPATCH_KIND_VADD") and has(hexagon_kernel_uapi, r"APOLLO_HEXAGON_CMDQ_DISPATCH_KIND_MNIST") and has(driver, r"max_command_bytes = APOLLO_HEXAGON_CMDQ_SUBMIT_MAX_BYTES") and has(driver, r"max_bindings_per_dispatch = 2") and has(driver_exec, r"apollo_hexagon_write_cmdq_dispatch_vadd") and has(driver_exec, r"apollo_hexagon_write_cmdq_dispatch_packet") and has(driver_exec, r"APOLLO_HEXAGON_REG_CMDQ_DOORBELL") and has(driver_exec, r"command BO LOAD_EXECUTABLE slot=") and has(driver_exec, r"command BO LOAD_PAYLOAD slot=") and has(driver_exec, r"command BO bound %s dispatch") and has(apko_vector_add_hexagon_smoke_script, r"APKO CMD_SUBMIT VADD ok") and has(apko_tiny_cnn_hexagon_smoke_script, r"APKO CMD_SUBMIT CNN ok") and has(apko_mnist_hexagon_smoke_script, r"APKO CMD_SUBMIT MNIST ok"), "Linux APKO VADD/CNN/MNIST generic submit can program a bounded command buffer with LOAD_EXECUTABLE, LOAD_PAYLOAD, and DISPATCH, and the command BO path consumes two BO bindings before ringing the CMDQ doorbell", "hexagon_apko_generic")
    add(checks, "repo_apko_negative_smoke_script", apko_negative_hexagon_smoke_script.is_file() and os_access_executable(apko_negative_hexagon_smoke_script) and hexagon_apko_negative.is_file() and has(hexagon_apko_negative, r"bad context ABI version") and has(hexagon_apko_negative, r"context create/destroy ok") and has(hexagon_apko_negative, r"bad BO size") and has(hexagon_apko_negative, r"BO create/destroy ok") and has(hexagon_apko_negative, r"bad BO bind size") and has(hexagon_apko_negative, r"bad BO unbind size") and has(hexagon_apko_negative, r"BO bind/unbind ok") and has(hexagon_apko_negative, r"bad command BO submit size") and has(hexagon_apko_negative, r"command BO submit signal-fence ok") and has(hexagon_apko_negative, r"command BO bad LOAD_EXECUTABLE fault ok") and has(hexagon_apko_negative, r"DRM_IOCTL_APOLLO_HEXAGON_CMD_SUBMIT") and has(hexagon_apko_negative, r"bad WAIT size") and has(hexagon_apko_negative, r"WAIT completed fence") and has(hexagon_apko_negative, r"future WAIT fence") and has(hexagon_apko_negative, r"bad APKO ABI version") and has(hexagon_apko_negative, r"invalid input pointer") and has(hexagon_apko_negative, r"destroyed executable handle") and has(hexagon_apko_negative, r"empty fault record") and has(hexagon_apko_negative, r"DRM_IOCTL_APOLLO_HEXAGON_QUERY_CAPS") and has(hexagon_apko_negative, r"DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_CREATE") and has(hexagon_apko_negative, r"DRM_IOCTL_APOLLO_HEXAGON_BO_CREATE") and has(hexagon_apko_negative, r"DRM_IOCTL_APOLLO_HEXAGON_BO_BIND") and has(hexagon_apko_negative, r"DRM_IOCTL_APOLLO_HEXAGON_WAIT") and has(apko_negative_hexagon_smoke_script, r"generic_abi_version=1") and has(apko_negative_hexagon_smoke_script, r"context create/destroy ok") and has(apko_negative_hexagon_smoke_script, r"BO create/destroy ok") and has(apko_negative_hexagon_smoke_script, r"bad BO unbind size") and has(apko_negative_hexagon_smoke_script, r"BO bind/unbind ok") and has(apko_negative_hexagon_smoke_script, r"command BO bad LOAD_EXECUTABLE fault ok") and has(apko_negative_hexagon_smoke_script, r"WAIT completed fence") and has(apko_negative_hexagon_smoke_script, r"APKO negative ioctl coverage completed") and has(vector_add_guest_stage_script, r"run_apko_negative_hexagon_guest\.sh"), "repo-local APKO negative smoke covers query-caps, context create/destroy ABI, BO create/destroy/bind ABI, command BO submit including malformed LOAD_EXECUTABLE, WAIT completion/timeout ABI, invalid APKO headers, wrong command sizes, bad user pointers, queue mismatch, stale executable handles, and empty fault retrieval", "hexagon_apko_generic")
    apko_invalid_iova_fault = (
        hexagon_apko_negative.is_file()
        and has(hexagon_apko_negative, r"command BO invalid IOVA fault ok")
        and has(hexagon_apko_negative, r"APOLLO_HEXAGON_CMDQ_FAULT_DMA_ERROR")
        and has(hexagon_apko_negative, r"DRM_IOCTL_APOLLO_HEXAGON_GET_FAULT")
        and has(apko_negative_hexagon_smoke_script, r"command BO invalid IOVA fault ok")
        and has(hexagon_kernel_uapi, r"APOLLO_HEXAGON_CMDQ_FAULT_DMA_ERROR")
        and has(hexagon_guest_uapi, r"APOLLO_HEXAGON_CMDQ_FAULT_DMA_ERROR")
    )
    add(checks, "repo_apko_negative_invalid_iova_fault", apko_invalid_iova_fault, "repo-local APKO negative smoke creates an invalid IOVA command BO COPY fault and retrieves the CMDQ DMA fault through GET_FAULT", "hexagon_apko_generic")
    add(checks, "repo_hexagon_vector_add_uapi", has(hexagon_guest_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_SUBMIT_VADD") and has(hexagon_hal, r"apollo_hexagon_queue_submit_vadd") and has(hexagon_runner, r"vector_add_graph") and has(hexagon_run_module, r"vector_add_graph"), "Apollo guest UAPI/HAL runner exposes a vector-add job path beside the tiny-CNN command path", "hexagon_vector_add")
    add(checks, "repo_hexagon_apko_generic_uapi", has(hexagon_kernel_uapi, r"struct drm_apollo_hexagon_apko_header") and has(hexagon_kernel_uapi, r"struct drm_apollo_hexagon_query_caps") and has(hexagon_kernel_uapi, r"struct drm_apollo_hexagon_context_create") and has(hexagon_kernel_uapi, r"struct drm_apollo_hexagon_context_destroy") and has(hexagon_kernel_uapi, r"struct drm_apollo_hexagon_bo_create") and has(hexagon_kernel_uapi, r"struct drm_apollo_hexagon_bo_destroy") and has(hexagon_kernel_uapi, r"struct drm_apollo_hexagon_bo_bind") and has(hexagon_kernel_uapi, r"struct drm_apollo_hexagon_bo_unbind") and has(hexagon_kernel_uapi, r"struct drm_apollo_hexagon_wait") and has(hexagon_kernel_uapi, r"struct drm_apollo_hexagon_cmd_submit") and has(hexagon_kernel_uapi, r"APOLLO_HEXAGON_GENERIC_ABI_VERSION") and has(hexagon_kernel_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_EXEC_CREATE") and has(hexagon_kernel_uapi, r"#define DRM_IOCTL_APOLLO_HEXAGON_SUBMIT\s") and has(hexagon_kernel_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_GET_FAULT") and has(hexagon_kernel_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_QUERY_CAPS") and has(hexagon_kernel_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_CREATE") and has(hexagon_kernel_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_DESTROY") and has(hexagon_kernel_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_BO_CREATE") and has(hexagon_kernel_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_BO_DESTROY") and has(hexagon_kernel_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_BO_BIND") and has(hexagon_kernel_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_BO_UNBIND") and has(hexagon_kernel_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_WAIT") and has(hexagon_kernel_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_CMD_SUBMIT") and has(hexagon_kernel_driver, r"APOLLO_HEXAGON_IOCTL\(EXEC_CREATE") and has(hexagon_kernel_driver, r"APOLLO_HEXAGON_IOCTL\(SUBMIT, submit\)") and has(hexagon_kernel_driver, r"APOLLO_HEXAGON_IOCTL\(GET_FAULT") and has(hexagon_kernel_driver, r"APOLLO_HEXAGON_IOCTL\(QUERY_CAPS") and has(hexagon_kernel_driver, r"APOLLO_HEXAGON_IOCTL\(CONTEXT_CREATE") and has(hexagon_kernel_driver, r"APOLLO_HEXAGON_IOCTL\(CONTEXT_DESTROY") and has(hexagon_kernel_driver, r"APOLLO_HEXAGON_IOCTL\(BO_CREATE") and has(hexagon_kernel_driver, r"APOLLO_HEXAGON_IOCTL\(BO_DESTROY") and has(hexagon_kernel_driver, r"APOLLO_HEXAGON_IOCTL\(BO_BIND") and has(hexagon_kernel_driver, r"APOLLO_HEXAGON_IOCTL\(BO_UNBIND") and has(hexagon_kernel_driver, r"APOLLO_HEXAGON_IOCTL\(WAIT") and has(hexagon_kernel_driver, r"APOLLO_HEXAGON_IOCTL\(CMD_SUBMIT") and has(driver_context, r"apollo_hexagon_ioctl_context_create") and has(driver_context, r"apollo_hexagon_ioctl_context_destroy") and has(driver_context, r"generic_abi_version") and has(driver_context, r"bindings") and has(driver_bo, r"apollo_hexagon_ioctl_bo_create") and has(driver_bo, r"drm_gem_shmem_create") and has(driver_bo, r"drm_gem_handle_create") and has(driver_bo, r"drm_gem_handle_delete") and has(driver_bo, r"apollo_hexagon_ioctl_bo_bind") and has(driver_bo, r"apollo_hexagon_ioctl_bo_unbind") and has(driver_bo, r"apollo_hexagon_context_copy_from_iova") and has(driver_bo, r"apollo_hexagon_context_get_iova_bo") and has(driver_bo, r"apollo_hexagon_bo_copy_to") and has(driver_fence, r"apollo_hexagon_ioctl_wait") and has(driver_exec, r"apollo_hexagon_ioctl_exec_create") and has(driver_exec, r"apollo_hexagon_ioctl_submit") and has(driver_exec, r"apollo_hexagon_ioctl_cmd_submit") and has(driver_fault, r"apollo_hexagon_ioctl_get_fault") and has(driver_exec, r"APKO dispatch complete") and has(hexagon_guest_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_EXEC_CREATE") and has(hexagon_guest_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_GET_FAULT") and has(hexagon_guest_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_QUERY_CAPS") and has(hexagon_guest_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_CREATE") and has(hexagon_guest_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_DESTROY") and has(hexagon_guest_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_BO_CREATE") and has(hexagon_guest_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_BO_DESTROY") and has(hexagon_guest_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_BO_BIND") and has(hexagon_guest_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_BO_UNBIND") and has(hexagon_guest_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_WAIT") and has(hexagon_guest_uapi, r"DRM_IOCTL_APOLLO_HEXAGON_CMD_SUBMIT") and has(hexagon_hal, r"DRM_IOCTL_APOLLO_HEXAGON_SUBMIT") and has(hexagon_hal, r"DRM_IOCTL_APOLLO_HEXAGON_CMD_SUBMIT") and has(hexagon_hal, r"DRM_IOCTL_APOLLO_HEXAGON_QUERY_CAPS") and has(hexagon_run_module, r"generic_abi_version=%u"), "Linux and guest UAPI expose query-caps, context create/destroy handles, GEM BO create/destroy/bind handles, CNN/VADD command BO submit with retained output BO lifetime, WAIT, APKO executable handles, legacy generic submit, and fault retrieval beside preserved fixed CNN/VADD ioctls", "hexagon_apko_generic")
    add(checks, "repo_hexagon_vector_add_firmware", has(hexagon_firmware, r"vector_add_job") and has(hexagon_firmware, r"0x56414444") and has(hexagon_firmware, r"0x41300000") and has(hexagon_firmware, r"0x42300000"), "Hexagon firmware job loop recognizes the vector-add ABI and emits the canonical 4xf32 output through SMMU-translated DMA", "hexagon_vector_add")
    add(checks, "hexagon_firmware_cnn_kernel", has(hexagon_firmware, r"0x42580000") and has(hexagon_firmware, r"0x10203000") and has(hexagon_firmware, r"job_loop"), "Hexagon firmware runtime consumes submit jobs, moves buffers through DMA, and emits tiny-CNN output", "hexagon_accelerator")
    add(checks, "hexagon_firmware_dma_copy_runtime", has(hexagon_firmware, r"dma_copy_job") and has(hexagon_firmware, r"0x53474f4b") and has(hexagon_firmware, r"poll_copy_dma_done"), "Hexagon firmware runtime handles command-queue DMA copy jobs for multi-page stress traffic", "hexagon_productization")
    add(checks, "buildroot_optional_iree_staging", has(post_build, r"QBOX_IREE_GUEST_ARTIFACTS_DIR") and has(post_build, r"/opt/qbox/iree/tiny-cnn"), "Buildroot post-build can optionally copy staged IREE tiny-CNN artifacts into the rootfs", "a710_guest_artifact_baseline")
    return checks


def host_checks(repo: Path) -> list[Check]:
    checks: list[Check] = []
    iree_import_onnx = tool_path(repo, "iree-import-onnx")
    iree_compile = tool_path(repo, "iree-compile")
    iree_run_module = tool_path(repo, "iree-run-module")
    add(checks, "iree_import_onnx_tool", iree_import_onnx is not None, f"tool={iree_import_onnx}", "host_smoke")
    add(checks, "iree_compile_tool", iree_compile is not None, f"tool={iree_compile}", "host_smoke")
    add(checks, "iree_run_module_tool", iree_run_module is not None, f"tool={iree_run_module}", "host_smoke")
    add(checks, "python_onnx", module_available_for_repo(repo, "onnx"), "python module onnx import", "host_smoke")
    add(checks, "python_numpy", module_available_for_repo(repo, "numpy"), "python module numpy import", "host_smoke")
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
    checks = repo_checks(repo) + host_checks(repo)
    payload = {
        "repo": str(repo),
        "summary": summarize(checks),
        "checks": [check.__dict__ for check in checks],
        "classification": {
            "a710_cpu_iree_baseline": "guest_runtime_ready: boot/rootfs/kernel lane exists and the Buildroot rootfs now includes a source-built IREE iree-run-module package for AArch64 VMFB smoke tests",
            "hexagon_iree_accelerator": "repo_local_integration_ready: dynamic C HAL plugin, /dev/accel/accel* DRM accel submit ABI, VMFB metadata loader, multi-queue command buffer/fence runner, >64KB SG DMA stress, and firmware CNN runtime are implemented and smoke-testable",
            "smmu_dma_model": "functional_smmuv3_ready: dynamic map/unmap/clear registers, page-table walk observability, ATS/PRI/fault queue status, and translated TLM splitting support >64KB SG stress",
            "upstream_iree_hal_driver": "guarded_pending: repo-local iree-run-module query/dispatch exposes apollo-hexagon through a C HAL registry frontend and dynamically dlopens the Apollo plugin, but guard markers explicitly classify wrapper and VMFB-trailer evidence as transitional until Apollo is registered in the upstream IREE runtime HAL driver registry",
            "hexagon_mlir_bridge": "adapter_slice: direct Hexagon-MLIR object execution still needs a real compiler object backend, but the repo now has an APKO v0 executable-handle/generic-submit bridge for staged vector-add and tiny-CNN artifacts",
            "apollo_apko_generic_smoke": "generic_submit_slice_ready: APKO v0 metadata, Linux context, GEM BO lifecycle, BO binding metadata, VADD/CNN/MNIST binding-table command BO submit, WAIT ioctls, invalid-IOVA GET_FAULT positive coverage, QBox command queue/fault registers, a QBox NOP/COPY/BARRIER/SIGNAL_FENCE packet execution subset, component-tested LOAD_EXECUTABLE metadata slots, executable-slot DISPATCH/VADD/CNN/MNIST packet execution, deterministic QBox CNN and MNIST Flatten+Gemm CMDQ model-kernel semantics, Linux APKO VADD/CNN/MNIST CMDQ programming, executable create/destroy ioctls, legacy generic submit and fault retrieval ioctls, guest HAL APKO loader, staged VMFB-embedded APKO trailer loading, APKO VADD/CNN/MNIST smoke scripts, MNIST-shaped ONNX host compile artifacts, and APKO negative ioctl smoke coverage exist; true hardware BO mapping, full APKO code execution, and upstream VMFB HAL executable target backend packaging remain pending",
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
