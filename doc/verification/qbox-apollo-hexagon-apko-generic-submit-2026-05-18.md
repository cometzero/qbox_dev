# Apollo Hexagon APKO generic submit 검증

날짜: 2026-05-18
작업공간: `/build/qbox_dev`
브랜치: `feature/qbox_dev`

## 요약

리뷰 반영 결과, 이전 `APKO lane 4 scaffold` 상태에서 멈추지 않고
`apollo-hexagon-apko-v0` header, executable handle, generic submit ioctl,
fault retrieval ioctl, guest HAL APKO loader, QBox guest VADD/CNN APKO
smoke까지 연결했다.

이번 결과는 repo-local APKO sidecar bridge의 functional slice다. 아직
upstream IREE compiler가 VMFB 내부 HAL executable data로 APKO를 직접 packaging하는
target backend는 아니다.

2026-05-19 리뷰 반영으로 Linux driver의 1차 behavior-preserving split도
완료했다. core/probe/ioctl table은 `apollo-hexagon.c`에 남기고, APKO executable
handle/generic submit/fault retrieval은 `apollo-hexagon-exec.c`, 기존 fixed
CNN/VADD/DMA stress compatibility path는 `apollo-hexagon-compat.c`로 분리했다.
이후 `DRM_APOLLO_HEXAGON_QUERY_CAPS`를 추가해 UMD가 generic ABI version,
supported APKO executable format, queue depth/count, fence model, SMMU page
granularity, fault record size를 runtime에서 확인하도록 했다.
추가 리뷰 반영으로 `DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_CREATE`와
`DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_DESTROY` foundation도 추가했다. 현재 context는
per-file handle lifetime, ABI version validation, queue/fence metadata return,
stale-handle rejection을 검증하는 단계이며, 아직 BO/address-space ownership이나
command ring scheduling을 담당하지 않는다.

2026-05-20 리뷰 반영으로 `DRM_IOCTL_APOLLO_HEXAGON_BO_CREATE`와
`DRM_IOCTL_APOLLO_HEXAGON_BO_DESTROY` foundation도 추가했다. 현재 BO는 DRM GEM
SHMEM helper 기반으로 per-file GEM handle과 `mmap_offset`을 제공하고,
negative smoke가 zero-size BO reject, BO create/destroy, stale BO handle reject를
검증한다. 같은 날 추가 리뷰 반영으로 `DRM_IOCTL_APOLLO_HEXAGON_BO_BIND`와
`DRM_IOCTL_APOLLO_HEXAGON_BO_UNBIND` foundation도 추가했다. 현재 BO binding은
context-owned xarray에 GEM BO reference, offset, length, usage, staged IOVA를
저장하고, negative smoke가 bad bind size, invalid context, invalid BO handle,
unaligned length, bad unbind size, bind/unbind, stale bind handle reject를
검증한다. 추가 리뷰 refresh에서는 BO_UNBIND도 `size/flags`를 검증하게 했고,
staged IOVA 계산에는 overflow guard를 추가했다. 아직 GEM page를 Apollo
TBU/SMMU hardware mapping에 install하거나 command packet binding table에
연결하지는 않는다.

같은 날 `DRM_IOCTL_APOLLO_HEXAGON_WAIT` foundation도 추가했다. 현재 WAIT은
완료된 fence의 `status`, `result`, `current_fence_seq`를 조회하고 future fence
zero-timeout을 `-ETIMEDOUT`으로 거부하는 단계다. 아직 command ring 기반 async
timeline wait는 아니다.

2026-05-20 추가 리뷰 반영으로 QBox Apollo Hexagon DMA component에 command queue
register/fault foundation을 추가했고, 이어서 최소 command packet 실행 subset을
구현했다. 새 register는 `CMDQ_BASE_LO/HI`, `CMDQ_SIZE`, `CMDQ_HEAD`,
`CMDQ_TAIL`, `CMDQ_DOORBELL`, `CMDQ_STATUS`, `CMDQ_FENCE_VALUE`,
`CMDQ_FAULT_CODE`, `CMDQ_FAULT_ADDR_LO/HI`이며, doorbell은 선형 non-wrapping
queue에서 `NOP`, `COPY`, `BARRIER`, `SIGNAL_FENCE`, `DISPATCH/VADD`를 실행한다.
empty queue, unsupported packet, malformed packet, DMA/TLM 실패는 fault register에
기록하고 기존 async IRQ/fence path로 completion을 발생시킨다. `DISPATCH/VADD`는
현재 APKO VADD smoke와 같은 8개 `u32` 입력을 읽어 4개 `f32` bit pattern으로
결과를 쓰는 첫 generic dispatch packet이다.
추가 review 반영으로 queue geometry 검증을 강화해 out-of-range head/tail이 empty
queue로 오분류되지 않게 했고, command queue base+offset overflow guard, COPY DMA
fault coverage, `DISPATCH/VADD` 성공 및 DMA fault coverage를 추가했다. 이어서
	Linux driver의 APKO VADD generic submit은 shared SRAM에 32-byte `DISPATCH/VADD`
	packet을 쓰고 `CMDQ_BASE/HEAD/TAIL/DOORBELL` register를 program하도록 연결했다.
	기존 APKO CNN과 fixed CNN/VADD ioctl은 compatibility path로 유지한다.
	추가 driver 리뷰 반영으로 `DRM_IOCTL_APOLLO_HEXAGON_CMD_SUBMIT`도
	append-only로 추가했다. 이 path는 userspace pointer 대신 GEM SHMEM command BO
	handle과 offset/size를 받아 bounded command buffer를 kernel에서 vmap/fetch한 뒤
	QBox CMDQ doorbell로 실행한다. APKO negative guest smoke는 `SIGNAL_FENCE`
	packet으로 status/result/fence return을 검증한다. 추가 리뷰 반영으로 invalid
	IOVA `COPY` packet의 guest-visible fault retrieval도 검증한다.
	추가 lifetime 리뷰 반영으로 VADD `CMD_SUBMIT`은 file-level lock을 잡은 채
	CMDQ completion을 기다리지 않는다. Binding table lookup은 짧은 critical section에
	한정하고, output BO는 GEM object ref를 잡아 wait 이후 copy-back까지 lifetime을
	보장한다.
	추가 진행으로 VADD `CMD_SUBMIT` happy path는
	`LOAD_EXECUTABLE -> DISPATCH(exec-slot)` 2-packet buffer를 제출한다. 아직 true
	APKO code/payload loading, tensor BO binding table 기반 dispatch, CNN/MNIST CMDQ
	dispatch는 다음 slice로 남아 있다.

## 변경 범위

- Linux UAPI:
  - `sources/linux/include/uapi/drm/apollo_hexagon_accel.h`
  - `DRM_IOCTL_APOLLO_HEXAGON_EXEC_CREATE`
  - `DRM_IOCTL_APOLLO_HEXAGON_EXEC_DESTROY`
  - `DRM_IOCTL_APOLLO_HEXAGON_SUBMIT`
  - `DRM_IOCTL_APOLLO_HEXAGON_GET_FAULT`
  - `DRM_IOCTL_APOLLO_HEXAGON_QUERY_CAPS`
  - `DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_CREATE`
  - `DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_DESTROY`
  - `DRM_IOCTL_APOLLO_HEXAGON_BO_CREATE`
  - `DRM_IOCTL_APOLLO_HEXAGON_BO_DESTROY`
  - `DRM_IOCTL_APOLLO_HEXAGON_WAIT`
  - `DRM_IOCTL_APOLLO_HEXAGON_BO_BIND`
  - `DRM_IOCTL_APOLLO_HEXAGON_BO_UNBIND`
  - `DRM_IOCTL_APOLLO_HEXAGON_CMD_SUBMIT`
- Linux driver:
  - `sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon.c`
  - `sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-bo.c`
  - `sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-context.c`
  - `sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-exec.c`
  - `sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-fence.c`
  - `sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-compat.c`
  - `sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon.h`
  - `sources/linux/drivers/accel/apollo_hexagon/Kconfig`
  - `sources/linux/drivers/accel/apollo_hexagon/Makefile`
  - core/probe/ioctl table과 APKO exec/context/compat path 분리
  - per-file context xarray와 `CONTEXT_CREATE/DESTROY` validation
  - DRM GEM SHMEM 기반 BO create/destroy와 `mmap_offset` reporting
  - context-owned BO bind/unbind metadata, staged IOVA reporting, overflow guard
  - GEM SHMEM command BO packet fetch와 `CMD_SUBMIT` doorbell/fence/status return
  - VADD `CMD_SUBMIT` output BO ref retention과 file-lock-shortened submit lifetime
  - completed-fence `WAIT` snapshot과 timeout validation
  - per-file executable xarray와 APKO header validation
  - generic submit path와 `GET_FAULT` retrieval
  - `QUERY_CAPS` 기반 generic ABI/executable format/fault record capability
    reporting
  - fixed CNN/VADD/DMA stress compatibility submit 유지
  - hardware completion status/result 기반 fault record 저장
  - runtime markers: `APKO dispatch start`, `generic submit ok`,
    `APKO dispatch complete`
- Guest UMD/HAL:
  - `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/`
  - APKO metadata parsing
  - `QUERY_CAPS` validation and runtime marker
  - `EXEC_CREATE -> SUBMIT -> EXEC_DESTROY`
  - dynamic HAL plugin API version 2
- Staging/smoke:
  - `scripts/stage_iree_vector_add_guest_artifacts.sh`
  - `scripts/stage_iree_tiny_cnn_guest_artifacts.sh`
  - `scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh`
  - `scripts/run_iree_apko_cnn_hexagon_qbox_guest_smoke.sh`
  - `scripts/run_iree_apko_negative_hexagon_qbox_guest_smoke.sh`
