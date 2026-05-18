#!/usr/bin/env python3
"""Check whether Hexagon-MLIR can feed the current Apollo IREE path.

The current QBox Apollo Hexagon lane exposes a fixed DRM accel ABI for the
repo-local CNN, vector-add, and DMA stress jobs. This checker keeps that
boundary explicit while documenting what Hexagon-MLIR can provide today.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


TEXT_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".md",
    ".py",
    ".sh",
    ".txt",
}


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
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def has(path: Path, pattern: str) -> bool:
    return re.search(pattern, read_text(path), re.MULTILINE) is not None


def add(checks: list[Check], name: str, status: str, detail: str, required_for: str) -> None:
    checks.append(Check(name, status, detail, required_for))


def scan_tree(root: Path, pattern: str) -> list[str]:
    if not root.exists():
        return []
    regex = re.compile(pattern, re.IGNORECASE)
    hits: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        rel = path.relative_to(root)
        text = read_text(path)
        if regex.search(text):
            hits.append(str(rel))
    return hits


def tool_exists(repo: Path, name: str) -> bool:
    if shutil.which(name):
        return True
    return any((repo / "sources/hexagon-mlir").glob(f"**/{name}"))


def hexagon_mlir_checks(repo: Path) -> list[Check]:
    checks: list[Check] = []
    gitmodules = repo / ".gitmodules"
    source = repo / "sources/hexagon-mlir"
    readme = source / "README.md"
    user_guide = source / "docs/user-guide.md"
    build_script = source / "scripts/build_hexagon_mlir.sh"

    source_ready = (
        readme.is_file()
        and (source / "qcom_hexagon_backend").is_dir()
        and build_script.is_file()
        and has(gitmodules, r"path = sources/hexagon-mlir")
        and has(gitmodules, r"url = https://github\.com/qualcomm/hexagon-mlir\.git")
    )
    add(
        checks,
        "hexagon_mlir_source_checkout",
        "pass" if source_ready else "missing",
        "sources/hexagon-mlir has README, qcom_hexagon_backend, build script, and .gitmodules registration",
        "compiler_source",
    )

    frontend_text = read_text(readme) + "\n" + read_text(user_guide)
    triton_torch = all(word in frontend_text for word in ("Triton", "PyTorch"))
    onnx_hits = scan_tree(source / "docs", r"\bonnx\b") + scan_tree(
        source / "qcom_hexagon_backend", r"\bonnx\b"
    )
    add(
        checks,
        "hexagon_mlir_frontend_scope",
        "blocked" if triton_torch and not onnx_hits else "pass",
        "Hexagon-MLIR docs/source describe Triton and PyTorch flows; no repo-local ONNX frontend was found"
        if triton_torch and not onnx_hits
        else f"ONNX-related hits: {', '.join(onnx_hits[:8])}",
        "onnx_to_hexagon_mlir",
    )

    required_env = [
        "HEXAGON_SDK_ROOT",
        "HEXAGON_TOOLS",
        "HEXKL_ROOT",
        "LLVM_PROJECT_BUILD_DIR",
        "CONDA_ENV",
    ]
    missing_env = [
        name
        for name in required_env
        if not os.environ.get(name) or not Path(os.environ[name]).exists()
    ]
    built_tools = all(tool_exists(repo, name) for name in ("linalg-hexagon-opt", "linalg-hexagon-translate"))
    add(
        checks,
        "hexagon_mlir_toolchain_ready",
        "pass" if not missing_env and built_tools else "missing",
        "Hexagon SDK/Tools/HexKL/LLVM/Python env and linalg-hexagon tools are available"
        if not missing_env and built_tools
        else "missing environment/tools: "
        + ", ".join(missing_env + ([] if built_tools else ["linalg-hexagon-opt", "linalg-hexagon-translate"])),
        "compiler_build",
    )

    submodule_ready = (source / "triton").is_dir() and (source / "triton_shared").is_dir()
    add(
        checks,
        "hexagon_mlir_nested_submodules",
        "pass" if submodule_ready else "missing",
        "triton and triton_shared nested submodules are present"
        if submodule_ready
        else "triton and/or triton_shared nested submodules are not initialized",
        "compiler_build",
    )
    return checks


def qbox_bridge_checks(repo: Path) -> list[Check]:
    checks: list[Check] = []
    guest = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools"
    uapi = guest / "apollo_hexagon_uapi_guest.h"
    hal_h = guest / "apollo_iree_hexagon_hal.h"
    hal_c = guest / "apollo_iree_hexagon_hal.c"
    runner_c = guest / "apollo_iree_hexagon_runner.c"
    run_module_c = guest / "apollo_iree_run_module.c"
    firmware = repo / "sources/qbox/platforms/buildroot/fw/hexagon_dma_smoke.s"
    vector_host = repo / "scripts/run_iree_vector_add_host_smoke.sh"
    vector_stage = repo / "scripts/stage_iree_vector_add_guest_artifacts.sh"
    vector_guest = repo / "scripts/run_iree_vector_add_hexagon_qbox_guest_smoke.sh"
    tiny_stage = repo / "scripts/stage_iree_tiny_cnn_guest_artifacts.sh"

    fixed_jobs = (
        has(uapi, r"DRM_IOCTL_APOLLO_HEXAGON_SUBMIT_CNN")
        and has(uapi, r"DRM_IOCTL_APOLLO_HEXAGON_SUBMIT_VADD")
        and has(uapi, r"DRM_IOCTL_APOLLO_HEXAGON_DMA_STRESS")
        and has(firmware, r"vector_add_job")
        and has(firmware, r"dma_copy_job")
        and has(firmware, r"job_loop")
    )
    add(
        checks,
        "qbox_apollo_fixed_job_abi",
        "pass" if fixed_jobs else "missing",
        "Apollo Hexagon UAPI and firmware expose fixed CNN, VADD, and DMA stress jobs",
        "qbox_runtime",
    )

    generic_loader = (
        has(uapi, r"SUBMIT_(ELF|MODULE|OBJECT|PROGRAM)|LOAD_(ELF|MODULE|OBJECT|PROGRAM)")
        or has(runner_c, r"dlopen.*hexagon|elf|object")
        or has(firmware, r"elf|reloc|program_loader")
    )
    add(
        checks,
        "qbox_generic_hexagon_object_loader",
        "pass" if generic_loader else "blocked",
        "generic Hexagon object/module loader ABI exists"
        if generic_loader
        else "current QBox path has no generic loader for Hexagon-MLIR object code; it only dispatches fixed jobs",
        "hexagon_mlir_object_execution",
    )

    metadata_bridge = (
        has(hal_h, r"compiler_artifact_path")
        and has(hal_c, r"compiler_artifact=")
        and has(runner_c, r"compiler bridge=%s")
        and has(run_module_c, r"compiler bridge=%s")
        and has(vector_stage, r"QBOX_HEXAGON_MLIR_ARTIFACT")
        and has(tiny_stage, r"QBOX_HEXAGON_MLIR_ARTIFACT")
    )
    add(
        checks,
        "qbox_hexagon_mlir_metadata_bridge",
        "pass" if metadata_bridge else "missing",
        "guest metadata can carry a Hexagon-MLIR artifact sidecar and report it in Apollo HAL logs",
        "artifact_bridge",
    )

    vadd_ready = (
        has(vector_host, r"vector_add_graph")
        and has(vector_host, r"4xf32=11 22 33 44")
        and has(vector_stage, r"compiler_model=vector-add")
        and has(vector_guest, r"EXEC @vector_add_graph \[apollo-hexagon\]")
        and fixed_jobs
        and metadata_bridge
    )
    add(
        checks,
        "vadd_bridge_feasible",
        "feasible" if vadd_ready else "missing",
        "ONNX vector-add can be compiled by the existing IREE host lane and run on Apollo Hexagon through the fixed VADD ioctl; Hexagon-MLIR artifacts can be staged as sidecar evidence",
        "vadd",
    )

    mnist_candidates = [
        uapi,
        hal_c,
        runner_c,
        run_module_c,
        firmware,
        repo / "scripts/run_iree_tiny_cnn_host_smoke.sh",
        repo / "scripts/stage_iree_tiny_cnn_guest_artifacts.sh",
        repo / "scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh",
        repo / "scripts/run_iree_vector_add_host_smoke.sh",
        repo / "scripts/stage_iree_vector_add_guest_artifacts.sh",
        repo / "scripts/run_iree_vector_add_hexagon_qbox_guest_smoke.sh",
    ]
    mnist_contract = [
        str(path.relative_to(repo))
        for path in mnist_candidates
        if re.search(r"\bmnist\b", read_text(path), re.IGNORECASE)
    ]
    add(
        checks,
        "mnist_bridge_feasible",
        "blocked" if not mnist_contract else "missing",
        "no MNIST model, tensor ABI, firmware job, or guest runner contract exists in the current Apollo Hexagon path"
        if not mnist_contract
        else f"MNIST references found but no verified execution contract: {', '.join(mnist_contract[:8])}",
        "mnist",
    )
    return checks


def summarize(checks: Iterable[Check]) -> dict[str, int]:
    result: dict[str, int] = {}
    for check in checks:
        result[check.status] = result.get(check.status, 0) + 1
    return result


def build_plan() -> list[dict[str, str]]:
    return [
        {
            "step": "vadd_current_slice",
            "status": "implemented",
            "detail": "Use existing ONNX->IREE vector_add_graph generation and the Apollo VADD ioctl path; optionally attach QBOX_HEXAGON_MLIR_ARTIFACT as a metadata sidecar.",
        },
        {
            "step": "hexagon_mlir_compile_gate",
            "status": "blocked_until_toolchain",
            "detail": "Initialize nested submodules and install Hexagon SDK 6.4.0.2, Hexagon Tools 19.0.02, HexKL, LLVM, and Python 3.11 environment before producing linalg-hexagon object code.",
        },
        {
            "step": "generic_execution_gate",
            "status": "blocked_until_runtime_abi",
            "detail": "Add a QBox Apollo Hexagon program/object loader ABI and firmware/runtime loader before executing arbitrary Hexagon-MLIR object code.",
        },
        {
            "step": "mnist_gate",
            "status": "blocked_until_model_abi",
            "detail": "Define MNIST tensor buffers, submit ioctl, firmware implementation, IREE metadata, and guest smoke markers before claiming MNIST support.",
        },
    ]


def classify(checks: list[Check]) -> dict[str, str]:
    by_name = {check.name: check for check in checks}
    direct_ok = (
        by_name["hexagon_mlir_frontend_scope"].status == "pass"
        and by_name["hexagon_mlir_toolchain_ready"].status == "pass"
        and by_name["qbox_generic_hexagon_object_loader"].status == "pass"
    )
    return {
        "direct_hexagon_mlir_to_qbox": "feasible" if direct_ok else "not_feasible_currently",
        "vadd": "feasible_adapter"
        if by_name["vadd_bridge_feasible"].status == "feasible"
        else "not_ready",
        "mnist": "blocked_currently"
        if by_name["mnist_bridge_feasible"].status == "blocked"
        else "not_ready",
        "execution_boundary": "metadata sidecar plus fixed Apollo ioctl jobs; no generic Hexagon object execution yet",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument("--json", dest="json_path", type=Path, help="write JSON report")
    parser.add_argument(
        "--require",
        choices=("vadd", "mnist", "direct"),
        help="return non-zero unless the requested execution slice is feasible",
    )
    args = parser.parse_args()

    repo = args.repo.resolve()
    checks = hexagon_mlir_checks(repo) + qbox_bridge_checks(repo)
    payload = {
        "repo": str(repo),
        "summary": summarize(checks),
        "classification": classify(checks),
        "checks": [check.__dict__ for check in checks],
        "plan": build_plan(),
    }

    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for check in checks:
        print(f"{check.status.upper():8} {check.name}: {check.detail}")
    print("SUMMARY", json.dumps(payload["summary"], sort_keys=True))
    print("CLASSIFICATION", json.dumps(payload["classification"], sort_keys=True))
    print("PLAN", json.dumps(payload["plan"], sort_keys=True))

    if args.require == "vadd" and payload["classification"]["vadd"] != "feasible_adapter":
        return 2
    if args.require == "mnist" and payload["classification"]["mnist"] != "feasible":
        return 2
    if args.require == "direct" and payload["classification"]["direct_hexagon_mlir_to_qbox"] != "feasible":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
