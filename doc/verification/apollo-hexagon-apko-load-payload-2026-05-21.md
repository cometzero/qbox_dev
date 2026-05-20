# Apollo Hexagon APKO LOAD_PAYLOAD/LOAD_CODE 리뷰 반영 검증

## 요약

2026-05-21 리뷰 반영으로 APKO command queue 경로를
`LOAD_EXECUTABLE -> LOAD_PAYLOAD -> LOAD_CODE -> DISPATCH(exec-slot)`
4-packet 계약으로 갱신했다. 기존 QBox model은 `LOAD_EXECUTABLE.entry_kind`에서
payload opcode를 자동 생성했지만, 이제 APKO byte stream의 `PAYL` descriptor와
`CODE` descriptor를 UMD가 읽어 각각 `LOAD_PAYLOAD`, `LOAD_CODE` packet으로
명시 전달한다. executable-slot dispatch의 model-kernel 선택은
`LOAD_EXECUTABLE.entry_kind`가 아니라 검증된 `CODE` entry instruction decode 결과를
기준으로 한다.

이 리포트는 repo-local transition slice의 검증 결과다. full APKO code interpreter,
true hardware BO mapping, upstream IREE HAL executable packaging 완료 증거는 아니다.
2026-05-21 추가 진행으로 `CODE` 첫 word는 raw model kind가 아니라
`MODEL_DISPATCH | model-kind` 형식의 encoded entry instruction으로 갱신했다.

## 변경 범위

- `sources/linux/include/uapi/drm/apollo_hexagon_accel.h`
- `sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon-exec.c`
- `sources/qbox/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h`
- `sources/qbox/tests/components/apollo_hexagon_dma/apollo-hexagon-dma-tests.cc`
- `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/`
- `scripts/stage_iree_*guest_artifacts.sh`
- `scripts/run_iree_apko_*hexagon_qbox_guest_smoke.sh`
- `scripts/check_*`
- `doc/analysis/apollo-hexagon-dnn-kernel-*.md`

2026-05-21 추가 리뷰 반영으로 Buildroot `iree-runtime` 패키지도 갱신했다. 이제
source-built upstream `iree-run-module`은 `/usr/libexec/qbox/iree-run-module.real`에
보존하고, `/usr/bin/iree-run-module`은 local CPU 실행을 real runner로 전달하면서
`apollo-hexagon` query/dispatch를 repo-local `apollo-iree-run-module`과
`libapollo_iree_hexagon_hal_plugin.so`로 라우팅한다. 이 경로는 rootfs 기본 runtime
query evidence를 제공하지만, upstream IREE HAL driver 등록 완료 증거는 아니다.

## 실행한 검증