- QBox component:
  - `sources/qbox/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h`
  - `sources/qbox/tests/components/apollo_hexagon_dma/apollo-hexagon-dma-tests.cc`
  - command queue register/fault foundation
  - `NOP/COPY/BARRIER/SIGNAL_FENCE` packet execution subset
  - empty queue, unsupported packet, COPY/BARRIER/SIGNAL completion component tests

## 검증 명령

```bash
git diff --check && git -C sources/linux diff --check
bash -n scripts/*.sh
PYTHONPYCACHEPREFIX=/tmp/qbox-pycache python3 -m py_compile \
  scripts/qbox_pty_runner.py \
  scripts/check_qbox_smmuv3_compliance.py \
  scripts/check_iree_cnn_pipeline_readiness.py
./scripts/check_buildroot_arm64_lane.sh
./scripts/build_apollo_hexagon_guest_tools.sh
python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . \
  --json build/verification/iree-readiness-apko-review-refresh2-2026-05-18.json
python3 scripts/check_qbox_smmuv3_compliance.py --repo .
./scripts/build_qbox_linux_arm64.sh
./scripts/stage_buildroot_artifacts.sh
QBOX_IREE_TINY_CNN_SKIP_HOST_SMOKE=1 \
  ./scripts/stage_iree_tiny_cnn_guest_artifacts.sh
QBOX_IREE_VECTOR_ADD_SKIP_HOST_SMOKE=1 \
  ./scripts/stage_iree_vector_add_guest_artifacts.sh
QBOX_APKO_VADD_HEXAGON_GUEST_SMOKE_STAMP=20260518-review \
  ./scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh
QBOX_APKO_CNN_HEXAGON_GUEST_SMOKE_STAMP=20260518-review \
  ./scripts/run_iree_apko_cnn_hexagon_qbox_guest_smoke.sh
QBOX_APKO_NEGATIVE_HEXAGON_GUEST_SMOKE_STAMP=20260518-review \
  ./scripts/run_iree_apko_negative_hexagon_qbox_guest_smoke.sh
./scripts/build_qbox_linux_arm64.sh
./scripts/stage_buildroot_artifacts.sh
QBOX_APKO_VADD_HEXAGON_GUEST_SMOKE_STAMP=20260518-getfault2 \
  ./scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh
QBOX_APKO_NEGATIVE_HEXAGON_GUEST_SMOKE_STAMP=20260518-getfault2 \
  ./scripts/run_iree_apko_negative_hexagon_qbox_guest_smoke.sh
python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . \
  --json build/verification/iree-readiness-apko-getfault2-2026-05-18.json
./scripts/build_qbox_linux_arm64.sh
./scripts/stage_buildroot_artifacts.sh
./scripts/check_buildroot_arm64_lane.sh
python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . \
  --json build/verification/iree-readiness-apko-compat-split-2026-05-19.json
python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . \
  --json build/verification/iree-readiness-apko-compat-split-final-2026-05-19.json
python3 scripts/check_qbox_smmuv3_compliance.py --repo .
git diff --check && git -C sources/linux diff --check
bash -n scripts/*.sh
PYTHONPYCACHEPREFIX=/tmp/qbox-pycache python3 -m py_compile \
  scripts/qbox_pty_runner.py \
  scripts/check_qbox_smmuv3_compliance.py \
  scripts/check_iree_cnn_pipeline_readiness.py
./scripts/build_apollo_hexagon_guest_tools.sh
./scripts/build_qbox_linux_arm64.sh
./scripts/check_buildroot_arm64_lane.sh
python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . \
  --json build/verification/iree-readiness-context-2026-05-19.json
python3 scripts/check_qbox_smmuv3_compliance.py --repo .
QBOX_APKO_VADD_HEXAGON_GUEST_SMOKE_STAMP=20260519-compat-split \
  ./scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh
QBOX_APKO_NEGATIVE_HEXAGON_GUEST_SMOKE_STAMP=20260519-compat-split \
  ./scripts/run_iree_apko_negative_hexagon_qbox_guest_smoke.sh
QBOX_VECTOR_ADD_HEXAGON_GUEST_SMOKE_STAMP=20260519-compat-split \
  ./scripts/run_iree_vector_add_hexagon_qbox_guest_smoke.sh
QBOX_IREE_TINY_CNN_SKIP_HOST_SMOKE=1 \
  ./scripts/stage_iree_tiny_cnn_guest_artifacts.sh
QBOX_IREE_VECTOR_ADD_SKIP_HOST_SMOKE=1 \
  ./scripts/stage_iree_vector_add_guest_artifacts.sh
QBOX_IREE_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/tiny-cnn \
QBOX_IREE_VECTOR_ADD_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/vector-add \
  ./scripts/build_qbox_buildroot_arm64.sh
./scripts/stage_buildroot_artifacts.sh
QBOX_APKO_VADD_HEXAGON_GUEST_SMOKE_STAMP=20260519-query-caps \
  ./scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh
QBOX_APKO_NEGATIVE_HEXAGON_GUEST_SMOKE_STAMP=20260519-query-caps \
  ./scripts/run_iree_apko_negative_hexagon_qbox_guest_smoke.sh
QBOX_VECTOR_ADD_HEXAGON_GUEST_SMOKE_STAMP=20260519-query-caps \
  ./scripts/run_iree_vector_add_hexagon_qbox_guest_smoke.sh
QBOX_IREE_VECTOR_ADD_SKIP_HOST_SMOKE=1 \
  ./scripts/stage_iree_vector_add_guest_artifacts.sh
QBOX_IREE_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/tiny-cnn \
QBOX_IREE_VECTOR_ADD_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/vector-add \
  ./scripts/build_qbox_buildroot_arm64.sh
./scripts/stage_buildroot_artifacts.sh
QBOX_APKO_NEGATIVE_HEXAGON_GUEST_SMOKE_STAMP=20260519-context \
  ./scripts/run_iree_apko_negative_hexagon_qbox_guest_smoke.sh
git diff --check && git -C sources/linux diff --check
bash -n scripts/*.sh
PYTHONPYCACHEPREFIX=/tmp/qbox-pycache python3 -m py_compile \
  scripts/qbox_pty_runner.py \
  scripts/check_qbox_smmuv3_compliance.py \
  scripts/check_iree_cnn_pipeline_readiness.py
./scripts/check_buildroot_arm64_lane.sh
python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . \
  --json build/verification/iree-readiness-context-review-2026-05-19.json
python3 scripts/check_qbox_smmuv3_compliance.py --repo .
git diff --check && git -C sources/linux diff --check
bash -n scripts/*.sh
PYTHONPYCACHEPREFIX=/tmp/qbox-pycache python3 -m py_compile \
  scripts/qbox_pty_runner.py \
  scripts/check_qbox_smmuv3_compliance.py \
  scripts/check_iree_cnn_pipeline_readiness.py
./scripts/build_apollo_hexagon_guest_tools.sh
./scripts/build_qbox_linux_arm64.sh
./scripts/check_buildroot_arm64_lane.sh
python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . \
  --json build/verification/iree-readiness-bo-prebuild-2026-05-20.json
python3 scripts/check_qbox_smmuv3_compliance.py --repo .
QBOX_IREE_TINY_CNN_SKIP_HOST_SMOKE=1 \
  ./scripts/stage_iree_tiny_cnn_guest_artifacts.sh
QBOX_IREE_VECTOR_ADD_SKIP_HOST_SMOKE=1 \
  ./scripts/stage_iree_vector_add_guest_artifacts.sh
QBOX_IREE_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/tiny-cnn \
QBOX_IREE_VECTOR_ADD_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/vector-add \
  ./scripts/build_qbox_buildroot_arm64.sh
./scripts/stage_buildroot_artifacts.sh
QBOX_APKO_NEGATIVE_HEXAGON_GUEST_SMOKE_STAMP=20260520-bo \
  ./scripts/run_iree_apko_negative_hexagon_qbox_guest_smoke.sh
python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . \
  --json build/verification/iree-readiness-bo-final-2026-05-20.json
./scripts/build_qbox_linux_arm64.sh
./scripts/stage_buildroot_artifacts.sh
QBOX_APKO_NEGATIVE_HEXAGON_GUEST_SMOKE_STAMP=20260520-bo-final \
  ./scripts/run_iree_apko_negative_hexagon_qbox_guest_smoke.sh
python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . \
  --json build/verification/iree-readiness-wait-2026-05-20.json
./scripts/build_apollo_hexagon_guest_tools.sh
./scripts/build_qbox_linux_arm64.sh
QBOX_IREE_VECTOR_ADD_SKIP_HOST_SMOKE=1 \
  ./scripts/stage_iree_vector_add_guest_artifacts.sh
QBOX_IREE_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/tiny-cnn \
QBOX_IREE_VECTOR_ADD_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/vector-add \
  ./scripts/build_qbox_buildroot_arm64.sh
./scripts/stage_buildroot_artifacts.sh
QBOX_APKO_NEGATIVE_HEXAGON_GUEST_SMOKE_STAMP=20260520-wait2 \
  ./scripts/run_iree_apko_negative_hexagon_qbox_guest_smoke.sh
git diff --check && git -C sources/linux diff --check && git -C sources/qbox diff --check
bash -n scripts/*.sh
PYTHONPYCACHEPREFIX=/tmp/qbox-pycache python3 -m py_compile \
  scripts/qbox_pty_runner.py \
  scripts/check_qbox_smmuv3_compliance.py \
  scripts/check_iree_cnn_pipeline_readiness.py
cmake --build sources/qbox/build --target apollo-hexagon-dma-tests --parallel
ctest --test-dir sources/qbox/build -R '^apollo-hexagon-dma-tests$' \
  --output-on-failure
./scripts/build_qbox_buildroot_platform.sh
./scripts/check_buildroot_arm64_lane.sh
python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . \
  --json build/verification/iree-readiness-cmdq-foundation-2026-05-20.json
QBOX_APKO_NEGATIVE_HEXAGON_GUEST_SMOKE_STAMP=20260520-cmdq-foundation \
  ./scripts/run_iree_apko_negative_hexagon_qbox_guest_smoke.sh
```

