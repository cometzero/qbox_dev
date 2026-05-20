# Apollo Hexagon APKO LOAD_PAYLOAD 리뷰 반영 검증

## 요약

2026-05-21 리뷰 반영으로 APKO command queue 경로를
`LOAD_EXECUTABLE -> LOAD_PAYLOAD -> DISPATCH(exec-slot)` 3-packet 계약으로
갱신했다. 기존 QBox model은 `LOAD_EXECUTABLE.entry_kind`에서 payload opcode를
자동 생성했지만, 이제 APKO byte stream의 `PAYL` descriptor와 `CODE` descriptor를
UMD가 읽어 `LOAD_PAYLOAD` packet으로 명시 전달한다. 추가 진행으로
executable-slot dispatch의 model-kernel 선택은 `LOAD_EXECUTABLE.entry_kind`가 아니라
검증된 `CODE` entry instruction decode 결과를 기준으로 한다.

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

## 실행한 검증

```bash
bash -n scripts/*.sh
PYTHONPYCACHEPREFIX=/tmp/qbox-pycache-apko-entry \
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
  --json build/verification/iree-readiness-code-instr-check.json
python3 scripts/check_apko_vmfb_verification_lane.py --repo . \
  --json build/verification/apko-vmfb-code-instr-check.json
./scripts/check_buildroot_arm64_lane.sh
QBOX_IREE_VECTOR_ADD_SKIP_HOST_SMOKE=1 \
  ./scripts/stage_iree_vector_add_guest_artifacts.sh
QBOX_IREE_TINY_CNN_SKIP_HOST_SMOKE=1 \
  ./scripts/stage_iree_tiny_cnn_guest_artifacts.sh
QBOX_IREE_MNIST_SKIP_HOST_SMOKE=1 \
  ./scripts/stage_iree_mnist_guest_artifacts.sh
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
- VADD/CNN/MNIST APKO staging: PASS
- staged APKO code-entry words: VADD `65538`, CNN `65537`, MNIST `65539`
- diff whitespace checks: PASS

## 확인된 새 계약

- `LOAD_EXECUTABLE`만으로 executable-slot dispatch를 실행할 수 없다.
- `LOAD_PAYLOAD`는 `PAYL` magic, version, descriptor word count, payload opcode,
  `CODE` word count, encoded entry instruction을 검증한다.
- Linux driver와 QBox model은 executable-slot dispatch kind를
  `CODE` entry instruction의 `MODEL_DISPATCH | model-kind` encoding에서 decode한다.
- QBox component test가 missing payload와 bad payload opcode를 malformed fault로
  확인한다.
- QBox component test가 `LOAD_PAYLOAD`의 missing code words를 malformed fault로
  확인한다.
- QBox component test가 payload opcode와 code entry mismatch를 malformed fault로
  확인한다.
- guest HAL은 APKO payload/code descriptor를 읽은 뒤 command BO에
  `LOAD_PAYLOAD`를 추가한다.
- guest HAL은 `PAYL` descriptor가 없는 기존 48-byte APKO v0 artifact는 legacy
  submit path로 fallback한다. descriptor가 존재하지만 내용이 잘못된 경우는 오류로
  처리한다.
- VADD, CNN, MNIST staging artifact는 APKO header 뒤에 `PAYL` descriptor,
  `CODE` descriptor, 최소 1-word transition code payload를 포함한다. 해당 code word는
  `MODEL_DISPATCH | model-kind` 형식이다.
- guest HAL, Linux driver, QBox model은 `APOLLO_HEXAGON_APKO_CODE_OP_MODEL_DISPATCH`
  opcode와 low 16-bit model kind를 decode한 뒤에만 executable-slot dispatch를
  허용한다.

## 남은 작업

- APKO `CODE` section을 실제 Hexagon code blob/interpreter 또는 executable BO/code
  DMA 입력으로 연결한다.
- Linux driver copy shim을 true BO/SMMU/TBU page mapping으로 바꾼다.
- VMFB trailer transition ABI를 upstream IREE HAL executable packaging으로 교체한다.
