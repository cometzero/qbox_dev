# QBox Apollo IREE tiny CNN guest runtime 구현/검증 리포트

- 날짜: 2026-05-09
- 대상: `/build/qbox_dev`
- 목표: Apollo QBox A710 Linux guest 안에서 IREE tiny CNN VMFB를 실행하고 최종
  출력이 `1x1x2x2xf32=[[[54 63][90 99]]]`와 일치하는지 검증한다.

## 결론

A710 CPU baseline은 **QBox guest 내부 실행까지 완료**했다. Buildroot rootfs에
AArch64 `iree-run-module`, `tiny_cnn_aarch64.vmfb`, reference/manifest, 실행
스크립트를 staging했고, QBox 부팅 후 guest shell에서 IREE Runtime이 tiny CNN을
실행하여 expected tensor와 일치했다.

Hexagon accelerator 경로는 아직 완료 범위가 아니다. 현재 Hexagon/SMMU는 부팅 중
SMMU-translated DMA smoke와 Linux probe selftest까지 검증되며, IREE HAL/driver/
firmware 기반 CNN offload는 후속 과제로 남는다.

## 구현 변경

| 파일 | 변경 내용 |
| --- | --- |
| `configs/buildroot/external/apollo_qbox/configs/apollo_qbox_defconfig` | IREE runner 실행에 필요한 Buildroot C++ toolchain과 `libstdc++` 설치 활성화 |
| `scripts/stage_iree_tiny_cnn_guest_artifacts.sh` | PyPI `iree-base-runtime==3.11.0` AArch64 manylinux wheel에서 `iree-run-module`을 추출해 guest artifact에 포함 |
| `scripts/run_iree_tiny_cnn_qbox_guest_smoke.sh` | QBox 부팅, root 로그인, guest IREE 실행, output grep 검증을 자동화 |
| `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/post-build.sh` | `/opt/qbox/iree/tiny-cnn` guest 실행 안내 갱신 |
| `scripts/check_iree_cnn_pipeline_readiness.py` | A710 guest runtime readiness와 Hexagon HAL 미지원 항목을 분리 |
| `scripts/check_buildroot_arm64_lane.sh` | guest smoke script, C++ runtime, staged runner contract 확인 추가 |
| `doc/spec/qbox-iree-cnn-pipeline-tasks.md` | IREE-CNN-005B를 완료로 갱신 |

## 핵심 artifact

- Guest package: `build/iree-guest-artifacts/tiny-cnn/`
- Runner: `build/iree-guest-artifacts/tiny-cnn/bin/iree-run-module`
- VMFB: `build/iree-guest-artifacts/tiny-cnn/tiny_cnn_aarch64.vmfb`
- Guest install path: `/opt/qbox/iree/tiny-cnn`
- Runtime source: `iree-base-runtime-3.11.0` AArch64 manylinux wheel

`rootfs.cpio` 포함 확인:

```text
opt/qbox/iree/tiny-cnn/bin/iree-run-module
opt/qbox/iree/tiny-cnn/manifest.json
opt/qbox/iree/tiny-cnn/run_tiny_cnn_guest.sh
opt/qbox/iree/tiny-cnn/tiny_cnn_aarch64.vmfb
usr/lib/libstdc++.so
usr/lib/libstdc++.so.6
usr/lib/libstdc++.so.6.0.33
```

## 검증 명령과 결과

### 1. Guest artifact staging

```bash
./scripts/stage_iree_tiny_cnn_guest_artifacts.sh
```

결과: PASS. `manifest.json`에 AArch64 runner와 expected output이 기록됨.

### 2. Buildroot C++ runtime 재구성 및 rootfs 생성

```bash
make -C sources/buildroot O=/build/qbox_dev/build/buildroot-a710 \
  host-gcc-final-dirclean host-gcc-final
make -C sources/buildroot O=/build/qbox_dev/build/buildroot-a710 \
  gcc-final-reinstall
QBOX_IREE_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/tiny-cnn \
  ./scripts/build_qbox_buildroot_arm64.sh
```

증거 로그:

- `build/verification/buildroot-host-gcc-final-cxx-20260509-172726.log`
- `build/verification/buildroot-gcc-final-reinstall-cxx-20260509-173521.log`
- `build/verification/buildroot-iree-runtime-final2-20260509-173533.log`

### 3. QBox platform artifact staging

```bash
./scripts/stage_buildroot_artifacts.sh
```

결과: PASS.

증거 로그: `build/verification/stage-iree-runtime-final-20260509-173544.log`

### 4. QBox guest IREE tiny CNN smoke

```bash
QBOX_IREE_LOGIN_DELAY=9 \
QBOX_IREE_COMMAND_DELAY=2 \
QBOX_IREE_AFTER_COMMAND_DELAY=10 \
QBOX_BOOT_TIMEOUT=70 \
  ./scripts/run_iree_tiny_cnn_qbox_guest_smoke.sh
```

결과: PASS.

증거 로그:

- `build/verification/qbox-iree-tiny-cnn-guest-20260509-173548.log`
- `build/verification/qbox-iree-tiny-cnn-guest-boot-20260509-173548.log`

핵심 출력:

```text
EXEC @tiny_cnn_graph
result[0]: hal.buffer_view
1x1x2x2xf32=[[[54 63][90 99]]]
PASS: QBox guest IREE tiny-CNN output matched
```

동일 부팅 로그에서 확인된 기존 Apollo marker:

```text
APOLLO_HEXAGON_DMA: path=smmu-translated stream-id=0x1 caps=0x5
apollo-hexagon-test 1c220000.hexagon: probe ok
Run /sbin/init as init process
apollo-qbox login:
```

## 남은 범위

1. `iree-run-module` wheel 추출 방식 대신 Buildroot native package 또는 repo-local
   reproducible runtime package로 전환.
2. Hexagon userspace submit ABI, executable loader, queue/completion path 구현.
3. SMMU fixed-window smoke model을 dynamic map/unmap, fault reporting, multi-page DMA
   검증으로 확장.
4. IREE out-of-tree `apollo-hexagon` HAL과 Hexagon firmware CNN kernel 구현.
