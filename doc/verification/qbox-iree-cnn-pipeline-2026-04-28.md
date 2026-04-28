# QBox Apollo IREE CNN Pipeline 구현/검증 리포트

- 날짜: 2026-04-28
- 대상: `/build/qbox_dev`
- 목표: ONNX → MLIR import → IREE compile → IREE Runtime pipeline을 Apollo QBox
  Hexagon/SMMU 기능 모델 관점에서 구현 가능한 범위까지 구성하고 검증한다.

## 결론

현재 완료한 범위는 **host CPU tiny CNN IREE pipeline**, **AArch64 VMFB guest artifact staging**, 그리고 **Apollo/QBox readiness
자동 분류**이다. QBox A710 Linux boot lane과 Hexagon SMMU-translated DMA smoke는
유효하지만, Hexagon을 IREE accelerator로 사용하는 것은 아직 불가능하다.

- A710 CPU baseline: artifact 준비. qbox Linux 부팅은 검증됐고 AArch64 VMFB/reference/runner를 rootfs에 선택 staging할 수 있음. guest 내부 IREE runtime packaging은 차기 작업.
- Hexagon DMA/SMMU: smoke 준비. fixed-window SMMU-translated TLM path는 검증됨.
- Hexagon IREE accelerator: 미준비. HAL driver/device, command ABI, executable
  loader, dynamic SMMU mapping, Hexagon ML kernel runtime이 필요함.

## 생성한 태스크와 결과

| ID | 결과 | 설명 |
| --- | --- | --- |
| IREE-CNN-001 | 완료 | `scripts/check_iree_cnn_pipeline_readiness.py` 추가 |
| IREE-CNN-002 | 완료 | `scripts/run_iree_tiny_cnn_host_smoke.sh` 추가 |
| IREE-CNN-003 | 완료 | `doc/spec/qbox-iree-cnn-pipeline-tasks.md` 작성 |
| IREE-CNN-004 | 완료 | 본 리포트 작성 |
| IREE-CNN-005A | 완료 | A710 guest artifact staging |
| IREE-CNN-005B | 차기 | A710 guest 내부 IREE runtime packaging |
| IREE-CNN-006 | 차기 | Hexagon userspace submit driver ABI |
| IREE-CNN-007 | 차기 | dynamic SMMU map/unmap 및 fault 모델 |
| IREE-CNN-008 | 차기 | IREE out-of-tree Apollo Hexagon HAL |
| IREE-CNN-009 | 차기 | Hexagon CNN kernel/firmware runtime |

## 구현 내용

### 1. Readiness checker

파일: `scripts/check_iree_cnn_pipeline_readiness.py`

기능:

- Buildroot rootfs-only 구성 확인
- standalone Linux build script 확인
- Apollo DTS의 Hexagon/SMMU binding 확인
- QBox Hexagon/SMMU/DMA module build/run guard 확인
- current DMA/SMMU model gap 분류
- host IREE/ONNX tooling 존재 여부 확인
- JSON evidence 출력

### 2. Host tiny CNN smoke

파일: `scripts/run_iree_tiny_cnn_host_smoke.sh`

기능:

1. `build/iree-smoke-venv` 생성
2. 필요 시 `iree-base-compiler[onnx]`, `iree-base-runtime`, `onnx`, `numpy` 설치
3. 1x1x4x4 input, 1x1x3x3 all-ones Conv + Relu ONNX 생성
4. `iree-import-onnx`로 MLIR 생성
5. `iree-compile`로 host CPU VMFB 및 AArch64/Cortex-A710 VMFB 생성
6. `iree-run-module --device=local-task`로 host 실행
7. expected tensor와 비교
8. `build/verification/iree-tiny-cnn-host/report.json` 생성

## 검증 증거

### Shell/Python 정적 검증

```bash
bash -n scripts/run_iree_tiny_cnn_host_smoke.sh \
  scripts/build_qbox_buildroot_arm64.sh \
  scripts/build_qbox_linux_arm64.sh \
  scripts/build_qbox_buildroot_platform.sh \
  scripts/run_qbox_buildroot_boot.sh
```

결과: PASS, exit code 0

```bash
python3 -m py_compile \
  scripts/check_iree_cnn_pipeline_readiness.py \
  scripts/qbox_pty_runner.py
```

결과: PASS, exit code 0

### Host IREE tiny CNN smoke

```bash
./scripts/run_iree_tiny_cnn_host_smoke.sh
```

결과 artifact:

- `build/verification/iree-tiny-cnn-host/tiny_cnn.onnx`
- `build/verification/iree-tiny-cnn-host/tiny_cnn.mlir`
- `build/verification/iree-tiny-cnn-host/tiny_cnn_cpu.vmfb`
- `build/verification/iree-tiny-cnn-host/run.log`
- `build/verification/iree-tiny-cnn-host/report.json`

핵심 출력:

```text
EXEC @tiny_cnn_graph
result[0]: hal.buffer_view
1x1x2x2xf32=[[[54 63][90 99]]]
```

