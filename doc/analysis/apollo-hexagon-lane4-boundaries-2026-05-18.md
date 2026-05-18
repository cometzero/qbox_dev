# Apollo Hexagon Lane4 경계와 회귀 메모

날짜: 2026-05-18
작업공간: `/build/qbox_dev`

## 목적

이 문서는 Apollo/Hexagon/APKO 작업에서 Lane4가 담당할 계획 근거,
compatibility 메모, 회귀 요구사항, 소유 경계를 기록한다. 범위는 계약
스크립트, smoke script, 증거 문서, gate 유지보수로 제한한다.

## 현재 계획 근거

- `/build/qbox_dev/doc/analysis/apollo-hexagon-dnn-kernel-execution-plan-2026-05-18.md:27-34`
  - VMFB는 IREE runtime/UMD 영역에 남아야 한다.
  - fixed CNN/VADD job path는 일시적 compatibility shim이다.
- `/build/qbox_dev/doc/analysis/apollo-hexagon-dnn-kernel-execution-plan-2026-05-18.md:158-199`
  - `APKO`는 `apollo-hexagon-apko-v0`로 정의한다.
  - `.vmfb.meta`는 staging/provenance artifact로만 사용한다.
- `/build/qbox_dev/doc/analysis/apollo-hexagon-dnn-kernel-execution-plan-2026-05-18.md:537-566`
  - repo contract는 compat fixed-path check와 generic v2 check를 분리해야
    한다.
  - 기존 fixed marker는 전환 기간 동안 compat section에만 남긴다.
- `/build/qbox_dev/doc/analysis/apollo-hexagon-dnn-kernel-execution-plan-2026-05-18.md:570-577`
  - driver refactor는 기존 동작을 보존하면서 소유 경계를 만들어야 한다.
- `/build/qbox_dev/doc/analysis/apollo-hexagon-dnn-kernel-execution-plan-2026-05-18.md:744-816`
  - 기존 smoke script는 compat lane에 남긴다.
  - 새 generic APKO smoke와 evidence는 별도 항목으로 관리한다.

## Compatibility 메모

- `/build/qbox_dev/doc/analysis/hexagon-mlir-target-execution-2026-05-18.md:36-55`
  - QBox는 fixed DRM job을 가진 Buildroot Linux guest이며, upstream
    Hexagon-MLIR runtime contract와 다르다.
  - generic loader ABI가 생기기 전까지 직접 Hexagon-MLIR object 실행은
    blocked 상태다.
- `/build/qbox_dev/doc/analysis/hexagon-mlir-iree-qbox-bridge-plan-2026-05-18.md:8-25`
  - 현재 feasible bridge는 ONNX vector-add를 IREE로 거친 뒤 fixed Apollo
    VADD ioctl로 실행하는 방식이다.
  - MNIST는 model/tensor execution contract가 생기기 전까지 blocked 상태다.
- `/build/qbox_dev/doc/verification/qbox-iree-vector-add-hexagon-2026-05-15.md:87-93`
  - 검증된 vector-add path는 repo-local integration slice이며 upstream
    Hexagon backend integration으로 과장하면 안 된다.

## 회귀 요구사항

- refactor 중에도 현재 compat smoke 동작을 유지한다.
- generic APKO smoke가 안정화되기 전까지 fixed marker를 보존한다.
- `doc/verification/`에서 compat evidence와 generic evidence를 분리한다.
- generic path에는 unsupported op, ABI mismatch, invalid IOVA negative
  coverage를 유지한다.
- Linux driver code를 수정할 때는 `kernel-review`를 반드시 수행한다.

## Lane4 소유 경계

Lane4가 소유하는 범위:

- contract script
- smoke script
- 한글 evidence/report artifact
- regression gate 문서

Lane4가 직접 수정하지 않아야 하는 범위:

- Linux UAPI와 DRM accel 구현
  - `/build/qbox_dev/sources/linux/include/uapi/drm/apollo_hexagon_accel.h`
  - `/build/qbox_dev/sources/linux/drivers/accel/apollo_hexagon/*`
- QBox APKO command queue와 firmware execution
  - `/build/qbox_dev/sources/qbox/platforms/buildroot/fw/hexagon_dma_smoke.s`
- Apollo IREE HAL UMD와 Buildroot integration
  - `/build/qbox_dev/configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/*`
  - `/build/qbox_dev/configs/buildroot/external/apollo_qbox/package/iree-runtime/*`

## Lane4 실행 지침

- lane gate check는 이미 구현된 동작을 반영할 때만 갱신한다.
- script와 report에서 compat section과 generic section을 분리한다.
- VMFB, executable loading, runtime dispatch semantics를 Lane4 contract file로
  옮기지 않는다.
- runtime code 수정이 필요하면 Lane4 범위를 넓히지 말고 해당 lane으로
  넘긴다.
