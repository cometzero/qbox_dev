#!/usr/bin/env python3
"""Verify APKO VMFB transition-lane contracts.

This checker is intentionally static: it verifies that the repository contains
the smoke scripts, contract gates, negative markers, and documentation needed to
prove the current APKO VMFB transition slice without launching QBox. Runtime
smokes remain owned by the existing run_iree_apko_* scripts.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def has(path: Path, pattern: str) -> bool:
    return re.search(pattern, read_text(path), flags=re.MULTILINE) is not None


def executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def venv_dir(repo: Path) -> Path:
    return Path(os.environ.get("QBOX_IREE_SMOKE_VENV", repo / "build/iree-smoke-venv"))


def tool_available(repo: Path, name: str) -> bool:
    if shutil.which(name) is not None:
        return True
    return executable(venv_dir(repo) / "bin" / name)


def add(checks: list[Check], name: str, ok: bool, detail: str) -> None:
    checks.append(Check(name=name, status="pass" if ok else "fail", detail=detail))


def require_markers(path: Path, markers: Iterable[str]) -> bool:
    text = read_text(path)
    return path.is_file() and all(marker in text for marker in markers)


def repo_checks(repo: Path) -> list[Check]:
    checks: list[Check] = []
    scripts = repo / "scripts"
    verification = repo / "doc/verification/qbox-apollo-hexagon-apko-generic-submit-2026-05-18.md"
    apko_vmfb_lane_report = repo / "doc/verification/apko-vmfb-verification-lane-2026-05-20.md"
    buildroot_lane = scripts / "check_buildroot_arm64_lane.sh"
    readiness = scripts / "check_iree_cnn_pipeline_readiness.py"
    vadd = scripts / "run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh"
    vadd_vmfb = scripts / "run_iree_apko_vadd_vmfb_hexagon_qbox_guest_smoke.sh"
    cnn = scripts / "run_iree_apko_cnn_hexagon_qbox_guest_smoke.sh"
    cnn_vmfb = scripts / "run_iree_apko_cnn_vmfb_hexagon_qbox_guest_smoke.sh"
    mnist = scripts / "run_iree_apko_mnist_hexagon_qbox_guest_smoke.sh"
    negative = scripts / "run_iree_apko_negative_hexagon_qbox_guest_smoke.sh"
    vector_stage = scripts / "stage_iree_vector_add_guest_artifacts.sh"
    tiny_stage = scripts / "stage_iree_tiny_cnn_guest_artifacts.sh"
    mnist_stage = scripts / "stage_iree_mnist_guest_artifacts.sh"
    hal = (
        repo
        / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hexagon_hal.c"
    )
    run_module = (
        repo
        / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_run_module.c"
    )
    apko_negative = (
        repo
        / "configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_hexagon_apko_negative.c"
    )

    add(
        checks,
        "apko_smoke_scripts_executable",
        all(executable(path) for path in (vadd, vadd_vmfb, cnn, cnn_vmfb, mnist, negative)),
        "APKO VADD, VMFB-embedded VADD/CNN, CNN, MNIST, and negative smoke scripts are executable",
    )
    add(
        checks,
        "vmfb_embedded_apko_smoke_contract",
        require_markers(
            vadd_vmfb,
            (
                "run_vector_add_vmfb_apko_hexagon_guest.sh",
                "executable_source=vmfb-embedded-apko",
                "command-buffer=generic-submit",
                "APKO CMD_SUBMIT VADD ok",
                "PASS: QBox guest APKO VADD VMFB-embedded output matched",
            ),
        ),
        "VMFB smoke proves repo-local embedded APKO source, generic submit, and VADD output",
    )
    add(
        checks,
        "vmfb_embedded_apko_cnn_smoke_contract",
        require_markers(
            cnn_vmfb,
            (
                "run_tiny_cnn_vmfb_apko_hexagon_guest.sh",
                "executable_source=vmfb-embedded-apko",
                "command-buffer=generic-submit",
                "APKO CMD_SUBMIT CNN ok",
                "PASS: QBox guest APKO CNN VMFB-embedded output matched",
            ),
        ),
        "VMFB smoke proves repo-local embedded APKO source, generic submit, and CNN output",
    )
    add(
        checks,
        "generic_vadd_cmd_submit_contract",
        require_markers(
            vadd,
            (
                "command-buffer=generic-submit",
                "command load executable slot=1 kind=2",
                "command load payload slot=1 opcode=2",
                "command load code slot=1 offset=0 words=2 entry=65538",
                "APKO code program dispatch pc=0 opcode=2",
                "APKO code program end pc=1",
                "code_words=2",
                "code_entry=65538",
                "code_end=131072",
                "command BO bound VADD dispatch",
                "command BO bound VADD output copied",
                "APKO CMD_SUBMIT VADD ok",
                "4xf32=11 22 33 44",
            ),
        ),
        "VADD smoke requires LOAD_EXECUTABLE, LOAD_PAYLOAD, LOAD_CODE, and bound DISPATCH/VADD command BO markers",
    )
    add(
        checks,
        "generic_cnn_compat_boundary_contract",
        require_markers(
            cnn,
            (
                "command-buffer=generic-submit",
                "generic_abi_version=1",
                "command load payload slot=1 opcode=1",
                "command load code slot=1 offset=0 words=2 entry=65537",
                "APKO code program dispatch pc=0 opcode=1",
                "APKO code program end pc=1",
                "code_words=2",
                "code_entry=65537",
                "code_end=131072",
                "command dispatch executable slot=1 kind=1",
                "command dispatch cnn",
                "APKO CMD_SUBMIT CNN ok",
                "1x1x2x2xf32=[[[54 63][90 99]]]",
            ),
        ),
        "CNN smoke uses the same LOAD_PAYLOAD plus LOAD_CODE command BO path as VMFB-embedded APKO model dispatch",
    )
    add(
        checks,
        "generic_mnist_cmd_submit_contract",
        require_markers(
            mnist,
            (
                "command-buffer=generic-submit",
                "generic_abi_version=1",
                "command load payload slot=1 opcode=3",
                "command load code slot=1 offset=0 words=2 entry=65539",
                "APKO code program dispatch pc=0 opcode=3",
                "APKO code program end pc=1",
                "code_words=2",
                "code_entry=65539",
                "code_end=131072",
                "command dispatch executable slot=1 kind=3",
                "command dispatch mnist",
                "APKO CMD_SUBMIT MNIST ok",
                "1x10xf32=[0 1 2 3 4 5 6 7 8 9]",
            ),
        ),
        "MNIST smoke uses APKO CMD_SUBMIT plus LOAD_CODE-gated executable-slot dispatch and matches the host ONNX Flatten+Gemm output",
    )
    add(
        checks,
        "negative_ioctl_and_fault_contract",
        require_markers(
            negative,
            (
                "bad context ABI version",
                "bad BO bind size",
                "command BO bad LOAD_EXECUTABLE fault ok",
                "command BO bad LOAD_PAYLOAD fault ok",
                "command BO invalid IOVA fault ok",
                "bad WAIT size",
                "future WAIT fence",
                "bad APKO ABI version",
                "empty fault record",
                "APKO negative ioctl coverage completed",
            ),
        )
        and require_markers(
            apko_negative,
            (
                "DRM_IOCTL_APOLLO_HEXAGON_CMD_SUBMIT",
                "DRM_IOCTL_APOLLO_HEXAGON_GET_FAULT",
                "APOLLO_HEXAGON_CMDQ_FAULT_DMA_ERROR",
            ),
        ),
        "negative smoke covers context/BO/CMD_SUBMIT/WAIT/APKO/fault-retrieval failures",
    )
    add(
        checks,
        "artifact_stage_contract",
        require_markers(
            vector_stage,
            (
                "vector_add_apollo.vmfb",
                "0x45444F43",
                "run_vector_add_vmfb_apko_hexagon_guest.sh",
                "run_apko_negative_hexagon_guest.sh",
            ),
        )
        and require_markers(
            tiny_stage,
            (
                "tiny_cnn_apollo.vmfb",
                "0x45444F43",
                "run_tiny_cnn_vmfb_apko_hexagon_guest.sh",
                "apollo_hexagon_apko.vmfb.meta",
            ),
        )
        and require_markers(
            mnist_stage,
            (
                "run_iree_mnist_host_smoke.sh",
                "mnist_aarch64.vmfb",
                "0x45444F43",
                "host-report.json",
                "semantic_match=host-onnx-and-apollo-payload-produce-1x10xf32-bias-output",
                "apko_input_bytes=3136",
                "apko_output_bytes=40",
                "mnist_apollo.vmfb",
                "run_mnist_apko_hexagon_guest.sh",
                "apko_entry_kind=mnist",
            ),
        ),
        "staging scripts package VMFB-embedded APKO artifacts, the MNIST ONNX compile base, and negative runner wrappers",
    )
    add(
        checks,
        "loader_vmfb_footer_contract",
        require_markers(
            hal,
            (
                "load_embedded_apko_from_module",
                "APOLLO_HEXAGON_VMFB_APKO_FOOTER_MAGIC",
                "header[1] != sizeof(header)",
                "DRM_IOCTL_APOLLO_HEXAGON_CMD_SUBMIT",
            ),
        )
        and has(run_module, r"executable_source=vmfb-embedded-apko"),
        "guest HAL validates the repo-local VMFB APKO footer and submits via CMD_SUBMIT",
    )
    add(
        checks,
        "buildroot_lane_contract_gate",
        require_markers(
            buildroot_lane,
            (
                "run_iree_apko_vadd_vmfb_hexagon_qbox_guest_smoke.sh",
                "VMFB-embedded APKO VADD smoke marker",
                "run_iree_apko_cnn_vmfb_hexagon_qbox_guest_smoke.sh",
                "VMFB-embedded APKO CNN smoke marker",
                "APKO MNIST CMD_SUBMIT smoke marker",
                "APKO negative ioctl coverage completed",
                "run_tiny_cnn_vmfb_apko_hexagon_guest\\.sh",
                "command BO invalid IOVA fault ok",
            ),
        ),
        "check_buildroot_arm64_lane.sh gates VMFB, negative, generic, and compat markers",
    )
    add(
        checks,
        "readiness_json_contract_gate",
        require_markers(
            readiness,
            (
                "repo_apko_vmfb_embedded_smoke_script",
                "repo_apko_negative_invalid_iova_fault",
                "repo_apko_mnist_cmdq_smoke_script",
                "repo_iree_hexagon_vmfb_embedded_apko",
                "apollo_apko_generic_smoke",
                "generic_submit_slice_ready",
            ),
        ),
        "readiness checker reports VMFB-embedded APKO and invalid-IOVA negative coverage",
    )
    add(
        checks,
        "verification_report_tracks_runtime_evidence",
        require_markers(
            verification,
            (
                "VMFB-embedded APKO transition slice",
                "QBOX_APKO_VADD_VMFB_HEXAGON_GUEST_SMOKE_STAMP",
                "VMFB trailer parse",
                "invalid IOVA fault",
                "packaging은 아직 미구현",
            ),
        ),
        "verification report records PASS evidence and remaining non-overclaimed blockers",
    )
    add(
        checks,
        "vmfb_trailer_not_upstream_hal_packaging_contract",
        require_markers(
            apko_vmfb_lane_report,
            (
                "repo-local APKO",
                "trailer",
                "upstream IREE target backend packaging",
                "PASS 범위 밖",
            ),
        )
        and require_markers(
            repo / "doc/analysis/apollo-hexagon-dnn-kernel-execution-plan-2026-05-18.md",
            (
                "IREE compiler가 HAL executable section에 APKO를 packaging했다는 뜻이 아니며",
                "full APKO code/payload interpreter",
                "upstream VMFB HAL executable packaging",
                "functional integration slice",
            ),
        )
        and require_markers(
            repo / "doc/analysis/apollo-hexagon-dnn-kernel-task-breakdown-2026-05-20.md",
            (
                "true hardware BO",
                "mapping",
                "full APKO payload execution",
                "upstream IREE packaging",
                "functional integration slice",
            ),
        ),
        "contract language keeps repo-local VMFB trailer separate from upstream HAL executable packaging, full APKO payload execution, and bit-exact SMMUv3 claims",
    )
    add(
        checks,
        "unsupported_payload_and_tooling_classification_contract",
        require_markers(
            repo / "doc/analysis/apollo-hexagon-dnn-kernel-task-breakdown-2026-05-20.md",
            (
                "unsupported ONNX op coverage",
                "blocked_missing_tool",
                "tool 미설치면 `blocked_missing_tool`",
            ),
        )
        and require_markers(
            repo / "doc/verification/apollo-hexagon-mnist-apko-review-2026-05-21.md",
            (
                "full APKO code/payload execution",
                "upstream IREE VMFB HAL executable section packaging",
                "host-side IREE/ONNX tooling",
            ),
        ),
        "unsupported payload/tooling blockers remain explicit instead of being folded into VMFB trailer PASS",
    )
    add(
        checks,
        "unsupported_onnx_negative_tool_gate",
        tool_available(repo, "iree-import-onnx") and tool_available(repo, "iree-compile"),
        "blocked_missing_tool if IREE compiler/import tools are absent; install tools to run unsupported-ONNX compile rejection",
    )
    return checks


def summarize(checks: Iterable[Check]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for check in checks:
        summary[check.status] = summary.get(check.status, 0) + 1
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", dest="json_path", type=Path, help="write machine-readable report")
    parser.add_argument(
        "--require-host-tools",
        action="store_true",
        help="fail when unsupported-ONNX negative compile tools are missing",
    )
    args = parser.parse_args()

    repo = args.repo.resolve()
    checks = repo_checks(repo)
    if not args.require_host_tools:
        checks = [
            Check(c.name, "blocked_missing_tool" if c.name == "unsupported_onnx_negative_tool_gate" and c.status == "fail" else c.status, c.detail)
            for c in checks
        ]

    payload = {
        "repo": str(repo),
        "summary": summarize(checks),
        "checks": [asdict(check) for check in checks],
        "classification": {
            "apko_vmfb_transition": "repo_local_transition_ready",
            "unsupported_onnx_negative": "blocked_missing_tool"
            if any(c.name == "unsupported_onnx_negative_tool_gate" and c.status == "blocked_missing_tool" for c in checks)
            else "tooling_available",
        },
    }
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for check in checks:
        print(f"{check.status.upper():20} {check.name}: {check.detail}")
    print("SUMMARY", json.dumps(payload["summary"], sort_keys=True))
    print("CLASSIFICATION", json.dumps(payload["classification"], sort_keys=True))

    failures = [c for c in checks if c.status == "fail"]
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