## 결과

- static/syntax: PASS
- lane contract: PASS
- guest tools build: PASS
- APKO staging manifest refresh: PASS
  - `build/iree-guest-artifacts/tiny-cnn/manifest.json`
  - `build/iree-guest-artifacts/vector-add/manifest.json`
  - both now record `generic_command_buffer=generic-submit` and describe
    fixed CNN/VADD as compatibility paths only.
- IREE readiness checker: PASS, `SUMMARY {"missing": 5, "pass": 51}`
  - missing host tools/modules are unchanged:
    `iree-import-onnx`, `iree-compile`, `iree-run-module`, Python `onnx`,
    Python `numpy`.
- SMMUv3 contract: PASS, `SUMMARY {"pass": 1063}`
- Linux ARM64 build: PASS
- GET_FAULT 리뷰 보강 후 Linux ARM64 rebuild: PASS
  - rebuilt object: `drivers/accel/apollo_hexagon/apollo-hexagon.o`
  - Image: `build/linux-a710/arch/arm64/boot/Image`
- 2026-05-19 driver split 후 Linux ARM64 rebuild: PASS
  - rebuilt objects:
    - `drivers/accel/apollo_hexagon/apollo-hexagon.o`
    - `drivers/accel/apollo_hexagon/apollo-hexagon-exec.o`
    - `drivers/accel/apollo_hexagon/apollo-hexagon-compat.o`
  - Image: `build/linux-a710/arch/arm64/boot/Image`
- 2026-05-19 context foundation 후 Linux ARM64 rebuild: PASS
  - rebuilt object:
    - `drivers/accel/apollo_hexagon/apollo-hexagon-context.o`
  - Image: `build/linux-a710/arch/arm64/boot/Image`
- 2026-05-19 Buildroot artifact staging: PASS
  - staged into
    `sources/qbox/platforms/buildroot/fw/Artifacts`
- 2026-05-19 lane contract after split: PASS
  - `Apollo Hexagon fixed compat submit driver exists`
  - `Apollo Hexagon fixed compat submit object present`
  - `Apollo Hexagon executable submit object present`
  - `Apollo Hexagon generic context driver exists`
  - `Apollo Hexagon generic context object present`
  - `Apollo Hexagon generic query-caps UAPI`
  - `Apollo Hexagon generic context create UAPI`
  - `Linux Hexagon generic query-caps ioctl`
  - `Linux Hexagon generic context create ioctl`
  - `Linux Hexagon generic context create implementation`
  - `Apollo IREE Hexagon generic query-caps ABI`
  - `Apollo IREE Hexagon generic context create ABI`
  - `Apollo IREE Hexagon context ABI negative test`
  - `Linux Hexagon dynamic SMMU SG map present`
  - `Linux Hexagon SG DMA stress verification present`
- 2026-05-19 IREE readiness checker: PASS, `SUMMARY {"missing": 5, "pass": 51}`
  - final refresh JSON:
    `build/verification/iree-readiness-apko-compat-split-final-2026-05-19.json`
  - context refresh JSON:
    `build/verification/iree-readiness-context-2026-05-19.json`
  - remaining missing host tools/modules are unchanged:
    `iree-import-onnx`, `iree-compile`, `iree-run-module`, Python `onnx`,
    Python `numpy`.
- 2026-05-19 context review checker refresh: PASS,
  `SUMMARY {"missing": 5, "pass": 52}`
  - JSON:
    `build/verification/iree-readiness-context-review-2026-05-19.json`
  - new checker gate:
    `linux_driver_generic_kconfig`
  - remaining missing host tools/modules are unchanged:
    `iree-import-onnx`, `iree-compile`, `iree-run-module`, Python `onnx`,
    Python `numpy`.
- 2026-05-19 SMMUv3 contract: PASS, `SUMMARY {"pass": 1063}`
- 2026-05-20 BO foundation static/syntax: PASS
  - `git diff --check && git -C sources/linux diff --check`
  - `bash -n scripts/*.sh`
  - `PYTHONPYCACHEPREFIX=/tmp/qbox-pycache python3 -m py_compile ...`
- 2026-05-20 BO foundation guest tools build: PASS
  - AArch64:
    `build/apollo-hexagon-guest-tools/bin/apollo-hexagon-apko-negative`
  - host:
    `build/apollo-hexagon-guest-tools/host-bin/apollo-hexagon-apko-negative`
- 2026-05-20 BO foundation Linux ARM64 build: PASS
  - rebuilt objects include:
    - `drivers/gpu/drm/drm_gem_shmem_helper.o`
    - `drivers/accel/apollo_hexagon/apollo-hexagon-bo.o`
  - Image: `build/linux-a710/arch/arm64/boot/Image`
- 2026-05-20 BO foundation review refresh Linux ARM64 build: PASS
  - Kconfig refresh:
    `DRM_ACCEL_APOLLO_HEXAGON` now has `depends on MMU` before selecting
    `DRM_GEM_SHMEM_HELPER`.
  - BO create refresh:
    redundant explicit mmap-offset creation was removed because
    `drm_gem_shmem_create()` initializes the GEM mmap offset.
  - Image: `build/linux-a710/arch/arm64/boot/Image`
- 2026-05-20 lane contract: PASS
  - `Apollo Hexagon generic BO driver exists`
  - `Apollo Hexagon generic BO object present`
  - `Apollo Hexagon GEM SHMEM MMU dependency`
  - `Apollo Hexagon GEM SHMEM helper dependency present`
  - `Apollo Hexagon generic BO create UAPI`
  - `Linux Hexagon generic BO create ioctl`
  - `Linux Hexagon generic BO SHMEM allocation`
  - `Apollo IREE Hexagon BO lifecycle test`
- 2026-05-20 WAIT foundation lane contract: PASS
  - `Apollo Hexagon generic fence wait driver exists`
  - `Apollo Hexagon generic fence wait object present`
  - `Apollo Hexagon generic wait UAPI`
  - `Linux Hexagon generic wait ioctl`
  - `Linux Hexagon generic wait implementation`
  - `Apollo IREE Hexagon generic wait ABI`
  - `Apollo IREE Hexagon wait completion test`
  - `Apollo IREE Hexagon wait timeout negative test`
- 2026-05-20 BO bind review refresh static/syntax: PASS
  - `git diff --check && git -C sources/linux diff --check`
  - `bash -n scripts/*.sh`
  - `PYTHONPYCACHEPREFIX=/tmp/qbox-pycache python3 -m py_compile ...`
- 2026-05-20 BO bind review refresh Linux ARM64 build: PASS
  - rebuilt objects include:
    - `drivers/accel/apollo_hexagon/apollo-hexagon-bo.o`
    - `drivers/accel/apollo_hexagon/apollo-hexagon-context.o`
    - `drivers/accel/apollo_hexagon/apollo-hexagon-fence.o`
  - Image: `build/linux-a710/arch/arm64/boot/Image`
- 2026-05-20 BO bind review refresh guest tools build: PASS
  - AArch64:
    `build/apollo-hexagon-guest-tools/bin/apollo-hexagon-apko-negative`
  - host:
    `build/apollo-hexagon-guest-tools/host-bin/apollo-hexagon-apko-negative`
- 2026-05-20 BO bind review refresh lane contract: PASS
  - `Apollo IREE Hexagon BO unbind size negative test`
  - `Apollo IREE Hexagon BO bind lifecycle test`
- 2026-05-20 BO bind review refresh IREE readiness checker: PASS,
  `SUMMARY {"missing": 5, "pass": 54}`
  - JSON:
    `build/verification/iree-readiness-bo-bind-review-2026-05-20.json`
  - remaining missing host tools/modules are unchanged:
    `iree-import-onnx`, `iree-compile`, `iree-run-module`, Python `onnx`,
    Python `numpy`.
- 2026-05-20 command queue foundation static/syntax: PASS
  - `git diff --check && git -C sources/linux diff --check && git -C sources/qbox diff --check`
  - `bash -n scripts/*.sh`
  - `PYTHONPYCACHEPREFIX=/tmp/qbox-pycache python3 -m py_compile ...`
- 2026-05-20 command queue foundation QBox component build/test: PASS
  - `cmake --build sources/qbox/build --target apollo-hexagon-dma-tests --parallel`
  - `ctest --test-dir sources/qbox/build -R '^apollo-hexagon-dma-tests$' --output-on-failure`
  - result: `1/1` test passed
- 2026-05-20 command queue foundation QBox platform build: PASS
  - `./scripts/build_qbox_buildroot_platform.sh`
- 2026-05-20 command queue foundation lane contract: PASS
  - `QBox Apollo Hexagon command queue doorbell register`
  - `QBox Apollo Hexagon command queue fault register`
  - `QBox Apollo Hexagon unsupported command packet fault`
  - `QBox Apollo Hexagon empty command queue fault component test`
  - `QBox Apollo Hexagon unsupported command packet fault component test`
- 2026-05-20 command queue foundation IREE readiness checker: PASS,
  `SUMMARY {"missing": 5, "pass": 55}`
  - JSON:
    `build/verification/iree-readiness-cmdq-foundation-2026-05-20.json`
  - remaining missing host tools/modules are unchanged:
    `iree-import-onnx`, `iree-compile`, `iree-run-module`, Python `onnx`,
    Python `numpy`.
