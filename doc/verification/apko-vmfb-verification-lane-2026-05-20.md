# APKO VMFB 검증 lane

날짜: 2026-05-20
워크스페이스: `/build/qbox_dev`
작업 범위: `scripts/check_*.py`, `scripts/check_buildroot_arm64_lane.sh`,
`doc/verification/**`

## 요약

이 lane은 현재 repo-local APKO VMFB 전환 구간을 정적으로 검증하는 계약
checker를 추가한다. upstream IREE target backend packaging이 완료됐다고 주장하지
않고, staged VMFB trailer 경로, generic `CMD_SUBMIT` smoke 계약, negative
ioctl/fault coverage, artifact staging, 기존 증거 문서가 서로 맞는지만 확인한다.

## 추가된 checker

`scripts/check_apko_vmfb_verification_lane.py`는 다음 계약을 확인한다.

- APKO VADD, VMFB-embedded VADD, CNN, negative smoke script가 실행 가능하다.
- VMFB-embedded APKO marker인 `executable_source=vmfb-embedded-apko`,
  `command-buffer=generic-submit`, `APKO CMD_SUBMIT VADD ok`가 유지된다.
- generic VADD command BO smoke가 `LOAD_EXECUTABLE`, bound VADD dispatch,
  output copy-back, `4xf32=11 22 33 44` 결과를 요구한다.
- CNN APKO generic marker가 fixed compat 성공 marker와 섞이지 않는다.
- context ABI, BO bind/unbind, malformed `LOAD_EXECUTABLE`, invalid IOVA fault
  retrieval, WAIT, bad APKO ABI, empty fault record negative path가 유지된다.
- vector-add/tiny-CNN staging script가 VMFB-embedded APKO wrapper를 만든다.
- `iree-import-onnx` 또는 `iree-compile`이 없으면 unsupported ONNX negative
  compile 증거를 `blocked_missing_tool`로 분류한다.

`scripts/check_buildroot_arm64_lane.sh`는 이 checker의 실행 가능 여부와
classification/tool-gate 문자열도 상위 Buildroot lane 계약으로 확인한다.

## 검증 증거

```text
$ PYTHONPYCACHEPREFIX=/tmp/qbox-pycache \
> python3 scripts/check_apko_vmfb_verification_lane.py --repo . \
>   --json build/verification/apko-vmfb-verification-lane-2026-05-20.json
PASS                 apko_smoke_scripts_executable: APKO VADD, VMFB-embedded VADD, CNN, and negative smoke scripts are executable
PASS                 vmfb_embedded_apko_smoke_contract: VMFB smoke proves repo-local embedded APKO source, generic submit, and VADD output
PASS                 generic_vadd_cmd_submit_contract: VADD smoke requires LOAD_EXECUTABLE plus bound DISPATCH/VADD command BO markers
PASS                 generic_cnn_compat_boundary_contract: CNN smoke keeps APKO generic markers separate from fixed compat success
PASS                 negative_ioctl_and_fault_contract: negative smoke covers context/BO/CMD_SUBMIT/WAIT/APKO/fault-retrieval failures
PASS                 artifact_stage_contract: staging scripts package VMFB-embedded APKO artifacts and negative runner wrappers
PASS                 loader_vmfb_footer_contract: guest HAL validates the repo-local VMFB APKO footer and submits via CMD_SUBMIT
PASS                 buildroot_lane_contract_gate: check_buildroot_arm64_lane.sh gates VMFB, negative, generic, and compat markers
PASS                 readiness_json_contract_gate: readiness checker reports VMFB-embedded APKO and invalid-IOVA negative coverage
PASS                 verification_report_tracks_runtime_evidence: verification report records PASS evidence and remaining non-overclaimed blockers
BLOCKED_MISSING_TOOL unsupported_onnx_negative_tool_gate: blocked_missing_tool if IREE compiler/import tools are absent; install tools to run unsupported-ONNX compile rejection
SUMMARY {"blocked_missing_tool": 1, "pass": 10}
CLASSIFICATION {"apko_vmfb_transition": "repo_local_transition_ready", "unsupported_onnx_negative": "blocked_missing_tool"}
```


## Contract guardrails

- `repo_local_transition_ready`는 staged VMFB 뒤에 붙인 repo-local APKO
  trailer를 guest HAL loader가 안전하게 찾고 `CMD_SUBMIT`으로 전달한다는
  뜻이다. upstream IREE target backend가 HAL executable section에 APKO를
  packaging했다는 뜻이 아니다.
- APKO VADD/CNN/MNIST smoke는 generic command BO, executable slot, BO binding
  copy shim, fault retrieval 계약을 검증한다. full APKO code/payload
  interpreter 또는 trained MNIST graph execution 완료로 분류하지 않는다.
- QBox SMMU 관련 증거는 Apollo functional integration slice로만 유지한다.
  bit-exact Arm SMMUv3 completion claim으로 승격하지 않는다.
- unsupported ONNX/payload coverage는 host `iree-import-onnx`/`iree-compile`
  tooling이 없으면 `blocked_missing_tool`이며, 도구가 준비된 뒤 별도
  negative compile rejection evidence로 갱신한다.

## blocker 분류

- `unsupported_onnx_negative_tool_gate`: host에 `iree-import-onnx`와
  `iree-compile`이 없으면 `blocked_missing_tool`이다.
- upstream IREE target backend packaging은 이 lane의 PASS 범위 밖이다.
  현재 PASS는 repo-local staged VMFB trailer 전환 ABI에 한정된다.