```bash
bash -n scripts/*.sh
PYTHONPYCACHEPREFIX=/tmp/qbox-pycache-load-code \
  python3 -m py_compile \
  scripts/check_apko_vmfb_verification_lane.py \
  scripts/check_iree_cnn_pipeline_readiness.py
make -C sources/linux O=/build/qbox_dev/build/linux-a710 ARCH=arm64 \
  CROSS_COMPILE=/build/qbox_dev/build/buildroot-a710/host/bin/aarch64-buildroot-linux-gnu- \
  M=drivers/accel/apollo_hexagon -j2 modules
cmake --build sources/qbox/build \
  --target apollo_hexagon_dma apollo-hexagon-dma-tests -j2
ctest --test-dir sources/qbox/build -R '^apollo-hexagon-dma-tests$' \
  --output-on-failure
./scripts/build_apollo_hexagon_guest_tools.sh
python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . \
  --json build/verification/iree-readiness-load-code-check.json
python3 scripts/check_apko_vmfb_verification_lane.py --repo . \
  --json build/verification/apko-vmfb-load-code-check.json
./scripts/check_buildroot_arm64_lane.sh
python3 scripts/check_qbox_smmuv3_compliance.py --repo . \
  --json build/verification/smmuv3-load-code-check.json
QBOX_IREE_VECTOR_ADD_SKIP_HOST_SMOKE=1 \
  ./scripts/stage_iree_vector_add_guest_artifacts.sh
QBOX_IREE_TINY_CNN_SKIP_HOST_SMOKE=1 \
  ./scripts/stage_iree_tiny_cnn_guest_artifacts.sh
QBOX_IREE_MNIST_SKIP_HOST_SMOKE=1 \
  ./scripts/stage_iree_mnist_guest_artifacts.sh
QBOX_BUILDROOT_JOBS=2 ./scripts/build_iree_runtime_buildroot.sh
QBOX_BUILDROOT_JOBS=2 \
QBOX_IREE_VECTOR_ADD_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/vector-add \
QBOX_IREE_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/tiny-cnn \
QBOX_IREE_MNIST_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/mnist \
  ./scripts/build_qbox_buildroot_arm64.sh
./scripts/build_qbox_linux_arm64.sh
./scripts/stage_buildroot_artifacts.sh
QBOX_BOOT_TIMEOUT=80 \
QBOX_APKO_VADD_HEXAGON_GUEST_SMOKE_STAMP=20260521-044848 \
  ./scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh
QBOX_BOOT_TIMEOUT=55 QBOX_BOOT_LOG=build/verification/qbox-iree-runtime-wrapper-query-boot-20260521-045030.log \
  ./scripts/run_qbox_buildroot_boot.sh
od -An -t u4 -j 80 -N 4 \
  build/iree-guest-artifacts/vector-add/vector_add.apko
od -An -t u4 -j 80 -N 4 \
  build/iree-guest-artifacts/tiny-cnn/tiny_cnn.apko
od -An -t u4 -j 80 -N 4 \
  build/iree-guest-artifacts/mnist/mnist.apko
git diff --check
git -C sources/linux diff --check
git -C sources/qbox diff --check
```

## 결과

- Shell syntax: PASS
- Python compile: PASS
- Linux Apollo Hexagon module build: PASS
- QBox `apollo_hexagon_dma` and `apollo-hexagon-dma-tests` build: PASS
- QBox component test `apollo-hexagon-dma-tests`: PASS, 1/1
- Apollo Hexagon guest tools cross/host build: PASS
- IREE readiness checker: PASS 70
- APKO VMFB lane checker: PASS 15
- Buildroot ARM64 lane contract checker: PASS
- SMMUv3 compliance checker: PASS 1063
- VADD/CNN/MNIST APKO staging: PASS
- Buildroot `iree-runtime` package rebuild: PASS. Target rootfs contains
  `/usr/bin/iree-run-module` wrapper,
  `/usr/libexec/qbox/iree-run-module.real`,
  `/usr/bin/apollo-iree-run-module`,
  `/usr/lib/qbox/libapollo_iree_hexagon_hal_plugin.so`.
- Buildroot rootfs rebuild with VADD/CNN/MNIST guest artifacts: PASS
- Standalone Linux Image rebuild: PASS. The staged kernel reports
  `Linux version 7.0.0-13912-gdb85e4ae4196 ... #67 SMP PREEMPT Thu May 21 04:48:15 KST 2026`.
- QBox artifact staging: PASS
- `/usr/bin/iree-run-module` wrapper guest query: PASS.
  - log: `build/verification/qbox-iree-runtime-wrapper-query-20260521-045030.log`
  - markers: `apollo-hexagon (Apollo QBox repo-local C HAL registry frontend)`,
    `device[0]=apollo-hexagon://0`,
    `dynamically registered C HAL plugin=/usr/lib/qbox/libapollo_iree_hexagon_hal_plugin.so`,
    `upstream_hal_driver=not-linked`
- QBox guest APKO VADD smoke: PASS.
  - log: `build/verification/qbox-iree-apko-vadd-hexagon-guest-20260521-044848.log`
  - boot log: `build/verification/qbox-iree-apko-vadd-hexagon-guest-boot-20260521-044848.log`
  - markers: `max_command_bytes=128`, `command BO LOAD_PAYLOAD slot=1 opcode=2`,
    `command BO LOAD_CODE slot=1 offset=0 words=2 entry_word=65538 end_word=131072`,
    `APOLLO_HEXAGON_DMA: command load code slot=1 offset=0 words=2 entry=65538 end=131072`,
    `IREE Apollo Hexagon HAL: APKO CMD_SUBMIT VADD ok`, `4xf32=11 22 33 44`