- 2026-05-20 command queue packet subset QBox component build/test: PASS
  - `cmake --build sources/qbox/build --target apollo-hexagon-dma-tests --parallel`
  - `ctest --test-dir sources/qbox/build -R '^apollo-hexagon-dma-tests$' --output-on-failure`
  - result: `1/1` test passed
  - coverage: empty queue fault, unsupported packet fault,
    malformed queue geometry, COPY packet DMA fault,
    `NOP/COPY/BARRIER/SIGNAL_FENCE` successful execution and async
    fence/IRQ completion.
- 2026-05-20 command queue packet subset static/syntax: PASS
  - `git diff --check && git -C sources/linux diff --check && git -C sources/qbox diff --check`
  - `bash -n scripts/*.sh`
  - `PYTHONPYCACHEPREFIX=/tmp/qbox-pycache python3 -m py_compile scripts/qbox_pty_runner.py scripts/check_qbox_smmuv3_compliance.py scripts/check_iree_cnn_pipeline_readiness.py`
- 2026-05-20 command queue packet subset lane contract: PASS
  - `./scripts/check_buildroot_arm64_lane.sh`
  - new markers:
    `QBox Apollo Hexagon command queue COPY opcode`,
    `QBox Apollo Hexagon command queue SIGNAL_FENCE opcode`,
    `QBox Apollo Hexagon command queue COPY packet executor`,
    `QBox Apollo Hexagon command queue completion handler`,
    `QBox Apollo Hexagon command queue address overflow guard`,
    `QBox Apollo Hexagon malformed command queue geometry component test`,
    `QBox Apollo Hexagon command queue DMA fault component test`,
    `QBox Apollo Hexagon command queue COPY/BARRIER/SIGNAL component test`.
- 2026-05-20 command queue packet subset IREE readiness checker: PASS,
  `SUMMARY {"missing": 5, "pass": 55}`
  - JSON:
    `build/verification/iree-readiness-cmdq-packet-subset-2026-05-20.json`
  - remaining missing host tools/modules are unchanged:
    `iree-import-onnx`, `iree-compile`, `iree-run-module`, Python `onnx`,
    Python `numpy`.
- 2026-05-20 command queue packet subset QBox platform build: PASS
  - `./scripts/build_qbox_buildroot_platform.sh`
  - result: `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`
- 2026-05-20 command queue fault review refresh: PASS
  - `cmake --build sources/qbox/build --target apollo-hexagon-dma-tests --parallel`
  - `ctest --test-dir sources/qbox/build -R '^apollo-hexagon-dma-tests$' --output-on-failure`
  - `git diff --check && git -C sources/linux diff --check && git -C sources/qbox diff --check`
  - `bash -n scripts/*.sh`
  - `PYTHONPYCACHEPREFIX=/tmp/qbox-pycache python3 -m py_compile scripts/qbox_pty_runner.py scripts/check_qbox_smmuv3_compliance.py scripts/check_iree_cnn_pipeline_readiness.py`
  - `./scripts/check_buildroot_arm64_lane.sh`
  - `./scripts/build_qbox_buildroot_platform.sh`
  - readiness JSON:
    `build/verification/iree-readiness-cmdq-fault-review-2026-05-20.json`
- 2026-05-20 command queue DISPATCH/VADD review refresh: PASS
  - `cmake --build sources/qbox/build --target apollo-hexagon-dma-tests --parallel`
  - `ctest --test-dir sources/qbox/build -R '^apollo-hexagon-dma-tests$' --output-on-failure`
  - result: `1/1` test passed
  - `git diff --check && git -C sources/linux diff --check && git -C sources/qbox diff --check`
  - `bash -n scripts/*.sh`
  - `PYTHONPYCACHEPREFIX=/tmp/qbox-pycache python3 -m py_compile scripts/qbox_pty_runner.py scripts/check_qbox_smmuv3_compliance.py scripts/check_iree_cnn_pipeline_readiness.py`
  - `./scripts/check_buildroot_arm64_lane.sh`
  - `python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . --json build/verification/iree-readiness-cmdq-dispatch-vadd-2026-05-20.json`
  - readiness result: `SUMMARY {"missing": 5, "pass": 55}`
  - `./scripts/build_qbox_buildroot_platform.sh`
  - result: `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`
  - new coverage: `CMDQ_OPCODE_DISPATCH`, `CMDQ_DISPATCH_KIND_VADD`,
    `execute_dispatch_packet`, `execute_vadd_dispatch_packet`,
    `CommandQueueDispatchesVadd`, `CommandQueueDispatchReportsDmaFault`.
- 2026-05-20 APKO VADD Linux CMDQ driver slice: PASS
  - static/syntax:
    `git diff --check && git -C sources/linux diff --check && git -C sources/qbox diff --check`
  - shell syntax: `bash -n scripts/*.sh`
  - Python syntax:
    `PYTHONPYCACHEPREFIX=/tmp/qbox-pycache python3 -m py_compile scripts/qbox_pty_runner.py scripts/check_qbox_smmuv3_compliance.py scripts/check_iree_cnn_pipeline_readiness.py`
  - lane contract: `./scripts/check_buildroot_arm64_lane.sh`
  - readiness:
    `python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . --json build/verification/iree-readiness-cmdq-driver-vadd-2026-05-20.json`
  - readiness result: `SUMMARY {"missing": 5, "pass": 56}`
  - Linux build: `./scripts/build_qbox_linux_arm64.sh`
  - staged artifacts: `./scripts/stage_buildroot_artifacts.sh`
  - APKO VADD CMDQ smoke:
    `QBOX_APKO_VADD_HEXAGON_GUEST_SMOKE_STAMP=20260520-cmdq-driver2 ./scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh`
  - APKO VADD CMDQ smoke result: PASS,
    `PASS: QBox guest APKO VADD output matched`
  - log:
    `build/verification/qbox-iree-apko-vadd-hexagon-guest-20260520-cmdq-driver2.log`
  - boot log:
    `build/verification/qbox-iree-apko-vadd-hexagon-guest-boot-20260520-cmdq-driver2.log`
  - key markers:
    `max_command_bytes=32`,
    `APOLLO_HEXAGON_DMA: command queue doorbell base=0x10012000`,
    `APOLLO_HEXAGON_DMA: command dispatch vadd`,
    `APOLLO_HEXAGON_DMA: command queue complete`,
    `APKO CMDQ dispatch complete handle=1 kind=2 head=32 fence=2`,
    `4xf32=11 22 33 44`.
  - note: first smoke attempt proved the runtime path but failed exact marker
    matching because SystemC host logs interleaved inside the kernel
    `APKO CMDQ dispatch start` line. The smoke marker was changed to require
    the CMDQ start prefix plus QBox command-dispatch and command-complete
    markers, then the smoke passed.
  - APKO CNN compatibility smoke:
    `QBOX_APKO_CNN_HEXAGON_GUEST_SMOKE_STAMP=20260520-cmdq-driver ./scripts/run_iree_apko_cnn_hexagon_qbox_guest_smoke.sh`
  - APKO CNN compatibility result: PASS,
    `PASS: QBox guest APKO CNN output matched`
  - APKO CNN compatibility log:
    `build/verification/qbox-iree-apko-cnn-hexagon-guest-20260520-cmdq-driver.log`
  - APKO CNN compatibility boot log:
    `build/verification/qbox-iree-apko-cnn-hexagon-guest-boot-20260520-cmdq-driver.log`
- 2026-05-20 command BO submit driver slice: PASS
  - static/syntax:
    `git diff --check && git -C sources/linux diff --check && git -C sources/qbox diff --check`
  - shell syntax: `bash -n scripts/*.sh`
  - Python syntax:
    `PYTHONPYCACHEPREFIX=/tmp/qbox-pycache python3 -m py_compile scripts/qbox_pty_runner.py scripts/check_qbox_smmuv3_compliance.py scripts/check_iree_cnn_pipeline_readiness.py`
  - lane contract: `./scripts/check_buildroot_arm64_lane.sh`
  - readiness:
    `python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . --json build/verification/iree-readiness-cmd-submit-2026-05-20.json`
  - readiness result: `SUMMARY {"missing": 5, "pass": 57}`
  - Linux build: `./scripts/build_qbox_linux_arm64.sh`
  - guest tools build: `./scripts/build_apollo_hexagon_guest_tools.sh`
  - vector-add guest artifact staging:
    `QBOX_IREE_VECTOR_ADD_SKIP_HOST_SMOKE=1 ./scripts/stage_iree_vector_add_guest_artifacts.sh`
  - Buildroot rootfs refresh:
    `QBOX_IREE_VECTOR_ADD_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/vector-add ./scripts/build_qbox_buildroot_arm64.sh`
  - staged artifacts: `./scripts/stage_buildroot_artifacts.sh`
  - APKO negative CMD_SUBMIT smoke:
    `QBOX_APKO_NEGATIVE_HEXAGON_GUEST_SMOKE_STAMP=20260520-cmd-submit ./scripts/run_iree_apko_negative_hexagon_qbox_guest_smoke.sh`
  - APKO negative CMD_SUBMIT result: PASS,
    `PASS: QBox guest APKO negative ioctl coverage matched`
  - log:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-20260520-cmd-submit.log`
  - boot log:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-boot-20260520-cmd-submit.log`
  - key markers:
    `PASS: command BO submit signal-fence ok fence=1 status=0x1 result=0x0`,
    `APOLLO_HEXAGON_DMA: command signal fence`,
    `command BO submit complete ctx=1 bo=1 queue=1 head=32 fence=1`.
