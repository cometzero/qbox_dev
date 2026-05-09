#!/usr/bin/env python3
"""Check Apollo QBox readiness for an IREE tiny-CNN pipeline.

This is intentionally split into:
  * host/tooling checks for ONNX -> MLIR -> IREE CPU execution,
  * repo contract checks for the current A710 Linux boot lane, and
  * repo gap checks for a future Hexagon accelerator/HAL path.

It does not claim Hexagon IREE support.  Instead, it produces machine-readable
classification so later work can turn missing items into concrete tasks.
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
    driver = repo / "sources/linux/drivers/soc/apollo/apollo-hexagon-test.c"
    qemu_cmake = repo / "sources/qemu/qemu.cmake"

    add(checks, "buildroot_rootfs_only", has(buildroot_defconfig, r"^BR2_TARGET_ROOTFS_CPIO=y$") and not has(buildroot_defconfig, r"^BR2_LINUX_KERNEL"), "Buildroot defconfig builds rootfs/initramfs and excludes kernel build", "a710_cpu_baseline")
    add(checks, "buildroot_cxx_runtime", has(buildroot_defconfig, r"^BR2_TOOLCHAIN_BUILDROOT_CXX=y$") and has(buildroot_defconfig, r"^BR2_INSTALL_LIBSTDCPP=y$"), "Buildroot defconfig enables C++ and installs libstdc++ required by the IREE runner", "a710_guest_runtime")
    add(checks, "standalone_linux_builder", has(linux_script, r"sources/linux") and has(linux_script, r"\bImage\b") and has(linux_script, r"ccache"), "standalone Linux Image build script uses sources/linux and ccache", "a710_cpu_baseline")
    add(checks, "a710_linux_config", has(linux_config, r"^CONFIG_ARM_SMMU_V3=y$") and has(linux_config, r"^CONFIG_APOLLO_HEXAGON_TEST=y$"), "Linux config fragment enables ARM SMMUv3 and Apollo Hexagon test driver; ARCH=arm64 is supplied by build script", "a710_cpu_baseline")
    add(checks, "apollo_hexagon_dt_binding", has(dts, r"compatible = \"apollo,hexagon-ip\"") and has(dts, r"iommus = <&smmu 0x1>") and has(dts, r"apollo,dma-path = \"smmu-translated\""), "DTS exposes Apollo Hexagon node behind SMMU with smmu-translated DMA contract", "hexagon_dma_smoke")
    add(checks, "qbox_hexagon_modules", has(platform_script, r"qemu_cpu_hexagon") and has(platform_script, r"apollo_hexagon_dma") and has(platform_script, r"apollo_smmu_tbu"), "QBox platform build includes Hexagon CPU, DMA, and Apollo SMMU TBU modules", "hexagon_dma_smoke")
    add(checks, "runtime_module_guards", has(run_script, r"qemu_cpu_hexagon\.so") and has(run_script, r"apollo_hexagon_dma\.so") and has(run_script, r"apollo_smmu_tbu\.so"), "boot runner verifies Hexagon/SMMU runtime modules before launch", "hexagon_dma_smoke")
    add(checks, "translated_tlm_binding", has(platform, r"translated_dma = \{bind = \"&hexagon_smmu_tbu_0\.upstream\"\}") and has(platform, r"smmu_translated = true"), "Apollo Lua platform routes Hexagon DMA through SMMU-translated TLM path", "hexagon_dma_smoke")
    add(checks, "fixed_window_tbu", has(tbu, r"iova_base") and has(tbu, r"pa_base") and has(tbu, r"window_size") and has(tbu, r"TLM_ADDRESS_ERROR_RESPONSE"), "Apollo SMMU TBU supports fixed-window IOVA->PA translation and TLM address faults", "hexagon_dma_smoke")
    add(checks, "dma_smoke_limit", has(dma, r"m_len > 4096"), "Apollo Hexagon DMA intentionally limits smoke transfers to 4096 bytes", "hexagon_accelerator_gap")
    add(checks, "linux_driver_is_test_probe", has(driver, r"firmware dma traffic ok") and not has(driver, r"unlocked_ioctl|\.mmap|misc_register|cdev"), "Apollo Linux driver validates boot-time firmware DMA but exposes no user runtime submit ABI", "hexagon_accelerator_gap")
    add(checks, "qemu_system_only", has(qemu_cmake, r"--disable-user") and has(qemu_cmake, r"\$\{target\}-softmmu"), "libqemu integration builds system targets and disables QEMU user-mode", "hexagon_runtime_gap")

    host_smoke_script = repo / "scripts/run_iree_tiny_cnn_host_smoke.sh"
    guest_stage_script = repo / "scripts/stage_iree_tiny_cnn_guest_artifacts.sh"
    guest_smoke_script = repo / "scripts/run_iree_tiny_cnn_qbox_guest_smoke.sh"
    add(checks, "repo_iree_host_smoke_script", host_smoke_script.is_file() and os_access_executable(host_smoke_script), "repo-local host smoke script exists for ONNX->MLIR->IREE CPU validation", "a710_cpu_baseline")
    add(checks, "repo_iree_aarch64_compile", has(host_smoke_script, r"iree-llvmcpu-target-triple=aarch64-unknown-linux-gnu") and has(host_smoke_script, r"iree-llvmcpu-target-cpu=cortex-a710"), "host smoke also emits an AArch64/Cortex-A710 VMFB for guest staging", "a710_guest_artifact_baseline")
    add(checks, "repo_iree_guest_stage_script", guest_stage_script.is_file() and os_access_executable(guest_stage_script), "repo-local staging script packages tiny-CNN VMFB/reference/runner for Buildroot guest images", "a710_guest_artifact_baseline")
    add(checks, "repo_iree_guest_runtime_staged", has(guest_stage_script, r"iree-base-runtime") and has(guest_stage_script, r"bin/iree-run-module"), "guest staging script extracts an AArch64 iree-run-module runtime from the official wheel", "a710_guest_runtime")
    add(checks, "repo_iree_guest_smoke_script", guest_smoke_script.is_file() and os_access_executable(guest_smoke_script), "repo-local QBox guest smoke script verifies IREE tiny-CNN output in the booted guest", "a710_guest_runtime")
    add(checks, "buildroot_optional_iree_staging", has(post_build, r"QBOX_IREE_GUEST_ARTIFACTS_DIR") and has(post_build, r"/opt/qbox/iree/tiny-cnn"), "Buildroot post-build can optionally copy staged IREE tiny-CNN artifacts into the rootfs", "a710_guest_artifact_baseline")
    add(checks, "repo_iree_hexagon_hal_absent", not has(driver, r"IREE|iree|HAL"), "Hexagon accelerator HAL integration is still absent; current IREE execution is A710 CPU local-task", "hexagon_accelerator_gap")
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
            "hexagon_iree_accelerator": "not_ready: requires HAL driver/device, command ABI, executable loader, user submit driver, dynamic SMMU mapping, and Hexagon kernels",
            "smmu_dma_model": "smoke_ready_only: fixed-window translated TLM path with 4KiB DMA smoke limit",
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
