# Apollo Hexagon APKO lane 4 scaffold verification

날짜: 2026-05-18
작업공간: `/build/qbox_dev`

## 요약

이 문서는 리뷰 반영 전의 lane 4 scaffold 상태를 기록한 문서다. 이후 리뷰 반영으로
`apollo-hexagon-apko-v0` executable handle과 generic submit smoke가 구현되어
blocked 상태가 해소되었다.

최신 PASS 증거는
`doc/verification/qbox-apollo-hexagon-apko-generic-submit-2026-05-18.md`를
기준으로 본다.

## 변경된 계약

- generic APKO smoke scaffold 2개를 추가했다.
  - `scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh`
  - `scripts/run_iree_apko_cnn_hexagon_qbox_guest_smoke.sh`
- 이후 같은 script가 실제 QBox guest APKO smoke를 실행하도록 갱신되었다.
- lane contract gate와 readiness gate도 APKO generic submit slice를 검사하도록
  갱신되었다.

## 현재 상태

### 당시 PASS

- compat tiny-CNN smoke lane는 기존 스크립트로 유지된다.
- compat vector-add smoke lane는 기존 스크립트로 유지된다.
- generic APKO smoke 스캐폴드는 저장소에 존재했다.

### 당시 BLOCKED

- `apollo-hexagon-apko-v0` executable/runtime ABI
- generic APKO dispatch path
- generic APKO 실제 DNN execution

### 리뷰 반영 후 상태

- 위 세 항목은 repo-local APKO sidecar bridge 범위에서 PASS로 전환되었다.
- VMFB 내부 APKO packaging, APKO payload semantics, negative tests는 아직 남은
  blocker다.

## 확인한 파일

- `scripts/check_buildroot_arm64_lane.sh`
- `scripts/check_iree_cnn_pipeline_readiness.py`
- `scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh`
- `scripts/run_iree_apko_cnn_hexagon_qbox_guest_smoke.sh`

## 회고

lane 4 scaffold는 compat smoke를 깨지 않으면서 generic APKO로의 전환 경계를
문서화했다. 리뷰 반영 후에는 실제 APKO executable ABI와 command queue dispatch가
연결되었으므로, 이 문서는 superseded 기록으로 유지한다.