- 2026-05-20 IREE readiness checker: PASS, `SUMMARY {"missing": 5, "pass": 52}`
  - JSON:
    `build/verification/iree-readiness-bo-prebuild-2026-05-20.json`
  - final JSON after kernel-review refresh:
    `build/verification/iree-readiness-bo-final-2026-05-20.json`
  - WAIT refresh: PASS, `SUMMARY {"missing": 5, "pass": 53}`
  - WAIT JSON:
    `build/verification/iree-readiness-wait-2026-05-20.json`
  - WAIT final JSON after checker refresh:
    `build/verification/iree-readiness-wait-final-2026-05-20.json`
  - review refresh JSON:
    `build/verification/iree-readiness-wait-review-2026-05-20.json`
  - remaining missing host tools/modules are unchanged:
    `iree-import-onnx`, `iree-compile`, `iree-run-module`, Python `onnx`,
    Python `numpy`.
- 2026-05-20 SMMUv3 contract: PASS, `SUMMARY {"pass": 1063}`
  - review refresh JSON:
    `build/verification/smmuv3-wait-review-2026-05-20.json`
- 2026-05-20 rootfs/staging refresh: PASS
  - refreshed guest artifacts:
    - `build/iree-guest-artifacts/tiny-cnn`
    - `build/iree-guest-artifacts/vector-add`
  - Buildroot images:
    `build/buildroot-a710/images`
  - staged QBox artifacts:
    `sources/qbox/platforms/buildroot/fw/Artifacts`
- 2026-05-20 BO bind review rootfs/staging refresh: PASS
  - refreshed guest artifacts:
    - `build/iree-guest-artifacts/tiny-cnn`
    - `build/iree-guest-artifacts/vector-add`
  - rebuilt Buildroot images:
    `build/buildroot-a710/images`
  - staged QBox artifacts:
    `sources/qbox/platforms/buildroot/fw/Artifacts`
- 2026-05-19 query-caps refresh rootfs/staging: PASS
  - refreshed guest tools in:
    - `build/iree-guest-artifacts/tiny-cnn`
    - `build/iree-guest-artifacts/vector-add`
  - rebuilt `build/buildroot-a710/images/rootfs.cpio` with both staged IREE
    artifact directories.
  - staged refreshed rootfs/DTB/Image into
    `sources/qbox/platforms/buildroot/fw/Artifacts`
- 2026-05-19 context refresh rootfs/staging: PASS
  - refreshed vector-add APKO negative helper:
    `build/iree-guest-artifacts/vector-add/bin/apollo-hexagon-apko-negative`
  - rebuilt `build/buildroot-a710/images/rootfs.cpio` with the refreshed
    vector-add APKO negative helper.
  - staged refreshed rootfs into
    `sources/qbox/platforms/buildroot/fw/Artifacts/rootfs.cpio`
- APKO VADD guest smoke: PASS
  - log: `build/verification/qbox-iree-apko-vadd-hexagon-guest-20260518-review.log`
  - boot log:
    `build/verification/qbox-iree-apko-vadd-hexagon-guest-boot-20260518-review.log`
  - refreshed log after GET_FAULT status/result propagation:
    `build/verification/qbox-iree-apko-vadd-hexagon-guest-20260518-getfault2.log`
  - refreshed boot log:
    `build/verification/qbox-iree-apko-vadd-hexagon-guest-boot-20260518-getfault2.log`
  - split refresh log:
    `build/verification/qbox-iree-apko-vadd-hexagon-guest-20260519-compat-split.log`
  - split refresh boot log:
    `build/verification/qbox-iree-apko-vadd-hexagon-guest-boot-20260519-compat-split.log`
  - query-caps refresh log:
    `build/verification/qbox-iree-apko-vadd-hexagon-guest-20260519-query-caps.log`
  - query-caps refresh boot log:
    `build/verification/qbox-iree-apko-vadd-hexagon-guest-boot-20260519-query-caps.log`
  - CMDQ driver refresh log:
    `build/verification/qbox-iree-apko-vadd-hexagon-guest-20260520-cmdq-driver2.log`
  - CMDQ driver refresh boot log:
    `build/verification/qbox-iree-apko-vadd-hexagon-guest-boot-20260520-cmdq-driver2.log`
- APKO CNN guest smoke: PASS
  - log: `build/verification/qbox-iree-apko-cnn-hexagon-guest-20260518-review.log`
  - boot log:
    `build/verification/qbox-iree-apko-cnn-hexagon-guest-boot-20260518-review.log`
  - CMDQ driver compatibility refresh log:
    `build/verification/qbox-iree-apko-cnn-hexagon-guest-20260520-cmdq-driver.log`
  - CMDQ driver compatibility refresh boot log:
    `build/verification/qbox-iree-apko-cnn-hexagon-guest-boot-20260520-cmdq-driver.log`