검증된 package/tool version:

- `iree-base-compiler`: 3.11.0
- `iree-base-runtime`: 3.11.0
- `onnx`: 1.21.0
- `numpy`: 2.4.4
- `iree-compile`: 3.11.0rc20260316

### Readiness checker

Host tools 활성화 상태:

```bash
source build/iree-smoke-venv/bin/activate
./scripts/check_iree_cnn_pipeline_readiness.py \
  --require-host-tools \
  --json build/verification/iree-cnn-readiness-with-host-tools.json
```

결과:

```text
SUMMARY {"pass": 21}
```

분류:

```json
{
  "a710_cpu_iree_baseline": "artifact_ready: boot/rootfs/kernel lane exists and AArch64 VMFB guest artifacts can be staged; IREE runtime packaging is still missing",
  "hexagon_iree_accelerator": "not_ready: requires HAL driver/device, command ABI, executable loader, user submit driver, dynamic SMMU mapping, and Hexagon kernels",
  "smmu_dma_model": "smoke_ready_only: fixed-window translated TLM path with 4KiB DMA smoke limit"
}
```

### 기존 Apollo/QBox lane 회귀 검증

```bash
./scripts/check_buildroot_arm64_lane.sh \
  > build/verification/check-buildroot-arm64-lane-iree-20260428.log
```

결과: PASS. 마지막 결론:

```text
Lane conclusion: Buildroot owns rootfs/DTB generation only; Linux Image comes from sources/linux, and libqemu comes from sources/qemu.
```

### QBox boot smoke

```bash
QBOX_BOOT_TIMEOUT=20 \
QBOX_BOOT_LOG=build/verification/qbox-boot-iree-readiness-20260428.log \
./scripts/run_qbox_buildroot_boot.sh
```

확인된 marker:

```text
APOLLO_HEXAGON_DMA: path=smmu-translated stream-id=0x1 caps=0x5
APOLLO_SMMU_TBU: stream-id=0x1 translate read iova=0x10201000 pa=0xc01000 len=0x20
APOLLO_SMMU_TBU: stream-id=0x1 translate write iova=0x10000000 pa=0xa00000 len=0x20
apollo-hexagon-test 1c220000.hexagon: firmware dma traffic ok dst=0x0000000000a00000 words=8 first=0x48455831
apollo-hexagon-test 1c220000.hexagon: dma selftest ok dma=0x0000fffffffff000 size=4096
apollo-hexagon-test 1c220000.hexagon: probe ok
Run /sbin/init as init process
apollo-qbox login:
```

결과: timeout에 의해 정상 종료, boot 및 Hexagon/SMMU smoke marker 확인.

## 부족한 부분

### A710 guest IREE baseline 부족분

- Buildroot rootfs에 IREE runtime/runner가 포함되어 있지 않다.
- VMFB와 input/output fixture를 guest로 staging하는 flow는 완료됐다.
- guest shell에서 `iree-run-module` 또는 custom C runner를 실행하는 smoke는 runtime package 추가 후 가능하다.

### Hexagon accelerator 부족분

- Linux driver가 `apollo-hexagon-test` selftest driver이며, `ioctl`, `mmap`,
  char device, job submission ABI가 없다.
- `apollo_hexagon_dma`는 MMIO smoke copy engine이며 4KB 제한이 있다.
- `apollo_smmu_tbu`는 fixed-window IOVA→PA translator이며 실제 SMMUv3 page-table
  datapath가 아니다.
- IREE HAL driver/device/executable loader/command buffer/synchronization 구현이 없다.
- Hexagon firmware가 CNN kernel dispatch를 처리하지 않는다.

## 다음 단계 권장 순서

1. Buildroot에 A710용 IREE runtime runner 추가.
2. qbox guest에서 tiny CNN VMFB 실행 및 output 비교.
3. Apollo Hexagon driver를 selftest에서 runtime submit ABI로 확장.
4. SMMU fixed-window를 dynamic mapping/fault reporting 가능한 모델로 확장.
5. Hexagon firmware에 command loop와 작은 conv/vector kernel 추가.
6. IREE out-of-tree `apollo-hexagon` HAL prototype 작성.

## 참조한 공식 문서

- IREE ONNX flow: <https://iree.dev/guides/ml-frameworks/onnx/>
- IREE CPU deployment: <https://iree.dev/guides/deployment-configurations/cpu/>
- IREE deployment configurations: <https://iree.dev/guides/deployment-configurations/>
- IREE C API/HAL 개념: <https://iree.dev/reference/bindings/c-api/>
- IREE HAL dialect: <https://iree.dev/reference/mlir-dialects/HAL/>

---

## Ultrapilot continuation: A710 guest artifact staging

추가 요청에 따라 IREE-CNN-005를 세분화하여, guest runtime 실행 전 단계까지
구현 가능한 artifact staging 경로를 완료했다.

### 추가 구현

