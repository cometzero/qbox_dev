# Apollo Hexagon MNIST Semantics 리뷰 반영 검증

날짜: 2026-05-21
작업공간: `/build/qbox_dev`
브랜치: `feature/qbox_dev`

## 요약

리뷰 반영으로 APKO MNIST smoke를 byte-invert stub에서
MNIST-shaped `Flatten+Gemm(zero weights, bias 0..9)` 계약으로 전환했다.
host ONNX/IREE smoke와 Apollo Hexagon CMDQ payload가 모두 zero input에 대해
다음 출력을 반환한다.

```text
1x10xf32=[0 1 2 3 4 5 6 7 8 9]
```

이번 범위는 deterministic MNIST-shaped graph semantics 검증이다. 학습된 MNIST
정확도, full APKO code/payload interpreter, true hardware BO mapping, upstream
IREE HAL executable backend packaging은 아직 남은 작업이다.

## 반영 내용

| 영역 | 변경 |
| --- | --- |
| Linux UAPI/driver | MNIST input/output을 `28 * 28` words와 `10` words로 확장하고, 큰 MNIST buffer를 kernel stack이 아니라 heap에서 처리 |
| QBox DMA | `CMDQ_DISPATCH_KIND_MNIST`를 28x28 입력/10-f32 출력의 Flatten+Gemm deterministic kernel로 실행 |
| Guest UMD/HAL | `mnist_graph` 출력 formatting과 expected output을 1x10 f32로 갱신 |
| Staging/checkers | MNIST APKO metadata를 `3136` input bytes, `40` output bytes, semantic-match marker로 갱신 |
| Plan/docs | MNIST-like/byte-invert 표현을 현재 계약과 남은 blocker 기준으로 정리 |

## 검증

| 명령 | 결과 | 증거 |
| --- | --- | --- |
| `bash -n scripts/*.sh` | PASS | shell syntax 통과 |
| `python3 -m py_compile scripts/check_iree_cnn_pipeline_readiness.py scripts/check_apko_vmfb_verification_lane.py scripts/qbox_pty_runner.py scripts/check_qbox_smmuv3_compliance.py` | PASS | Python helper compile 통과 |
| `git diff --check -- . ':!sources/linux' ':!sources/qbox' && git -C sources/linux diff --check && git -C sources/qbox diff --check` | PASS | whitespace check 통과 |
| `cmake --build sources/qbox/build --target apollo_hexagon_dma apollo-hexagon-dma-tests -j2` | PASS | QBox DMA component/test target build |
| `ctest --test-dir sources/qbox/build -R '^apollo-hexagon-dma-tests$' --output-on-failure` | PASS | 15/15 component tests pass |
| `./scripts/stage_iree_mnist_guest_artifacts.sh` | PASS | host output `1x10xf32=[0 1 2 3 4 5 6 7 8 9]`, staged manifest input/output `3136/40` |
| `python3 scripts/check_apko_vmfb_verification_lane.py --repo . --json build/verification/apko-vmfb-lane-mnist-semantics-20260521-rerun.json` | PASS | `SUMMARY {"pass": 13}` |
| `python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . --json build/verification/iree-readiness-mnist-semantics-20260521-rerun.json` | PASS | `SUMMARY {"pass": 69}` |
| `./scripts/check_buildroot_arm64_lane.sh` | PASS | MNIST Flatten+Gemm CMDQ marker 포함 contract lane 통과 |
| `./scripts/build_qbox_linux_arm64.sh` | PASS | stack frame warning 없이 `Image` 재생성 |
| `QBOX_IREE_MNIST_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/mnist ./scripts/build_qbox_buildroot_arm64.sh` | PASS | MNIST artifacts 포함 rootfs/DTB 재생성 |
| `./scripts/stage_buildroot_artifacts.sh` | PASS | Linux/rootfs/DTB QBox artifact staging |
| `./scripts/build_qbox_buildroot_platform.sh` | PASS | QBox Buildroot platform runtime rebuild |
| `QBOX_APKO_MNIST_HEXAGON_GUEST_SMOKE_STAMP=mnist-semantics-20260521 QBOX_BOOT_TIMEOUT=70 ./scripts/run_iree_apko_mnist_hexagon_qbox_guest_smoke.sh` | PASS | QBox guest APKO MNIST output matched |

## Guest Smoke 핵심 Marker

로그:

- `build/verification/qbox-iree-apko-mnist-hexagon-guest-mnist-semantics-20260521.log`
- `build/verification/qbox-iree-apko-mnist-hexagon-guest-boot-mnist-semantics-20260521.log`

확인된 marker:

```text
IREE Apollo Hexagon HAL: APKO CMD_SUBMIT MNIST ok
APOLLO_HEXAGON_DMA: command load executable slot=1 kind=3 input-bytes=3136 output-bytes=40 format=0x1
APOLLO_HEXAGON_DMA: command dispatch executable slot=1 kind=3
APOLLO_HEXAGON_DMA: command dispatch mnist flatten-gemm input=0x10010000 output=0x10011000 bytes=0xc40
IREE Apollo Hexagon HAL: offload complete queue=1 status=0x4d4e4953
EXEC @mnist_graph [apollo-hexagon]
1x10xf32=[0 1 2 3 4 5 6 7 8 9]
```

## Kernel Review

로드한 prompt:

- `.codex/review-prompts/kernel/technical-patterns.md`
- `.codex/review-prompts/kernel/review-core.md`
- `.codex/review-prompts/kernel/subsystem/subsystem.md`
- `.codex/review-prompts/kernel/subsystem/drm.md`
- `.codex/review-prompts/kernel/subsystem/io-accessors.md`
- `.codex/review-prompts/kernel/subsystem/locking.md`
- `.codex/review-prompts/kernel/subsystem/mm-alloc.md`
- `.codex/review-prompts/kernel/subsystem/syscall.md`

검토 경로:

- `sources/linux/include/uapi/drm/apollo_hexagon_accel.h`
- `sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-exec.c`

prompt-driven regression review 결과:

- MNIST buffer 확장으로 발생한 kernel stack frame warning을 heap allocation으로
  수정했다.
- `GFP_KERNEL` allocation은 ioctl process context와 mutex-protected path에서만
  수행되며 IRQ/spinlock context에 도달하지 않는다.
- `copy_from_user`/`copy_to_user`는 size/handle 검증 후 수행되고, allocation 및
  GEM object reference cleanup path를 확인했다.
- prompt-driven 추가 regression은 발견하지 못했다.

## 남은 범위

- BO binding metadata를 실제 Apollo TBU/SMMU hardware mapping 경로로 전환
- APKO metadata-only dispatch를 넘어 full APKO code/payload interpreter 구현
- upstream IREE VMFB HAL executable section에 Apollo APKO backend packaging 연결
