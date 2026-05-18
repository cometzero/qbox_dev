# Apollo Hexagon APKO lane 4 scaffold verification

날짜: 2026-05-18
작업공간: `/build/qbox_dev`

## 요약

이 검증은 Apollo Hexagon generic DNN 실행의 lane 4 산출물에 초점을 둔다.
현재 QBox는 아직 `apollo-hexagon-apko-v0` 실행 ABI를 제공하지 않으므로,
generic APKO smoke는 **blocked** 상태로 남겨 두고 compat CNN/VADD smoke lane를
보존한다.

## 변경된 계약

- generic APKO smoke scaffold 2개를 추가했다.
  - `scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh`
  - `scripts/run_iree_apko_cnn_hexagon_qbox_guest_smoke.sh`
- lane contract gate가 위 scaffold를 명시적으로 요구하도록 갱신되었다.
- readiness gate가 generic APKO scaffold 존재와 현재 blocker를 별도 분류로
  보고하도록 갱신되었다.

## 현재 상태

### PASS

- compat tiny-CNN smoke lane는 기존 스크립트로 유지된다.
- compat vector-add smoke lane는 기존 스크립트로 유지된다.
- generic APKO smoke 스캐폴드는 저장소에 존재하고, blocked 메시지로 현재
  한계를 명시한다.

### BLOCKED

- `apollo-hexagon-apko-v0` executable/runtime ABI
- generic APKO dispatch path
- generic APKO 실제 DNN execution

## 확인한 파일

- `scripts/check_buildroot_arm64_lane.sh`
- `scripts/check_iree_cnn_pipeline_readiness.py`
- `scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh`
- `scripts/run_iree_apko_cnn_hexagon_qbox_guest_smoke.sh`

## 회고

lane 4는 compat smoke를 깨지 않으면서 generic APKO로의 전환 경계를 문서화하는
역할에 맞게 진행되었다. 다음 구현 단계는 실제 APKO executable ABI와 command
queue dispatch를 연결한 뒤, 이 scaffold를 PASS 기준으로 바꾸는 것이다.