- APKO negative guest smoke: PASS
  - log:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-20260518-review.log`
  - boot log:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-boot-20260518-review.log`
  - refreshed log after GET_FAULT status/result propagation:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-20260518-getfault2.log`
  - refreshed boot log:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-boot-20260518-getfault2.log`
  - split refresh log:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-20260519-compat-split.log`
  - split refresh boot log:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-boot-20260519-compat-split.log`
  - query-caps refresh log:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-20260519-query-caps.log`
  - query-caps refresh boot log:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-boot-20260519-query-caps.log`
  - context refresh log:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-20260519-context.log`
  - context refresh boot log:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-boot-20260519-context.log`
  - context refresh markers:
    `PASS: bad context ABI version rejected errno=Invalid argument`,
    `PASS: context create/destroy ok handle=1 queues=2`,
    `PASS: destroyed context handle rejected errno=No such file or directory`
  - BO refresh log:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-20260520-bo.log`
  - BO refresh boot log:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-boot-20260520-bo.log`
  - BO refresh markers:
    `PASS: bad BO size rejected errno=Invalid argument`,
    `PASS: BO create/destroy ok handle=1 size=4096 mmap_offset=0x100000000`,
    `PASS: destroyed BO handle rejected errno=Invalid argument`
  - BO final refresh log after kernel-review fix:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-20260520-bo-final.log`
  - BO final refresh boot log after kernel-review fix:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-boot-20260520-bo-final.log`
  - BO final refresh markers:
    `PASS: bad BO size rejected errno=Invalid argument`,
    `PASS: BO create/destroy ok handle=1 size=4096 mmap_offset=0x100000000`,
    `PASS: destroyed BO handle rejected errno=Invalid argument`
  - WAIT refresh log:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-20260520-wait2.log`
  - WAIT refresh boot log:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-boot-20260520-wait2.log`
  - WAIT refresh markers:
    `PASS: bad WAIT size rejected errno=Invalid argument`,
    `PASS: zero WAIT fence rejected errno=Invalid argument`,
    `PASS: bad WAIT queue rejected errno=Invalid argument`,
    `PASS: WAIT completed fence=1 current=1 status=0x1 result=0x56414444`,
    `PASS: future WAIT fence rejected errno=Connection timed out`
  - review refresh log:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-20260520-review2.log`
  - review refresh boot log:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-boot-20260520-review2.log`
  - review refresh result:
    `PASS: QBox guest APKO negative ioctl coverage matched`
  - BO bind review refresh log:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-20260520-bobind-review.log`
  - BO bind review refresh boot log:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-boot-20260520-bobind-review.log`
  - BO bind review refresh markers:
    `PASS: bad BO bind size rejected errno=Invalid argument`,
    `PASS: bad BO bind context rejected errno=No such file or directory`,
    `PASS: bad BO bind handle rejected errno=No such file or directory`,
    `PASS: unaligned BO bind length rejected errno=Invalid argument`,
    `PASS: bad BO unbind size rejected errno=Invalid argument`,
    `PASS: BO bind/unbind ok bind=1 bo=1 iova=0x10300000 length=4096`,
    `PASS: destroyed BO bind handle rejected errno=No such file or directory`,
    `PASS: QBox guest APKO negative ioctl coverage matched`
  - command queue foundation refresh log:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-20260520-cmdq-foundation.log`
  - command queue foundation refresh boot log:
    `build/verification/qbox-iree-apko-negative-hexagon-guest-boot-20260520-cmdq-foundation.log`
  - command queue foundation refresh markers:
    `PASS: bad BO unbind size rejected errno=Invalid argument`,
    `PASS: WAIT completed fence=1 current=1 status=0x1 result=0x56414444`,
    `PASS: APKO negative ioctl coverage completed`,
    `PASS: QBox guest APKO negative ioctl coverage matched`
- Fixed compat vector-add guest smoke after split: PASS
  - log:
    `build/verification/qbox-iree-vector-add-hexagon-guest-20260519-compat-split.log`
  - boot log:
    `build/verification/qbox-iree-vector-add-hexagon-guest-boot-20260519-compat-split.log`
  - query-caps refresh log:
    `build/verification/qbox-iree-vector-add-hexagon-guest-20260519-query-caps.log`
  - query-caps refresh boot log:
    `build/verification/qbox-iree-vector-add-hexagon-guest-boot-20260519-query-caps.log`

## 핵심 런타임 marker

VADD:

```text
IREE Apollo Hexagon HAL: executable_format=apollo-hexagon-apko-v0
IREE Apollo Hexagon HAL: queues=2 command-buffer=generic-submit fence=async-irq-poll
APKO CMDQ dispatch start handle=1 kind=2 queue=1 input=32 output=16
APKO CMDQ dispatch complete handle=1 kind=2 head=32 fence=2
generic submit ok handle=1 queue=1 fence=2 status=0x56414444
APKO dispatch complete handle=1 kind=2
4xf32=11 22 33 44
```

CNN:

```text
IREE Apollo Hexagon HAL: executable_format=apollo-hexagon-apko-v0
IREE Apollo Hexagon HAL: queues=2 command-buffer=generic-submit fence=async-irq-poll
APKO dispatch start handle=1 kind=1 queue=1 input=64 output=16
generic submit ok handle=1 queue=1 fence=2 status=0x434e4e4f
APKO dispatch complete handle=1 kind=1
1x1x2x2xf32=[[[54 63][90 99]]]
```

Negative ioctl coverage:

```text
PASS: bad context ABI version rejected errno=Invalid argument
PASS: context create/destroy ok
PASS: destroyed context handle rejected errno=No such file or directory
PASS: bad BO size rejected errno=Invalid argument
PASS: BO create/destroy ok
PASS: destroyed BO handle rejected errno=Invalid argument
PASS: bad BO bind size rejected errno=Invalid argument
PASS: bad BO bind context rejected errno=No such file or directory
PASS: bad BO bind handle rejected errno=No such file or directory
PASS: unaligned BO bind length rejected errno=Invalid argument
PASS: bad BO unbind size rejected errno=Invalid argument
PASS: BO bind/unbind ok bind=
PASS: destroyed BO bind handle rejected errno=No such file or directory
PASS: bad APKO magic rejected errno=Invalid argument
PASS: bad APKO ABI version rejected errno=Invalid argument
PASS: bad APKO entry kind rejected errno=Invalid argument
PASS: bad APKO input byte count rejected errno=Invalid argument
PASS: nonzero APKO reserved field rejected errno=Invalid argument
PASS: wrong input byte count rejected errno=Invalid argument
PASS: wrong output byte count rejected errno=Invalid argument
PASS: wrong queue id rejected errno=Invalid argument
PASS: invalid input pointer rejected errno=Bad address
PASS: destroyed executable handle rejected errno=No such file or directory
PASS: empty fault record rejected errno=No data available
PASS: bad fault request size rejected errno=Invalid argument
PASS: APKO negative ioctl coverage completed
```

Fixed compatibility vector-add after split:

```text
IREE Apollo Hexagon HAL: queues=2 command-buffer=fixed fence=async-irq-poll
dynamic SMMU SG map refreshed bytes=131072 segments=8
SG DMA stress ok queue=0 fence=1 bytes=131072 segments=8 checksum=0xfda40000 status=0x53474f4b
accelerator vector add ok queue=1 fence=2 status=0x56414444
4xf32=11 22 33 44
```

Earlier generic ABI caps marker:

```text
IREE Apollo Hexagon HAL: generic_abi_version=1 executable_formats=0x00000002 max_command_bytes=0 max_queue_depth=1 fault_record_size=48
```

Current CMDQ/command-BO caps marker:

```text
IREE Apollo Hexagon HAL: generic_abi_version=1 executable_formats=0x00000002 max_command_bytes=64 max_queue_depth=1 fault_record_size=48 max_bindings_per_dispatch=2
```

## 커널 리뷰

사용한 prompt:

- `.codex/review-prompts/kernel/technical-patterns.md`
- `.codex/review-prompts/kernel/review-core.md`
- `.codex/review-prompts/kernel/callstack.md`
- `.codex/review-prompts/kernel/subsystem/subsystem.md`
- `.codex/review-prompts/kernel/subsystem/drm.md`
- `.codex/review-prompts/kernel/subsystem/mm-alloc.md`
- `.codex/review-prompts/kernel/subsystem/mm-folio.md`
- `.codex/review-prompts/kernel/subsystem/syscall.md`
- `.codex/review-prompts/kernel/subsystem/io-accessors.md`
- `.codex/review-prompts/kernel/subsystem/locking.md`
- `.codex/review-prompts/kernel/subsystem/kconfig.md`

검토한 kernel path:

- `sources/linux/include/uapi/drm/apollo_hexagon_accel.h`
- `sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon.c`
- `sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-bo.c`
- `sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-context.c`
- `sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-exec.c`
- `sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-fence.c`
- `sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-compat.c`
- `sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon.h`
- `sources/linux/drivers/accel/apollo_hexagon/Kconfig`
- `sources/linux/drivers/accel/apollo_hexagon/Makefile`

리뷰 결과:

- 새 ioctl은 기존 ioctl number 뒤에 append되어 compat UAPI 번호를 재정렬하지
  않는다.
- `QUERY_CAPS`도 `GET_FAULT` 뒤에 append했으며, 기존 fixed ioctl 번호와 APKO
  executable/submit/fault ioctl 번호를 바꾸지 않는다.
- `CONTEXT_CREATE/CONTEXT_DESTROY`도 `QUERY_CAPS` 뒤에 append했으며, 기존 UAPI
  번호를 바꾸지 않는다.
- `BO_CREATE/BO_DESTROY`도 `CONTEXT_DESTROY` 뒤에 append했으며, 기존 UAPI 번호를
  바꾸지 않는다.
- `WAIT`도 `BO_DESTROY` 뒤에 append했으며, 기존 UAPI 번호를 바꾸지 않는다.
- `BO_BIND/BO_UNBIND`도 `WAIT` 뒤에 append했으며, 기존 UAPI 번호를 바꾸지
  않는다.
- `GET_FAULT`도 append-only로 추가했으며, validation 실패가 hardware fault로
  오염되지 않는 `-ENODATA` path를 negative smoke로 확인한다.
- context create는 `size`, `flags`, `generic_abi_version`, reserved field를
  검증하고, per-file xarray handle을 반환한다. destroy는 stale handle을
  `-ENOENT`로 거부한다.
- BO create는 `size`, `flags`, output field, reserved field, zero size, DMA window
  초과를 검증하고, DRM GEM SHMEM object를 GEM handle로 publish한 뒤
  `mmap_offset`을 반환한다. destroy는 DRM GEM handle manager가 stale handle을
  `-EINVAL`로 거부한다.
- BO bind는 `size`, `flags`, context handle, BO handle, usage, offset/length
  alignment, BO bounds, output field, reserved field를 검증하고, context-owned
  binding handle과 staged IOVA를 반환한다. staged IOVA 산술은
  `check_add_overflow()`로 방어한다. unbind는 `size`, `flags`, reserved field와
  stale binding handle을 검증하고, stale handle은 `-ENOENT`로 거부한다.
- `Kconfig`는 `DRM_GEM_SHMEM_HELPER`를 `select`하도록 갱신했다. ARM64 build에서
  `DRM_GEM_SHMEM_HELPER`의 `MMU` dependency를 만족하도록 `depends on MMU`도
  추가했다. ARM64 build에서 `drivers/gpu/drm/drm_gem_shmem_helper.o`와
  `apollo-hexagon-bo.o` link reachability를 확인했다.
- submit 실패 fault record는 고정 `ERROR` 값 대신 `apollo_hexagon_wait_job()`이
  읽은 hardware final status/result를 `apollo_hexagon_ioctl_submit()`까지 전달해
  저장한다.
- `copy_from_user()`는 hardware lock 밖에서 수행하고, `copy_to_user()`도 hardware
  lock 해제 후 수행한다.
- per-file executable table은 file-private xarray와 mutex로 보호하고, submit은
  table entry를 lock 안에서 값 복사한 뒤 실행하므로 concurrent destroy로 인한
  use-after-free 경로를 만들지 않는다.
- MMIO/shared SRAM 접근은 기존 `test->lock` 범위 안에 남아 있고, APKO generic
  submit도 기존 CNN/VADD path와 같은 queue/result/fence programming 순서를 따른다.
- fixed CNN/VADD/DMA stress path는 `apollo-hexagon-compat.c`로 이동했지만,
  기존 ioctl number와 queue/fence/status marker는 보존했다.
- APKO executable table, validation, generic submit, fault retrieval은
  `apollo-hexagon-exec.c`의 file-private state로 격리했다.
- `WAIT`은 `apollo-hexagon-fence.c`로 분리했다. 현재 구현은 완료된 fence의
  `status`, `result`, `current_fence_seq` snapshot과 bounded timeout validation을
  제공한다. command ring 기반 async timeline wait는 아직 구현하지 않았다.
- `WAIT` 구현의 fence 비교 helper는 ARM64 build에서 Linux `current` macro와
  충돌한 parameter 이름을 `current_seq`로 바꿔 `apollo-hexagon-fence.o`
  빌드를 통과시켰다.
- `QUERY_CAPS`는 core file에서 DRM device capability를 읽고, 현재 지원하는 APKO
  VADD 2-packet CMDQ 크기를 `max_command_bytes=64`로 보고한다. VADD
  transitional path는 input/output BO 2개를 binding table에서 소비하므로
  `max_bindings_per_dispatch=2`를 보고한다. 이는 VADD copy shim의 capability이며,
  아직 arbitrary tensor BO hardware mapping이나 CNN/MNIST dispatch coverage를 뜻하지
  않는다.
- `CMD_SUBMIT`은 append-only UAPI로 추가했다. handler는 command BO handle,
  32-bit aligned offset, packet-aligned bounded command size, context handle,
  queue id, output field, reserved field를 검증하고,
  `drm_gem_object_lookup()`/`drm_gem_vmap()`으로 command buffer를 복사한 뒤
  `test->lock` 범위에서 CMDQ shared window와 doorbell register를 program한다.
- `CMD_SUBMIT`의 context lookup은 현재 existence gate다. handler가 context
  binding table을 아직 소비하지 않으므로 lock 해제 뒤 `ctx` pointer를 재사용하지
  않아 concurrent destroy로 인한 use-after-free를 만들지 않는다.
- `CMD_SUBMIT` failure path는 CMDQ status/fault/fence snapshot을 `GET_FAULT`
  record로 남긴다. `SIGNAL_FENCE` positive path는 APKO negative guest smoke에서
  status `DONE`, fault `NONE`, non-zero fence로 검증했다.
- 2026-05-20 invalid IOVA 리뷰 반영으로 `CMD_SUBMIT` failure path는 fault
  completion fence를 `CMDQ_FENCE_VALUE`에서 함께 snapshot한다. APKO negative
  smoke는 invalid IOVA `COPY` packet을 command BO로 제출하고,
  `CMDQ_FAULT_DMA_ERROR`를 `GET_FAULT` clear retrieval로 회수한다.
- 2026-05-20 lifetime 리뷰 반영으로 VADD `CMD_SUBMIT`은 `afile->lock`을 잡은 채
  QBox CMDQ completion을 기다리지 않는다. Binding metadata lookup과 input snapshot은
  file lock 안에서 끝내고, output BO는 `drm_gem_object_get()`으로 ref를 잡아
  wait/copy-back 이후 `apollo_hexagon_bound_vadd_put()`에서 release한다. output
  copy-back은 `drm_dev_enter()` lifetime 안에서 수행한다.
- `apollo_hexagon_dynamic_map()`, `apollo_hexagon_prepare_async_fence()`,
  `apollo_hexagon_wait_job()` helper는 같은 DRM driver object 내부에서만 공유되고,
  `Makefile` object list와 ARM64 build로 link reachability를 확인했다.
- prompt-driven review에서 `DRM_GEM_SHMEM_HELPER`의 `MMU` dependency 누락과
  `drm_gem_shmem_create()` 이후의 중복 mmap-offset 생성 위험을 확인했고 둘 다
  수정했다. 추가 BO bind review refresh에서는 BO_UNBIND size/flags validation
  누락과 staged IOVA overflow guard 보강점을 반영했다. 수정 후 재검토에서는
  추가 prompt-driven regression을 발견하지 못했다.

## 2026-05-20 invalid IOVA fault 리뷰 반영

- 구현:
  - Linux/guest UAPI mirror에 `APOLLO_HEXAGON_CMDQ_FAULT_EMPTY`,
    `APOLLO_HEXAGON_CMDQ_FAULT_DISABLED`,
    `APOLLO_HEXAGON_CMDQ_FAULT_UNSUPPORTED_PACKET`,
    `APOLLO_HEXAGON_CMDQ_FAULT_MALFORMED_PACKET`,
    `APOLLO_HEXAGON_CMDQ_FAULT_DMA_ERROR`를 append-only constant로 노출했다.
  - `apollo_hexagon_wait_cmdq()`가 error path에서도 `CMDQ_FENCE_VALUE`를 읽어
    `CMD_SUBMIT` output과 `GET_FAULT` record에 같은 fault fence를 남기게 했다.
  - `apollo_hexagon_apko_negative.c`는 source IOVA `0x20000000`을 사용하는
    32-byte `COPY` packet을 command BO에 기록해 QBox TBU translation fault를
    유도하고, `GET_FAULT|CLEAR`로 queue/status/result/fence record를 검증한다.
- 검증:
  - `git diff --check && git -C sources/linux diff --check && git -C sources/qbox diff --check`:
    PASS.
  - `bash -n scripts/*.sh`: PASS.
  - `PYTHONPYCACHEPREFIX=/tmp/qbox-pycache python3 -m py_compile scripts/qbox_pty_runner.py scripts/check_qbox_smmuv3_compliance.py scripts/check_iree_cnn_pipeline_readiness.py`:
    PASS.
  - `./scripts/check_buildroot_arm64_lane.sh`: PASS.
  - `python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . --json build/verification/iree-readiness-invalid-iova-review-2026-05-20.json`:
    PASS, `SUMMARY {"missing": 5, "pass": 58}`. Missing 5개는 기존 host
    `iree-import-onnx`, `iree-compile`, `iree-run-module`, Python `onnx`,
    Python `numpy` 부재다.
  - `./scripts/build_qbox_linux_arm64.sh`: PASS. `apollo-hexagon-exec.o`와
    `arch/arm64/boot/Image`를 재빌드했다.
  - `./scripts/build_apollo_hexagon_guest_tools.sh`: PASS.
  - `QBOX_IREE_VECTOR_ADD_SKIP_HOST_SMOKE=1 ./scripts/stage_iree_vector_add_guest_artifacts.sh`:
    PASS.
  - `QBOX_IREE_VECTOR_ADD_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/vector-add ./scripts/build_qbox_buildroot_arm64.sh`:
    PASS.
  - `./scripts/stage_buildroot_artifacts.sh`: PASS.
  - `QBOX_APKO_NEGATIVE_HEXAGON_GUEST_SMOKE_STAMP=20260520-invalid-iova-review ./scripts/run_iree_apko_negative_hexagon_qbox_guest_smoke.sh`:
    PASS, `PASS: QBox guest APKO negative ioctl coverage matched`.
- 증거 로그:
  - `build/verification/qbox-iree-apko-negative-hexagon-guest-20260520-invalid-iova-review.log`
  - `build/verification/qbox-iree-apko-negative-hexagon-guest-boot-20260520-invalid-iova-review.log`
  - key markers:
    - `APOLLO_SMMU_TBU: translation fault stream-id=0x1 read iova=0x20000000`
    - `APOLLO_HEXAGON_DMA: command queue fault code=5 addr=0x20000000 fence=2`
    - `PASS: command BO invalid IOVA fault ok queue=1 fence=2 status=0x2 result=0x5`

## 2026-05-20 VADD CMD_SUBMIT lifetime 리뷰 반영

- 구현:
  - `apollo_hexagon_prepare_bound_vadd()`는 `afile->lock` 안에서 binding table을
    조회하고 input BO 내용을 snapshot한 뒤 output GEM object ref만 유지한다.
  - `apollo_hexagon_ioctl_cmd_submit()`은 file lock을 해제한 뒤 `drm_dev_enter()`,
    `test->lock`, QBox CMDQ doorbell, completion wait를 수행한다.
  - VADD output copy-back은 shared SRAM 결과를 stack buffer로 읽은 뒤, retained
    output GEM object에 `apollo_hexagon_bo_copy_to()`로 반영한다.
  - cleanup은 `apollo_hexagon_bound_vadd_put()`으로 단일화해 success/error path에서
    output GEM ref를 균형 있게 drop한다.
- 검증:
  - `git diff --check`: PASS.
  - `git -C sources/linux diff --check`: PASS.
  - `bash -n scripts/*.sh`: PASS.
  - `PYTHONPYCACHEPREFIX=/tmp/qbox-pycache python3 -m py_compile scripts/qbox_pty_runner.py scripts/check_qbox_smmuv3_compliance.py scripts/check_iree_cnn_pipeline_readiness.py`:
    PASS.
  - `./scripts/build_qbox_linux_arm64.sh`: PASS. `apollo-hexagon-exec.o`,
    `drivers/accel/apollo_hexagon/built-in.a`, `vmlinux`, `arch/arm64/boot/Image`
    재빌드를 확인했다.
  - `./scripts/check_buildroot_arm64_lane.sh`: PASS.
  - `python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . --json build/verification/iree-readiness-bound-vadd-review-2026-05-20.json`:
    PASS, `SUMMARY {"missing": 5, "pass": 59}`. Missing 5개는 기존 host
    `iree-import-onnx`, `iree-compile`, `iree-run-module`, Python `onnx`,
    Python `numpy` 부재다.
  - `./scripts/build_apollo_hexagon_guest_tools.sh`: PASS.
  - `QBOX_IREE_VECTOR_ADD_SKIP_HOST_SMOKE=1 ./scripts/stage_iree_vector_add_guest_artifacts.sh`:
    PASS.
  - `QBOX_IREE_VECTOR_ADD_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/vector-add ./scripts/build_qbox_buildroot_arm64.sh`:
    PASS.
  - `./scripts/stage_buildroot_artifacts.sh`: PASS.
  - `QBOX_APKO_VADD_HEXAGON_GUEST_SMOKE_STAMP=20260520-bound-cmdsubmit-review ./scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh`:
    PASS, `PASS: QBox guest APKO VADD output matched`.
  - `QBOX_APKO_NEGATIVE_HEXAGON_GUEST_SMOKE_STAMP=20260520-bound-cmdsubmit-review ./scripts/run_iree_apko_negative_hexagon_qbox_guest_smoke.sh`:
    PASS, `PASS: QBox guest APKO negative ioctl coverage matched`.
- 증거 로그:
  - `build/verification/qbox-iree-apko-vadd-hexagon-guest-20260520-bound-cmdsubmit-review.log`
  - `build/verification/qbox-iree-apko-vadd-hexagon-guest-boot-20260520-bound-cmdsubmit-review.log`
  - `build/verification/qbox-iree-apko-negative-hexagon-guest-20260520-bound-cmdsubmit-review.log`
  - `build/verification/qbox-iree-apko-negative-hexagon-guest-boot-20260520-bound-cmdsubmit-review.log`
  - key markers:
    - `command BO bound VADD dispatch ctx=1 input=0x10300000 output=0x10301000 bytes=32/16`
    - `APOLLO_HEXAGON_DMA: command dispatch vadd input=0x10010000 output=0x10011000 bytes=0x20`
    - `command BO bound VADD output copied ctx=1 output=0x10301000 bytes=16`
    - `IREE Apollo Hexagon HAL: APKO CMD_SUBMIT VADD ok executable=1 ctx=1 cmd_bo=3 input_bind=1 output_bind=2 queue=1 fence=2 status=0x00000001 result=0x00000000`
    - `PASS: command BO invalid IOVA fault ok queue=1 fence=2 status=0x2 result=0x5`
    - `PASS: APKO negative ioctl coverage completed`

## 2026-05-20 LOAD_EXECUTABLE slot 리뷰 반영

- 구현:
  - UAPI mirror에 `APOLLO_HEXAGON_CMDQ_OPCODE_LOAD_EXECUTABLE`,
    `APOLLO_HEXAGON_CMDQ_DISPATCH_EXEC_SLOT_FLAG`,
    `APOLLO_HEXAGON_CMDQ_SUBMIT_MAX_BYTES`를 추가했다.
  - QBox `apollo_hexagon_dma` command queue는 `LOAD_EXECUTABLE` packet으로 APKO v0
    metadata를 executable slot에 저장하고, `DISPATCH(exec-slot)`이 해당 metadata를
    참조해 VADD를 실행한다.
  - Linux `CMD_SUBMIT`은 2-packet bounded command buffer를 fetch하고, valid
    `LOAD_EXECUTABLE` metadata를 scan한 뒤 VADD dispatch packet의 BO binding IOVA를
    shared SRAM IOVA로 patch한다.
  - APKO VADD UMD happy path는 command BO에
    `LOAD_EXECUTABLE -> DISPATCH(exec-slot)`을 기록한다.
- 검증:
  - `git diff --check`: PASS.
  - `git -C sources/linux diff --check`: PASS.
  - `git -C sources/qbox diff --check`: PASS.
  - `bash -n scripts/*.sh`: PASS.
  - `PYTHONPYCACHEPREFIX=/tmp/qbox-pycache python3 -m py_compile scripts/qbox_pty_runner.py scripts/check_qbox_smmuv3_compliance.py scripts/check_iree_cnn_pipeline_readiness.py`:
    PASS.
  - `./scripts/check_buildroot_arm64_lane.sh`: PASS. `LOAD_EXECUTABLE`,
    executable-slot dispatch flag, QBox executor, and component-test contract
    markers를 확인했다.
  - `./scripts/build_apollo_hexagon_guest_tools.sh`: PASS.
  - `./scripts/build_qbox_buildroot_platform.sh`: PASS. `apollo_hexagon_dma.so`
    재빌드를 확인했다.
  - `cmake --build sources/qbox/build --target apollo-hexagon-dma-tests && ctest --test-dir sources/qbox/build -R '^apollo-hexagon-dma-tests$' --output-on-failure`:
    PASS, 1/1 test passed.
  - `./scripts/build_qbox_linux_arm64.sh`: PASS. `apollo-hexagon-exec.o`와
    `arch/arm64/boot/Image`를 재빌드했다.
  - `python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . --json build/verification/iree-readiness-load-executable-2026-05-20.json`:
    PASS, `SUMMARY {"missing": 5, "pass": 59}`. Missing 5개는 기존 host
    `iree-import-onnx`, `iree-compile`, `iree-run-module`, Python `onnx`,
    Python `numpy` 부재다.
  - `QBOX_IREE_VECTOR_ADD_SKIP_HOST_SMOKE=1 ./scripts/stage_iree_vector_add_guest_artifacts.sh`:
    PASS.
  - `QBOX_IREE_VECTOR_ADD_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/vector-add ./scripts/build_qbox_buildroot_arm64.sh`:
    PASS.
  - `./scripts/stage_buildroot_artifacts.sh`: PASS.
  - `QBOX_APKO_VADD_HEXAGON_GUEST_SMOKE_STAMP=20260520-load-executable-rerun ./scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh`:
    PASS, `PASS: QBox guest APKO VADD output matched`.
  - `QBOX_APKO_NEGATIVE_HEXAGON_GUEST_SMOKE_STAMP=20260520-load-executable ./scripts/run_iree_apko_negative_hexagon_qbox_guest_smoke.sh`:
    PASS, `PASS: QBox guest APKO negative ioctl coverage matched`.
- 증거 로그:
  - `build/verification/qbox-iree-apko-vadd-hexagon-guest-20260520-load-executable-rerun.log`
  - `build/verification/qbox-iree-apko-vadd-hexagon-guest-boot-20260520-load-executable-rerun.log`
  - `build/verification/qbox-iree-apko-negative-hexagon-guest-20260520-load-executable.log`
  - `build/verification/qbox-iree-apko-negative-hexagon-guest-boot-20260520-load-executable.log`
  - key markers:
    - `command BO LOAD_EXECUTABLE slot=1 kind=2 input=32 output=16`
    - `APOLLO_HEXAGON_DMA: command load executable slot=1 kind=2 input-bytes=32 output-bytes=16 format=0x1`
    - `APOLLO_HEXAGON_DMA: command dispatch executable slot=1 kind=2`
    - `APOLLO_HEXAGON_DMA: command dispatch vadd input=0x10010000 output=0x10011000 bytes=0x20`
    - `IREE Apollo Hexagon HAL: APKO CMD_SUBMIT VADD ok executable=1 exec_slot=1`
    - `4xf32=11 22 33 44`
    - `PASS: command BO bad LOAD_EXECUTABLE fault ok`
    - `APOLLO_HEXAGON_DMA: command queue fault code=4`

## 2026-05-20 VMFB-embedded APKO transition slice

- 구현:
  - guest HAL loader가 metadata path 없이 module을 열 때 staged VMFB 끝의
    repo-local APKO footer를 검사하고 APKO v0 payload를 추출하도록 했다.
  - vector-add와 tiny-CNN staging script는 기존 `.vmfb.meta` sidecar를 유지하면서
    `vector_add_apollo.vmfb`, `tiny_cnn_apollo.vmfb` embedded APKO artifact도 만든다.
  - `run_vector_add_vmfb_apko_hexagon_guest.sh`와
    `run_iree_apko_vadd_vmfb_hexagon_qbox_guest_smoke.sh`는 `.vmfb.meta` sidecar 자동
    주입을 끄고 `executable_source=vmfb-embedded-apko` marker를 요구한다.
- 범위:
  - 이 slice는 VMFB 파일 안에 APKO payload를 담는 repo-local transition ABI다.
  - 아직 upstream IREE compiler target backend가 HAL executable section을 생성하는
    것은 아니므로, final VMFB packaging 완료로 과장하지 않는다.
- 리뷰 반영:
  - VMFB-embedded APKO loader는 APKO header의 `header_bytes`와 footer의 entry,
    input/output byte 계약을 함께 검증한다.
  - embedded APKO payload는 `apollo_hexagon_unload_executable()`에서 명시적으로
    해제하며, `apollo-iree-run-module`과 `apollo-iree-hexagon-runner`의 성공/실패
    exit path가 unload를 호출한다.
- 후속 검증 gate:
  - `./scripts/build_apollo_hexagon_guest_tools.sh`
  - `QBOX_IREE_VECTOR_ADD_SKIP_HOST_SMOKE=1 ./scripts/stage_iree_vector_add_guest_artifacts.sh`
  - `QBOX_IREE_VECTOR_ADD_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/vector-add ./scripts/build_qbox_buildroot_arm64.sh`
  - `QBOX_APKO_VADD_VMFB_HEXAGON_GUEST_SMOKE_STAMP=<stamp> ./scripts/run_iree_apko_vadd_vmfb_hexagon_qbox_guest_smoke.sh`
- 이번 리뷰 refresh 검증:
  - `git diff --check`: PASS
  - `bash -n scripts/*.sh`: PASS
  - `PYTHONPYCACHEPREFIX=/tmp/qbox-pycache python3 -m py_compile scripts/qbox_pty_runner.py scripts/check_qbox_smmuv3_compliance.py scripts/check_iree_cnn_pipeline_readiness.py`: PASS
  - `./scripts/check_buildroot_arm64_lane.sh`: PASS
  - `./scripts/build_apollo_hexagon_guest_tools.sh`: PASS
  - `QBOX_IREE_VECTOR_ADD_SKIP_HOST_SMOKE=1 ./scripts/stage_iree_vector_add_guest_artifacts.sh`: PASS,
    staged `build/iree-guest-artifacts/vector-add/vector_add_apollo.vmfb`
  - `QBOX_IREE_TINY_CNN_SKIP_HOST_SMOKE=1 ./scripts/stage_iree_tiny_cnn_guest_artifacts.sh`: PASS,
    staged `build/iree-guest-artifacts/tiny-cnn/tiny_cnn_apollo.vmfb`
  - `python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . --json build/verification/iree-readiness-vmfb-embedded-apko-review-2026-05-20.json`: PASS,
    `{"missing": 5, "pass": 61}`
  - VMFB trailer parse:
    - vector-add footer/header: magic `0x4f4b4156`/`0x4f4b5041`, APKO size 48,
      entry kind 2, input 32 bytes, output 16 bytes
    - tiny-CNN footer/header: magic `0x4f4b4156`/`0x4f4b5041`, APKO size 48,
      entry kind 1, input 64 bytes, output 16 bytes

## 남은 blocker

- Upstream IREE target backend가 VMFB HAL executable data에 APKO를 직접 포함하는
  packaging은 아직 미구현이다. 현재 구현은 staged VMFB trailer 기반 transition
  ABI다.
- APKO `LOAD_EXECUTABLE`은 metadata slot foundation이다. true code/payload loading은
  아직 미구현이다.
- Linux driver의 1차 core/bo/context/exec/compat split과 generic `QUERY_CAPS`,
  `CONTEXT_CREATE/DESTROY`, `BO_CREATE/DESTROY`, `BO_BIND/UNBIND`, `WAIT`,
  `CMD_SUBMIT`, invalid IOVA fault-producing `GET_FAULT` foundation은 완료됐다.
  남은 v2 재편 범위는 staged BO IOVA metadata를 실제 hardware/SMMU mapping에
  연결하고, command BO가 tensor BO binding table과 executable payload를 dispatch로
  소비하게 만들며, async timeline semaphore scheduling과 full fault reporting을
  완성하는 작업이다.