- staged APKO code programs: VADD `65538, 131072`, CNN `65537, 131072`,
  MNIST `65539, 131072`. `131072` is `APKO_CODE_OP_END`.
- diff whitespace checks: PASS

## 재검증 중 확인한 artifact skew

- 첫 APKO VADD smoke
  `build/verification/qbox-iree-apko-vadd-hexagon-guest-20260521-044414.log`는
  결과 tensor 자체는 `4xf32=11 22 33 44`였지만 smoke marker에서 실패했다. 당시
  guest query가 `max_command_bytes=64`를 보고해 최신 4-packet command BO 경로가
  아니라 legacy executable submit fallback으로 실행되었기 때문이다.
- 원인은 rootfs는 갱신했지만 staged Linux Image가 이전 `#66` build였던 artifact
  skew였다. `./scripts/build_qbox_linux_arm64.sh`와
  `./scripts/stage_buildroot_artifacts.sh`를 다시 실행한 뒤 `#67` Image에서
  `max_command_bytes=128`과 `LOAD_PAYLOAD/LOAD_CODE` command BO marker가 모두
  확인되었다.

## 확인된 새 계약

- `LOAD_EXECUTABLE`만으로 executable-slot dispatch를 실행할 수 없다.
- `LOAD_PAYLOAD`는 `PAYL` magic, version, descriptor word count, payload opcode,
  `CODE` word count를 검증하고, entry offset은 0으로 고정한다.
- `LOAD_CODE`는 `CODE` magic/version, word offset/count, encoded entry instruction을
  검증하며 payload opcode와 entry model kind가 다르면 malformed fault로 거부한다.
- Linux driver와 QBox model은 `LOAD_CODE`가 성공한 slot만 executable-slot dispatch로
  허용하고, dispatch kind는 `CODE` entry instruction의
  `MODEL_DISPATCH | model-kind` encoding에서 decode한다.
- QBox component test가 missing payload와 bad payload opcode를 malformed fault로
  확인한다.
- QBox component test가 `LOAD_PAYLOAD`의 missing code words를 malformed fault로
  확인한다.
- QBox component test가 `LOAD_CODE` 없는 executable-slot dispatch와 payload opcode /
  code entry mismatch를 malformed fault로 확인한다.
- guest HAL은 APKO payload/code descriptor를 읽은 뒤 command BO에
  `LOAD_PAYLOAD`와 `LOAD_CODE`를 추가한다.
- guest HAL은 `PAYL` descriptor가 없는 기존 48-byte APKO v0 artifact는 legacy
  submit path로 fallback한다. descriptor가 존재하지만 내용이 잘못된 경우는 오류로
  처리한다.
- VADD, CNN, MNIST staging artifact는 APKO header 뒤에 `PAYL` descriptor,
  `CODE` descriptor, 2-word transition code payload를 포함한다. 첫 instruction은
  `MODEL_DISPATCH | model-kind`, 두 번째 instruction은 `APKO_CODE_OP_END`이다.
- guest HAL, Linux driver, QBox model은 `APOLLO_HEXAGON_APKO_CODE_OP_MODEL_DISPATCH`
  opcode와 low 16-bit model kind를 decode하고 `APKO_CODE_OP_END` terminator까지
  확인한 뒤에만 executable-slot dispatch를 허용한다.

## 남은 작업

- APKO `CODE` section은 현재 2-word mini program까지 검증한다. 다음 단계는 이를
  실제 Hexagon code blob/interpreter 또는 executable BO/code DMA 입력으로 연결하는 것이다.
- Linux driver copy shim을 true BO/SMMU/TBU page mapping으로 바꾼다.
- VMFB trailer transition ABI를 upstream IREE HAL executable packaging으로 교체한다.