1. `scripts/run_iree_tiny_cnn_host_smoke.sh`
   - 기존 host `tiny_cnn_cpu.vmfb` 외에 A710 guest용
     `tiny_cnn_aarch64.vmfb`를 추가 생성한다.
   - compile target:
     - `--iree-llvmcpu-target-triple=aarch64-unknown-linux-gnu`
     - `--iree-llvmcpu-target-cpu=cortex-a710`

2. `scripts/stage_iree_tiny_cnn_guest_artifacts.sh`
   - host smoke를 먼저 실행한다.
   - `build/iree-guest-artifacts/tiny-cnn/` 아래에 다음 artifact를 package한다.
     - `tiny_cnn.onnx`
     - `tiny_cnn.mlir`
     - `tiny_cnn_aarch64.vmfb`
     - `reference.json`
     - `host-report.json`
     - `run_tiny_cnn_guest.sh`
     - `manifest.json`

3. `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/post-build.sh`
   - `QBOX_IREE_GUEST_ARTIFACTS_DIR`가 지정된 경우에만
     `/opt/qbox/iree/tiny-cnn`으로 artifact를 복사한다.
   - 기본 minimal rootfs 동작은 변경하지 않는다.

4. `scripts/check_buildroot_arm64_lane.sh`
   - IREE host smoke script, guest artifact staging script, optional post-build hook을
     contract check에 추가했다.

5. `scripts/check_iree_cnn_pipeline_readiness.py`
   - AArch64 VMFB compile 지원 여부를 확인한다.
   - Buildroot optional artifact staging hook을 확인한다.
   - readiness summary는 21개 PASS로 확장되었다.

### 추가 검증

#### Guest artifact package 생성

```bash
./scripts/stage_iree_tiny_cnn_guest_artifacts.sh
```

결과:

```json
{
  "name": "apollo-qbox-iree-tiny-cnn-guest-artifacts",
  "status": "staged",
  "target": "aarch64-unknown-linux-gnu llvm-cpu local-task",
  "guest_install_path": "/opt/qbox/iree/tiny-cnn",
  "expected_output": "1x1x2x2xf32=[[[54 63][90 99]]]"
}
```

#### Buildroot rootfs에 optional artifact 포함

```bash
QBOX_IREE_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/tiny-cnn \
  ./scripts/build_qbox_buildroot_arm64.sh \
  > build/verification/buildroot-iree-guest-artifacts-20260428.log 2>&1
```

결과: PASS. `rootfs.cpio` 내부 artifact 확인:

```text
opt/qbox/iree/tiny-cnn/manifest.json
opt/qbox/iree/tiny-cnn/reference.json
opt/qbox/iree/tiny-cnn/run_tiny_cnn_guest.sh
opt/qbox/iree/tiny-cnn/tiny_cnn_aarch64.vmfb
```

#### Readiness checker 확장 검증

```bash
source build/iree-smoke-venv/bin/activate
./scripts/check_iree_cnn_pipeline_readiness.py \
  --require-host-tools \
  --json build/verification/iree-cnn-readiness-continuation.json
```

결과:

```text
SUMMARY {"pass": 21}
```

분류:

```json
{
  "a710_cpu_iree_baseline": "artifact_ready: boot/rootfs/kernel lane exists and AArch64 VMFB guest artifacts can be staged; IREE runtime packaging is still missing",
  "hexagon_iree_accelerator": "not_ready: requires HAL driver/device, command ABI, executable loader, user submit driver, dynamic SMMU mapping, and Hexagon kernels",
  "smmu_dma_model": "smoke_ready_only: fixed-window translated TLM path with 4KiB DMA smoke limit"
}
```

#### QBox boot 회귀 검증

```bash
./scripts/stage_buildroot_artifacts.sh
QBOX_BOOT_TIMEOUT=20 \
QBOX_BOOT_LOG=build/verification/qbox-boot-iree-guest-artifacts-20260428.log \
  ./scripts/run_qbox_buildroot_boot.sh
```

확인된 marker:

```text
APOLLO_HEXAGON_DMA: path=smmu-translated stream-id=0x1 caps=0x5
apollo-hexagon-test 1c220000.hexagon: probe ok
Run /sbin/init as init process
apollo-qbox login:
```

결과: optional IREE artifact가 포함된 rootfs로도 기존 Apollo/QBox boot lane과
Hexagon/SMMU DMA smoke가 유지됨을 확인했다.

### 현재 남은 한계

- guest 안에는 아직 `iree-run-module`이 없다. 따라서 `run_tiny_cnn_guest.sh`는
  runtime package가 추가되기 전까지 `127`로 실패하도록 명시적으로 guard한다.
- 이번 단계는 A710 guest 실행을 위한 VMFB/reference/runner staging 완료이며,
  guest 내부 실제 inference 실행은 다음 task인 IREE runtime packaging 이후 가능하다.
- Hexagon accelerator 실행은 여전히 HAL/driver/firmware/SMMU dynamic mapping이
  필요하다.
