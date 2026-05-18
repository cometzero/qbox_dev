#!/usr/bin/env python3
"""Check Hexagon-MLIR target execution readiness.

Hexagon-MLIR has two upstream execution modes:

* device: push a generated Hexagon shared object to an Android target via adb
  and run it with Qualcomm's run_main_on_hexagon launcher.
* simulator: run the same shared object under the Hexagon SDK QuRT simulator
  using hexagon-sim, qurt_model.so, and run_main_on_hexagon_sim.

The Apollo QBox Buildroot guest is a different target. It currently exposes
fixed DRM accel jobs and does not provide the Qualcomm run_main_on_hexagon /
QuRT runtime expected by Hexagon-MLIR, so this checker reports that boundary
explicitly instead of treating QBox as an upstream Hexagon-MLIR device.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
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
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def has(path: Path, pattern: str) -> bool:
    return re.search(pattern, read_text(path), re.MULTILINE) is not None


def add(checks: list[Check], name: str, status: str, detail: str, required_for: str) -> None:
    checks.append(Check(name, status, detail, required_for))


def env_path(name: str) -> Path | None:
    value = os.environ.get(name)
    if not value:
        return None
    return Path(value).expanduser()


def path_ok(path: Path | None, executable: bool = False) -> bool:
    if path is None or not path.exists():
        return False
    if executable and not os.access(path, os.X_OK):
        return False
    return True


def tool_path(name: str, root: Path | None = None) -> Path | None:
    found = shutil.which(name)
    if found:
        return Path(found)
    if root and root.exists():
        matches = sorted(root.glob(f"**/{name}"))
        if matches:
            return matches[0]
    return None


def q6_version() -> str:
    return os.environ.get("HEXAGON_ARCH_VERSION", "75")


def source_checks(repo: Path) -> list[Check]:
    checks: list[Check] = []
    src = repo / "sources/hexagon-mlir"
    executor = src / "qcom_hexagon_backend/backend/hexagon_executor.py"
    compiler = src / "qcom_hexagon_backend/backend/compiler.py"
    driver = src / "qcom_hexagon_backend/backend/driver.py"
    vector_doc = src / "docs/tutorials/triton/vector_add.md"
    user_guide = src / "docs/user-guide.md"

    source_ready = (
        (src / "README.md").is_file()
        and executor.is_file()
        and compiler.is_file()
        and driver.is_file()
    )
    add(
        checks,
        "hexagon_mlir_source_ready",
        "pass" if source_ready else "missing",
        "sources/hexagon-mlir includes backend compiler, driver, executor, and docs",
        "source",
    )
    add(
        checks,
        "hexagon_mlir_device_launcher_contract",
        "pass"
        if has(executor, r"run_kernel_on_device")
        and has(executor, r"adb .* push")
        and has(executor, r"run_main_on_hexagon")
        and has(executor, r"ADSP_LIBRARY_PATH")
        else "missing",
        "device mode pushes artifacts with adb and runs run_main_on_hexagon with ADSP_LIBRARY_PATH",
        "device",
    )
    add(
        checks,
        "hexagon_mlir_simulator_launcher_contract",
        "pass"
        if has(executor, r"run_kernel_on_simulator")
        and has(executor, r"hexagon-sim")
        and has(executor, r"qurt_model\.so")
        and has(executor, r"runelf\.pbn")
        else "missing",
        "simulator mode drives hexagon-sim with QuRT qurt_model.so and runelf.pbn",
        "simulator",
    )
    add(
        checks,
        "hexagon_mlir_triton_pipeline_contract",
        "pass"
        if has(compiler, r"ttir_to_ttsharedir")
        and has(compiler, r"translate_linalg_to_obj")
        and has(driver, r"TritonHexagonLauncher")
        else "missing",
        "Triton path lowers TTIR to Linalg and then Hexagon object code",
        "compile",
    )
    add(
        checks,
        "hexagon_mlir_vector_add_test_contract",
        "pass"
        if has(vector_doc, r"test/python/triton/test_vec_add\.py")
        and has(user_guide, r"pytest -sv test/python/triton/test_vec_add\.py")
        else "missing",
        "upstream vector-add smoke entrypoint is pytest -sv test/python/triton/test_vec_add.py",
        "smoke",
    )
    return checks


def build_checks(repo: Path) -> list[Check]:
    checks: list[Check] = []
    src = repo / "sources/hexagon-mlir"
    sdk = env_path("HEXAGON_SDK_ROOT")
    tools = env_path("HEXAGON_TOOLS")
    hexkl = env_path("HEXKL_ROOT")
    conda = env_path("CONDA_ENV")
    llvm = env_path("LLVM_PROJECT_BUILD_DIR")
    runtime_libs = env_path("HEXAGON_RUNTIME_LIBS_DIR")
    opt = tool_path("linalg-hexagon-opt", src)
    translate = tool_path("linalg-hexagon-translate", src)
    triton_shared_opt = env_path("TRITON_SHARED_OPT_PATH")
    q6 = q6_version()

    envs = {
        "HEXAGON_MLIR_ROOT": env_path("HEXAGON_MLIR_ROOT"),
        "HEXAGON_SDK_ROOT": sdk,
        "HEXAGON_TOOLS": tools,
        "HEXKL_ROOT": hexkl,
        "LLVM_PROJECT_BUILD_DIR": llvm,
        "CONDA_ENV": conda,
    }
    missing_env = [name for name, value in envs.items() if not path_ok(value)]
    add(
        checks,
        "hexagon_mlir_environment",
        "pass" if not missing_env else "missing",
        "required Hexagon-MLIR environment directories exist"
        if not missing_env
        else "missing environment directories: " + ", ".join(missing_env),
        "compile",
    )

    nested = (src / "triton").is_dir() and (src / "triton_shared").is_dir()
    add(
        checks,
        "hexagon_mlir_nested_submodules",
        "pass" if nested else "missing",
        "triton and triton_shared nested submodules are initialized"
        if nested
        else "triton and/or triton_shared nested submodules are not initialized",
        "compile",
    )

    tools_ready = (
        path_ok(opt, executable=True)
        and path_ok(translate, executable=True)
        and path_ok(triton_shared_opt, executable=True)
    )
    add(
        checks,
        "hexagon_mlir_compiler_tools",
        "pass" if tools_ready else "missing",
        "linalg-hexagon-opt, linalg-hexagon-translate, and triton-shared-opt are executable"
        if tools_ready
        else "missing compiler tools: "
        + ", ".join(
            name
            for name, path in (
                ("linalg-hexagon-opt", opt),
                ("linalg-hexagon-translate", translate),
                ("TRITON_SHARED_OPT_PATH", triton_shared_opt),
            )
            if not path_ok(path, executable=True)
        ),
        "compile",
    )

    clang = tools / "bin/hexagon-clang++" if tools else None
    sim = tools / "bin/hexagon-sim" if tools else None
    qurt_include = sdk / f"rtos/qurt/computev{q6}/include/qurt" if sdk else None
    qhl_hvx = sdk / f"libs/qhl_hvx/prebuilt/hexagon_toolv87_v{q6}/libqhmath_hvx.a" if sdk else None
    if runtime_libs is None and opt:
        runtime_libs = opt.parent / "runtime"
    async_runtime = (
        runtime_libs / "multithreading/libhexagon_mlir_async_runtime.a"
        if runtime_libs
        else None
    )
    link_ready = (
        path_ok(clang, executable=True)
        and path_ok(qurt_include)
        and path_ok(qhl_hvx)
        and path_ok(runtime_libs)
    )
    add(
        checks,
        "hexagon_mlir_shared_object_link_inputs",
        "pass" if link_ready else "missing",
        "hexagon-clang++, QuRT headers, qhmath_hvx, and runtime lib directory are present"
        if link_ready
        else "missing link inputs: "
        + ", ".join(
            name
            for name, path, exe in (
                ("hexagon-clang++", clang, True),
                ("QuRT include", qurt_include, False),
                ("libqhmath_hvx.a", qhl_hvx, False),
                ("HEXAGON_RUNTIME_LIBS_DIR", runtime_libs, False),
            )
            if not path_ok(path, executable=exe)
        ),
        "compile",
    )
    add(
        checks,
        "hexagon_mlir_async_runtime_optional",
        "pass" if path_ok(async_runtime) else "missing",
        "async runtime archive exists for multithreaded kernels"
        if path_ok(async_runtime)
        else "libhexagon_mlir_async_runtime.a not found; single-thread flows may still link, but vector-add tutorial enables multithreading",
        "compile",
    )
    add(
        checks,
        "hexagon_mlir_hexagon_sim_tool",
        "pass" if path_ok(sim, executable=True) else "missing",
        f"hexagon-sim exists for v{q6} simulator execution"
        if path_ok(sim, executable=True)
        else "hexagon-sim missing from HEXAGON_TOOLS/bin",
        "simulator",
    )
    return checks


def device_checks() -> list[Check]:
    checks: list[Check] = []
    sdk = env_path("HEXAGON_SDK_ROOT")
    tools = env_path("HEXAGON_TOOLS")
    q6 = q6_version()
    adb = tool_path("adb")
    serial = os.environ.get("ANDROID_SERIAL")
    run_main = sdk / "libs/run_main_on_hexagon/ship/android_aarch64/run_main_on_hexagon" if sdk else None
    skel = sdk / f"libs/run_main_on_hexagon/ship/hexagon_toolv87_v{q6}/librun_main_on_hexagon_skel.so" if sdk else None
    libcpp = tools / f"target/hexagon/lib/v{q6}/G0/pic/libc++.so.1" if tools else None

    add(
        checks,
        "hexagon_mlir_adb_available",
        "pass" if path_ok(adb, executable=True) else "missing",
        f"adb={adb}" if path_ok(adb, executable=True) else "adb not found in PATH",
        "device",
    )
    add(
        checks,
        "hexagon_mlir_android_serial",
        "pass" if serial else "missing",
        "ANDROID_SERIAL is set" if serial else "ANDROID_SERIAL is not set",
        "device",
    )
    add(
        checks,
        "hexagon_mlir_run_main_on_hexagon",
        "pass" if path_ok(run_main, executable=True) and path_ok(skel) else "missing",
        "run_main_on_hexagon and librun_main_on_hexagon_skel.so are present"
        if path_ok(run_main, executable=True) and path_ok(skel)
        else "missing run_main_on_hexagon device launcher and/or skel library",
        "device",
    )
    add(
        checks,
        "hexagon_mlir_device_libcpp",
        "pass" if path_ok(libcpp) else "missing",
        "Hexagon libc++.so.1 runtime exists" if path_ok(libcpp) else "Hexagon libc++.so.1 missing",
        "device",
    )
    return checks


def simulator_checks() -> list[Check]:
    checks: list[Check] = []
    sdk = env_path("HEXAGON_SDK_ROOT")
    tools = env_path("HEXAGON_TOOLS")
    q6 = q6_version()
    qurt_model = sdk / f"rtos/qurt/computev{q6}/debugger/lnx64/qurt_model.so" if sdk else None
    qtimer = tools / "lib/iss/qtimer.so" if tools else None
    l2vic = tools / "lib/iss/l2vic.so" if tools else None
    runelf = sdk / f"rtos/qurt/computev{q6}/sdksim_bin/runelf.pbn" if sdk else None
    run_main_sim = sdk / f"libs/run_main_on_hexagon/ship/hexagon_toolv87_v{q6}/run_main_on_hexagon_sim" if sdk else None
    required = (
        ("qurt_model.so", qurt_model, False),
        ("qtimer.so", qtimer, False),
        ("l2vic.so", l2vic, False),
        ("runelf.pbn", runelf, False),
        ("run_main_on_hexagon_sim", run_main_sim, True),
    )
    missing = [name for name, path, exe in required if not path_ok(path, executable=exe)]
    add(
        checks,
        "hexagon_mlir_simulator_runtime",
        "pass" if not missing else "missing",
        "QuRT simulator runtime files are present"
        if not missing
        else "missing simulator runtime files: " + ", ".join(missing),
        "simulator",
    )
    return checks


def qbox_checks(repo: Path) -> list[Check]:
    checks: list[Check] = []
    guest = repo / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools"
    uapi = guest / "apollo_hexagon_uapi_guest.h"
    firmware = repo / "sources/qbox/platforms/buildroot/fw/hexagon_dma_smoke.s"
    sidecar = repo / "scripts/stage_iree_vector_add_guest_artifacts.sh"

    fixed_jobs = (
        has(uapi, r"DRM_IOCTL_APOLLO_HEXAGON_SUBMIT_CNN")
        and has(uapi, r"DRM_IOCTL_APOLLO_HEXAGON_SUBMIT_VADD")
        and has(uapi, r"DRM_IOCTL_APOLLO_HEXAGON_DMA_STRESS")
        and has(firmware, r"vector_add_job")
    )
    add(
        checks,
        "qbox_fixed_job_boundary",
        "pass" if fixed_jobs else "missing",
        "QBox Apollo Hexagon exposes fixed CNN/VADD/DMA jobs, not an upstream Hexagon-MLIR loader",
        "qbox",
    )
    add(
        checks,
        "qbox_hexagon_mlir_sidecar_bridge",
        "pass" if has(sidecar, r"QBOX_HEXAGON_MLIR_ARTIFACT") else "missing",
        "QBox staging can carry a Hexagon-MLIR artifact as metadata sidecar",
        "qbox",
    )
    generic_loader = has(uapi, r"LOAD_(OBJECT|MODULE|ELF)|SUBMIT_(OBJECT|MODULE|ELF)")
    add(
        checks,
        "qbox_generic_hexagon_mlir_loader",
        "pass" if generic_loader else "blocked",
        "generic Hexagon-MLIR object loader exists"
        if generic_loader
        else "QBox target lacks Qualcomm run_main_on_hexagon/QuRT and lacks a generic Apollo object loader ABI",
        "qbox",
    )
    return checks


def summarize(checks: Iterable[Check]) -> dict[str, int]:
    result: dict[str, int] = {}
    for check in checks:
        result[check.status] = result.get(check.status, 0) + 1
    return result


def ready(checks: Iterable[Check], required_for: set[str]) -> bool:
    for check in checks:
        if check.required_for in required_for and check.status != "pass":
            return False
    return True


def classify(checks: list[Check]) -> dict[str, str]:
    compile_ready = ready(checks, {"source", "compile"})
    return {
        "device": "ready" if compile_ready and ready(checks, {"device"}) else "blocked_missing_prerequisites",
        "simulator": "ready" if compile_ready and ready(checks, {"simulator"}) else "blocked_missing_prerequisites",
        "qbox": "not_supported_currently"
        if any(c.name == "qbox_generic_hexagon_mlir_loader" and c.status == "blocked" for c in checks)
        else "ready",
        "current_qbox_path": "fixed-job adapter only; use QBOX_HEXAGON_MLIR_ARTIFACT sidecar plus existing Apollo VADD/CNN ioctl path until a generic loader exists",
    }


def recipes(repo: Path) -> dict[str, list[str]]:
    return {
        "device": [
            "cd sources/hexagon-mlir",
            "source scripts/set_local_env.sh",
            "export RUN_ON_SIM=0",
            "export ANDROID_SERIAL=<adb-serial>",
            "export ANDROID_HOST=<optional-adb-host>",
            "TRITON_ALWAYS_COMPILE=1 pytest -sv test/python/triton/test_vec_add.py",
        ],
        "simulator": [
            "cd sources/hexagon-mlir",
            "source scripts/set_local_env.sh",
            "export RUN_ON_SIM=1",
            "TRITON_ALWAYS_COMPILE=1 pytest -sv test/python/triton/test_vec_add.py",
        ],
        "qbox_adapter": [
            "QBOX_HEXAGON_MLIR_ARTIFACT=/path/to/hexagon-mlir/artifact ./scripts/stage_iree_vector_add_guest_artifacts.sh",
            "QBOX_IREE_VECTOR_ADD_GUEST_ARTIFACTS_DIR=build/iree-guest-artifacts/vector-add ./scripts/build_qbox_buildroot_arm64.sh",
            "./scripts/stage_buildroot_artifacts.sh",
            "QBOX_BOOT_TIMEOUT=70 ./scripts/run_iree_vector_add_hexagon_qbox_guest_smoke.sh",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument("--json", dest="json_path", type=Path)
    parser.add_argument("--require", choices=("device", "simulator", "qbox"))
    args = parser.parse_args()

    repo = args.repo.resolve()
    checks = (
        source_checks(repo)
        + build_checks(repo)
        + device_checks()
        + simulator_checks()
        + qbox_checks(repo)
    )
    payload = {
        "repo": str(repo),
        "summary": summarize(checks),
        "classification": classify(checks),
        "checks": [check.__dict__ for check in checks],
        "recipes": recipes(repo),
    }

    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for check in checks:
        print(f"{check.status.upper():8} {check.name}: {check.detail}")
    print("SUMMARY", json.dumps(payload["summary"], sort_keys=True))
    print("CLASSIFICATION", json.dumps(payload["classification"], sort_keys=True))

    if args.require and payload["classification"][args.require] != "ready":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
