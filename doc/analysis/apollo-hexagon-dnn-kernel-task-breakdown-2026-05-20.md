# Apollo Hexagon DNN 커널 실행 태스크 분해

날짜: 2026-05-20
작업공간: `/build/qbox_dev`
기준 plan:
`doc/analysis/apollo-hexagon-dnn-kernel-execution-plan-2026-05-18.md`

## 목표

최종 목표는 다음 실행 경로를 실제 검증 가능한 형태로 완성하는 것이다.

```text
iree compile -> VMFB -> IREE runtime -> Apollo Hexagon UMD
  -> Apollo Hexagon driver -> Apollo Hexagon hardware
```

현재 구현은 APKO v0 sidecar/VMFB trailer, executable handle, generic submit,
`GET_FAULT`, `QUERY_CAPS`, generic context, GEM SHMEM BO lifecycle, BO binding
metadata foundation, 64-byte command BO `CMD_SUBMIT`, 그리고 VADD/CNN/MNIST
`LOAD_EXECUTABLE -> DISPATCH(exec-slot)` smoke 준비, MNIST-shaped
`ONNX -> MLIR -> host/AArch64 VMFB` compile evidence까지 진행된 상태다. 그러나
아직 DNN kernel 실행 구조의 최종 상태는 아니다. 남은 핵심은 BO binding을 실제
hardware/SMMU mapping에 연결하고, full APKO code/payload interpreter와 upstream
IREE VMFB HAL executable packaging을 완성하는 것이다.

## 계획 리뷰 반영 요약

이번 리뷰 반영은 새 코드를 추가하기 전에 실행 계획을 더 엄격하게 만드는
것이다. 특히 현재 구현된 foundation과 최종 목표를 섞어 표현하지 않도록
구분하고, 기존 device driver 전면 재개편을 독립 태스크로 쪼갠다.

- 현재 상태와 목표 상태를 분리한다. `CMD_SUBMIT`, `BO_BIND`, `WAIT`,
  `GET_FAULT`는 foundation으로 완료됐고 VADD/CNN은 binding table과 VMFB 내부
  APKO trailer를 통해 CMDQ dispatch로 검증됐다. 2026-05-21 추가 리뷰 반영으로
  MNIST APKO kind도 Linux/UMD `CMD_SUBMIT` 경계에 연결했고 host ONNX smoke와
  Apollo payload의 deterministic Flatten+Gemm 출력 계약을 맞췄다. true hardware BO
  mapping, full APKO payload execution, upstream IREE packaging은 아직 완료가 아니다.
- fixed CNN/VADD ioctl은 계속 compatibility shim으로만 취급한다. 새 driver
  core의 중심 경로는 context, BO, executable, command BO submit, wait/fence,
  fault record, SMMU-visible binding이다.
- `$team` 생성은 tmux leader session에서만 정상으로 간주한다. 현재 Codex App
  shell은 `$TMUX`가 비어 있으므로 이 문서는 team launch command와 작업자
  배치를 제공하되, 실제 team 생성 완료로 주장하지 않는다.
- 정적 검사와 smoke test는 사용자의 지시에 맞춰 모든 수정 정리 이후에 수행한다.
  아래 검증 명령은 즉시 실행 증거가 아니라 후속 실행 gate다.
- 각 lane은 "선행 조건", "작업", "완료 기준", "검증"을 갖는 실행 태스크로
  유지한다. 구현 중에는 lane별 소유 파일을 섞지 않고, kernel 변경 시
  `kernel-review`를 별도 수행한다.

## 현재 완료 상태

- Linux driver는 `apollo-hexagon.c` core와 `apollo-hexagon-context.c`,
  `apollo-hexagon-bo.c`, `apollo-hexagon-exec.c`,
  `apollo-hexagon-fence.c`, `apollo-hexagon-compat.c`로 1차 분리되어 있다.
- UAPI는 append-only로 다음 generic foundation을 갖는다.
  - `QUERY_CAPS`
  - `CONTEXT_CREATE`
  - `CONTEXT_DESTROY`
  - `BO_CREATE`
  - `BO_DESTROY`
  - `BO_BIND`
  - `BO_UNBIND`
  - `CMD_SUBMIT`
  - `EXEC_CREATE`
  - `EXEC_DESTROY`
  - `SUBMIT`
  - `WAIT`
  - `GET_FAULT`
- `QUERY_CAPS`는 이제 APKO command queue 2-packet buffer 크기인
  `max_command_bytes=64`를 반환한다. VADD/CNN `CMD_SUBMIT` path가 input/output
  BO binding 2개를 소비하는 transitional copy shim을 갖게 되어
  `max_bindings_per_dispatch=2`를 반환한다. 이는 아직 실제 Apollo TBU/SMMU page
  mapping 완료를 뜻하지 않는다.
- APKO VADD/CNN sidecar guest smoke, VADD/CNN VMFB-embedded APKO guest smoke,
  APKO negative ioctl smoke는 통과한다.
- MNIST APKO sidecar guest smoke는 staging/smoke/checker 계약이 추가됐고,
  정적 검사와 smoke 실행은 전체 수정 정리 이후 수행한다.
- BO negative smoke는 zero-size reject, BO create/destroy, stale BO handle
  reject를 검증한다.
- BO bind negative smoke는 bad bind size, invalid context, invalid BO handle,
  unaligned length, bad unbind size, bind/unbind, stale bind handle reject를
  검증한다.
- WAIT negative/positive smoke는 bad size, zero fence, bad queue, completed
  fence wait, future fence timeout을 검증한다.
- command BO submit foundation은 `CMD_SUBMIT` ioctl, guest UAPI mirror, negative
  smoke helper까지 추가됐다. 현재 범위는 GEM SHMEM command BO에서 32-byte command
  packet을 fetch해 QBox CMDQ doorbell로 실행하고 CMDQ status/fence metadata를
  반환하는 단계이며, invalid IOVA COPY packet으로 만든 CMDQ DMA fault를
  `GET_FAULT`로 회수하는 positive path도 포함한다. 추가 진행으로 VADD/CNN
  `DISPATCH` packet의 staged input/output IOVA는 context binding table을 조회해
  input BO를 shared SRAM으로 복사하고, completion 후 output BO로 결과를 되돌리는
  transitional binding-table 소비 path를 갖는다. APKO VADD/CNN command BO는
  `LOAD_EXECUTABLE -> DISPATCH(exec-slot)` 2-packet buffer를 제출한다.
- QBox SMMU는 functional integration slice로 검증 중이며, bit-exact Arm SMMUv3
  구현이라고 주장하지 않는다.

## 남은 작업 요약

1. 완료: Linux driver v2 UAPI를 command BO submit foundation까지 확장했다.
2. 완료/부분: VADD/CNN `CMD_SUBMIT`은 binding table을 소비하는 transitional copy shim을
   갖는다. 남은 작업은 Apollo TBU/SMMU-visible IOVA binding metadata를 실제
   hardware mapping과 per-context address-space ownership으로 확장하는 것이다.
3. 완료: QBox Apollo Hexagon DMA/firmware path를 byte-count fixed dispatcher에서 command
   packet parser로 전환한다.
4. 부분 완료: APKO v0 metadata와 binding table을 VADD/CNN/MNIST command packet으로
   실행한다. MNIST-shaped ONNX compile artifact와 Apollo MNIST dispatch는 같은
   deterministic `Flatten+Gemm(zero weights, bias 0..9)` graph semantics로 맞춘다.
   남은 작업은 full APKO code/payload interpreter와 upstream IREE HAL executable
   backend packaging이다.
5. 부분 완료: Apollo IREE HAL UMD가 staged VMFB 안의 repo-local APKO trailer를
   읽어 driver v2로 submit할 수 있다. 남은 작업은 upstream IREE HAL executable
   section으로 APKO를 packaging하는 것이다.
6. 완료/부분: Buildroot rootfs staging과 smoke는 VMFB-driven APKO VADD/CNN과
   MNIST APKO sidecar/VMFB-trailer 계약까지 전환했다. upstream IREE HAL executable
   packaging은 후속 작업이다.
7. 완료: invalid IOVA fault-producing `GET_FAULT` positive path를
   negative/diagnostic coverage에 추가했다. unsupported ONNX op coverage는 남아
   있다.

## 작업 레인 1: Linux Driver v2 Resource Model

소유 파일:

- `sources/linux/include/uapi/drm/apollo_hexagon_accel.h`
- `sources/linux/drivers/accel/apollo_hexagon/`
- `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_hexagon_uapi_guest.h`

작업:

- 완료: `BO_BIND/BO_UNBIND` equivalent UAPI를 append-only로 추가했다.
- 완료: context별 binding xarray를 만들고 BO handle을 staged
  IOVA/usage/offset/length metadata와 연결한다. bind는 output/reserved field와
  staged IOVA overflow를 검증하고, unbind는 size/flags도 검증한다.
- 부분 완료: VADD/CNN `CMD_SUBMIT` path는 staged IOVA를 context binding table에서
  조회해 input/output BO를 소비한다. 남음: staged IOVA metadata를 실제 GEM
  page/SMMU/TBU mapping으로 연결한다.
- 추가 리뷰 반영: `CMD_SUBMIT`은 더 이상 file-level `afile->lock`을 잡은 채
  QBox CMDQ completion을 기다리지 않는다. Binding table은 lock 안에서 짧게
  해석하고, output BO는 `drm_gem_object_get()`으로 ref를 잡아 wait 이후
  output copy-back까지 lifetime을 보장한다.
- 완료: command BO submit UAPI를 append-only로 추가했다. 기존 `SUBMIT`의 userspace
  `input_ptr/output_ptr` 경로는 transitional APKO smoke용으로 유지하되, 새 path는
  context handle, command BO handle, command offset/size, queue id만 받는다. 첫
  구현은 GEM SHMEM command BO를 vmap해 32-byte packet을 shared CMDQ window에
  적재하고 CMDQ doorbell/fence/status를 검증한다.
- 완료: `WAIT` foundation을 추가해 submit return path와 completion wait path를
  분리하기 시작했다. 아직 command ring 기반 async timeline semaphore는 아니다.
- `QUERY_CAPS.max_command_bytes`는 `CMD_SUBMIT`/APKO VADD CMDQ smoke가
  `LOAD_EXECUTABLE -> DISPATCH(exec-slot)` 2-packet buffer를 사용하므로 64로
  올렸다. VADD command BO submit이 input/output BO binding 2개를 소비하므로
  `max_bindings_per_dispatch=2`를 반환한다. 단, 현재는 QBox shared SRAM copy shim이며
  true hardware BO page mapping은 남아 있다.

세부 태스크:

| ID | 태스크 | 선행 조건 | 완료 기준 |
| --- | --- | --- | --- |
| L1-1 | 완료: context binding table을 command submit에서 조회하는 helper 추가 | `BO_BIND/UNBIND`, `CMD_SUBMIT` foundation | VADD/CNN command packet의 staged IOVA가 bind table entry와 매칭된다. |
| L1-2 | 부분 완료: GEM SHMEM BO와 Apollo TBU/SMMU-visible IOVA 연결 | L1-1 | `max_bindings_per_dispatch=2`는 transitional copy shim evidence로만 올렸다. 실제 page mapping은 남아 있다. |
| L1-3 | 완료: command BO가 tensor BO input/output을 소비하는 VADD/CNN path | L1-1, L1-2 | UMD가 userspace pointer `SUBMIT` 없이 BO create/bind/CMD_SUBMIT만으로 VADD/CNN output BO를 읽는다. |
| L1-4 | 부분 완료: executable metadata를 command submit과 연결 | `EXEC_CREATE`, L1-3 | `LOAD_EXECUTABLE` metadata slot이 command queue dispatch의 검증 입력으로 사용된다. 실제 code/payload loading은 남아 있다. |
| L1-5 | submit/fault/iommu file split 정리 | L1-1 이후 | `apollo-hexagon-exec.c`가 과도하게 커지지 않고 submit, fault, iommu 책임이 분리된다. |

완료 기준:

- invalid context, invalid BO, overflow binding, unknown flag, non-zero
  reserved field가 모두 `-EINVAL`, `-ENOENT`, `-ENOSPC` 중 명확한 errno로
  거부된다. 현재 metadata allocator는 monotonic IOVA를 직접 배정하므로
  userspace-specified overlapping IOVA case는 아직 없다.
- file close에서 context/executable/BO binding lifetime이 정리된다.
- `CMD_SUBMIT` 중 concurrent BO unbind/context destroy가 들어와도 command wait는
  file-level lock을 장시간 점유하지 않고, 이미 잡은 output GEM ref로 copy-back
  lifetime을 보장한다.
- 기존 fixed CNN/VADD/DMA stress ioctl 번호와 동작이 유지된다.

검증:

```bash
./scripts/build_qbox_linux_arm64.sh
./scripts/check_buildroot_arm64_lane.sh
python3 scripts/check_qbox_smmuv3_compliance.py --repo .
QBOX_APKO_NEGATIVE_HEXAGON_GUEST_SMOKE_STAMP=<stamp> \
  ./scripts/run_iree_apko_negative_hexagon_qbox_guest_smoke.sh
git diff --check && git -C sources/linux diff --check
```

주의:

- kernel code 변경 후 `kernel-review` skill로 DRM, mm, uaccess, locking, kconfig
  관점의 regression review를 수행해야 한다.

## 작업 레인 2: QBox Command Queue and Firmware Contract

소유 파일:

- `sources/qbox/systemc-components/apollo_hexagon_dma/`
- `sources/qbox/platforms/buildroot/fw/`
- `sources/qbox/tests/components/apollo_hexagon_dma/`
- `scripts/build_qbox_hexagon_firmware.sh`
- `scripts/build_qbox_buildroot_platform.sh`

작업:

- command queue register를 추가한다.
  - `CMDQ_BASE_LO/HI`
  - `CMDQ_SIZE`
  - `CMDQ_HEAD`
  - `CMDQ_TAIL`
  - `DOORBELL`
  - `COMPLETION/FENCE_VALUE`
  - `FAULT_CODE`
  - `FAULT_ADDR_LO/HI`
- command packet을 최소 subset부터 구현한다.
  - `NOP`
  - `LOAD_EXECUTABLE`
  - `DISPATCH`
  - `COPY`
  - `BARRIER`
  - `SIGNAL_FENCE`
- APKO VADD를 첫 generic dispatch로 연결하고, 기존 byte-count VADD/CNN
  dispatcher는 compatibility path로 격리한다.
- invalid command packet과 invalid IOVA가 fault register/completion record에
  남도록 한다.

완료 기준:

- QBox component test가 command queue tail/head, doorbell, completion, invalid packet
  fault를 검증한다.
- guest APKO VADD smoke가 fixed byte-count branch 없이 command packet path marker를
  출력한다.

2026-05-20 리뷰 반영 상태:

- `apollo_hexagon_dma` component에 `CMDQ_BASE_LO/HI`, `CMDQ_SIZE`,
  `CMDQ_HEAD`, `CMDQ_TAIL`, `CMDQ_DOORBELL`, `CMDQ_STATUS`,
  `CMDQ_FENCE_VALUE`, `CMDQ_FAULT_CODE`, `CMDQ_FAULT_ADDR_LO/HI` register
  foundation을 추가했다.
- doorbell write는 이제 선형 non-wrapping command queue에서 32-byte packet을
  fetch/decode한다. `NOP`, `COPY`, `BARRIER`, `SIGNAL_FENCE`는 실행되고, 성공 시
  head가 tail까지 전진한 뒤 기존 async IRQ/fence path로 completion evidence를
  만든다.
- 빈 queue는 `CMDQ_FAULT_EMPTY`, 해석하지 못하는 packet은
  `CMDQ_FAULT_UNSUPPORTED_PACKET`, malformed packet/queue geometry와 DMA/TLM
  실패는 별도 fault로 남긴다. base+offset address overflow guard도 추가했다.
- `CMDQ_OPCODE_DISPATCH`와 `CMDQ_DISPATCH_KIND_VADD`를 추가해 APKO VADD
  smoke의 현재 입력 계약과 같은 8개 `u32` 입력을 읽고 4개 `f32` bit pattern
  출력으로 쓰는 첫 generic dispatch packet을 QBox component 안에서 실행한다.
  malformed byte count와 dispatch DMA/TLM fault도 command queue fault register로
  남긴다.
- QBox component test가 empty queue fault, unsupported packet fault,
  malformed queue geometry, COPY packet DMA fault, `NOP/COPY/BARRIER/SIGNAL_FENCE`
  성공 실행, `DISPATCH/VADD` 성공 실행, `DISPATCH/VADD` DMA fault와 completion을
  검증한다.
- Linux driver의 APKO VADD generic submit은 이제 shared SRAM에 32-byte
  `DISPATCH/VADD` packet을 쓰고 `CMDQ_BASE/HEAD/TAIL/DOORBELL` register를
  program한다. 기존 APKO CNN과 fixed CNN/VADD ioctl은 compatibility path로 남겨
  회귀 범위를 줄였다.
- Linux driver의 command BO submit foundation도 추가됐다. `CMD_SUBMIT`은
  userspace pointer 대신 GEM SHMEM command BO handle과 offset/size를 받아
  32-byte packet을 fetch하고, QBox CMDQ doorbell 완료 후 CMDQ status/result/fence를
  반환한다. APKO negative smoke helper는 `SIGNAL_FENCE` packet으로 이 경로를
  검증한다.
- 추가 리뷰 반영으로 APKO negative smoke helper는 invalid IOVA를 source로 둔
  `COPY` packet을 command BO로 제출하고, `CMDQ_FAULT_DMA_ERROR`를
  `GET_FAULT` clear retrieval로 회수한다.
- 추가 진행으로 `LOAD_EXECUTABLE`은 APKO v0 metadata를 QBox executable slot에
  적재하고, executable-slot `DISPATCH/VADD`, `DISPATCH/CNN`, `DISPATCH/MNIST`가
  그 metadata를 참조한다. 아직 true APKO code/payload loading과 true MNIST ONNX
  compile/runtime semantics는 다음 slice로 남아 있다.
- VMFB-embedded APKO transition slice 리뷰 반영으로 embedded APKO footer/header
  ABI 검증과 UMD-side executable unload path를 추가했다. 이 작업은 staged VMFB
  trailer를 안전하게 소비하는 중간 단계이며, upstream IREE VMFB HAL executable
  packaging 완료로 간주하지 않는다.

2026-05-21 리뷰 반영 상태:

- Linux driver `CMD_SUBMIT` scanner는 VADD뿐 아니라 CNN `LOAD_EXECUTABLE` metadata와
  executable-slot dispatch를 인식한다. input/output BO binding을 shared SRAM window로
  patch한 뒤 QBox CMDQ doorbell을 울리고, completion 후 output BO로 결과를 복사한다.
- QBox DMA 모델의 executable-slot CNN dispatch는 tiny-CNN canonical output
  `1x1x2x2xf32=[[[54 63][90 99]]]`을 반환한다. 이 당시에는 MNIST-like direct
  dispatch stub만 있었고 Linux/UMD binding은 아직 연결하지 않았다.
- sidecar APKO CNN smoke와 VMFB-embedded APKO CNN smoke가 모두 fixed `SUBMIT_CNN`
  compatibility path가 아니라 `APKO CMD_SUBMIT CNN ok` marker로 통과했다.

2026-05-21 추가 리뷰 반영 상태:

- kernel/guest UAPI에 `APOLLO_HEXAGON_EXEC_KIND_MNIST`와 MNIST 28x28-f32 input,
  10-f32 output geometry를 추가했다.
- Linux driver `CMD_SUBMIT` scanner와 APKO header validator가 MNIST entry kind를
  인식하고, UMD가 `mnist_graph` metadata를 `EXEC_CREATE -> CMD_SUBMIT ->
  EXEC_DESTROY`로 실행한다.
- `stage_iree_mnist_guest_artifacts.sh`와
  `run_iree_apko_mnist_hexagon_qbox_guest_smoke.sh`는 host ONNX smoke와 같은
  `1x10xf32=[0 1 2 3 4 5 6 7 8 9]` output을 검증한다. 이는 DNN kernel ABI 연결과
  deterministic graph semantics match를 증명하지만 trained MNIST accuracy는 아니다.

2026-05-21 계속 진행 상태:

- `run_iree_mnist_host_smoke.sh`는 MNIST-shaped `Flatten+Gemm` ONNX graph를 만들고
  `iree-import-onnx`, `iree-compile`로 host VMFB와 AArch64 VMFB를 생성한 뒤
  `iree-run-module --device=local-task`에서 `1x10xf32=[0 1 2 3 4 5 6 7 8 9]`
  reference를 검증한다.
- `stage_iree_mnist_guest_artifacts.sh`는 더 이상 빈 stub VMFB를 base module로
  쓰지 않고, 위 AArch64 VMFB에 repo-local APKO trailer를 붙여
  `mnist_apollo.vmfb`를 만든다.
- Apollo APKO MNIST payload semantics는 host ONNX smoke와 동일하게
  `Flatten+Gemm(zero weights, bias 0..9)` contract를 대표한다.
  `semantic_match=host-onnx-and-apollo-payload-produce-1x10xf32-bias-output`로
  staging metadata에 남긴다. 단, 이것은 아직 full APKO code interpreter나 trained
  MNIST accuracy 완료를 뜻하지 않는다.

세부 태스크:

| ID | 태스크 | 선행 조건 | 완료 기준 |
| --- | --- | --- | --- |
| L2-1 | 완료: `LOAD_EXECUTABLE` packet ABI 정의 | APKO v0 header/payload 결정 | QBox component test가 valid/invalid executable load를 구분한다. |
| L2-2 | 완료/부분: executable slot을 `DISPATCH`와 연결 | L2-1 | VADD/CNN/MNIST `DISPATCH` packet이 fixed kind만 보지 않고 loaded executable metadata를 참조한다. |
| L2-3 | tensor binding 기반 DMA fetch/store | L1-2 | QBox DMA가 staged shared SRAM 상수 주소가 아니라 binding-derived IOVA를 사용한다. |
| L2-4 | 부분 완료: CNN/MNIST 최소 op subset command dispatch | L2-2, L2-3 | APKO CNN과 MNIST smoke가 fixed byte-count dispatcher 없이 CMDQ path로 통과하도록 계약화됐다. MNIST는 deterministic Flatten+Gemm semantics까지 host/Apollo 계약을 맞췄다. |

검증:

```bash
./scripts/build_qbox_buildroot_platform.sh
./scripts/build_qbox_hexagon_firmware.sh
QBOX_APKO_VADD_HEXAGON_GUEST_SMOKE_STAMP=<stamp> \
  ./scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh
```

## 작업 레인 3: Apollo IREE HAL UMD and VMFB Bridge

소유 파일:

- `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/`
- `configs/buildroot/external/apollo_qbox/package/iree-runtime/`
- `scripts/build_iree_runtime_buildroot.sh`
- `scripts/stage_iree_tiny_cnn_guest_artifacts.sh`
- `scripts/stage_iree_vector_add_guest_artifacts.sh`
- `sources/iree` integration files if needed

작업:

- 현재 repo-local runner/plugin path를 IREE HAL driver 형태로 정리한다.
- VMFB executable data에서 APKO payload와 entry metadata를 읽는 loader contract를
  정의한다.
- HAL allocator는 driver BO create/bind path를 사용하도록 전환한다.
- command buffer record/submit은 command BO와 binding table을 만들고 driver submit
  v2로 내려간다.
- Buildroot rootfs에 runtime library, HAL plugin, sample VMFB/APKO artifacts를
  일관된 layout으로 staging한다.

세부 태스크:

| ID | 태스크 | 선행 조건 | 완료 기준 |
| --- | --- | --- | --- |
| L3-1 | repo-local plugin/runner ABI와 실제 IREE HAL driver 경계 정리 | 현재 guest-tools HAL shim | `--list_drivers`와 repo-local wrapper가 서로 다른 증거로 분리된다. |
| L3-2 | 완료: HAL allocator를 BO create/bind 기반으로 전환 | L1-1 또는 transitional shim | APKO VADD/CNN input/output이 userspace pointer가 아니라 mapped BO로 전달된다. |
| L3-3 | 완료: command buffer record/submit을 command BO 기반으로 전환 | L1-3 | APKO VADD/CNN UMD가 `DRM_IOCTL_APOLLO_HEXAGON_CMD_SUBMIT`을 happy path에서 사용한다. |
| L3-4 | 부분 완료: VMFB executable data에서 APKO payload 추출 | IREE compile artifact policy | staged VMFB 뒤에 repo-local APKO trailer를 붙이고 `.vmfb.meta` 없이 loader가 APKO를 찾는다. upstream IREE HAL executable section packaging은 남아 있다. |
| L3-4a | 완료: Buildroot runtime wrapper에 Apollo repo-local frontend 포함 | L3-1 | rootfs의 `/usr/bin/iree-run-module`은 local CPU 실행을 source-built real runner로 넘기고, `apollo-hexagon` query/dispatch는 repo-local registry frontend와 dynamic HAL plugin으로 넘긴다. |
| L3-5 | upstream IREE external HAL build/staging | L3-1, L3-4 | Buildroot rootfs의 `iree-run-module --device=apollo-hexagon://0`가 device query와 VADD run을 통과한다. |

완료 기준:

- guest에서 `iree-run-module --list_drivers`가 `apollo-hexagon`을 보여준다.
- guest에서 `iree-run-module --dump_devices --device=apollo-hexagon://0`가 repo-local
  registry frontend와 dynamic HAL plugin query 결과를 출력한다. 이 증거는 wrapper
  경로임을 marker로 남겨 upstream IREE HAL driver 완료로 과장하지 않는다.
- VADD/CNN VMFB smoke가 APKO sidecar metadata가 아니라 VMFB executable data 기반으로
  Apollo path를 선택한다.
  2026-05-20 추가 slice는 `vector_add_apollo.vmfb`/`tiny_cnn_apollo.vmfb`에
  repo-local APKO trailer를 붙이고 `--metadata=`로 sidecar 자동 주입을 끈 상태에서
  `executable_source=vmfb-embedded-apko` marker를 출력하도록 했다. 2026-05-21
  리뷰 반영으로 CNN VMFB smoke도 같은 marker와 `APKO CMD_SUBMIT CNN ok`를
  요구한다. 이는 최종
  upstream VMFB HAL executable packaging의 전 단계이며, 아직 IREE compiler backend가
  APKO section을 생성하는 것은 아니다.

검증:

```bash
./scripts/build_iree_runtime_buildroot.sh
./scripts/build_apollo_hexagon_guest_tools.sh
QBOX_IREE_VECTOR_ADD_SKIP_HOST_SMOKE=1 \
  ./scripts/stage_iree_vector_add_guest_artifacts.sh
build/buildroot-a710/target/usr/bin/iree-run-module --list_drivers
build/buildroot-a710/target/usr/bin/iree-run-module --dump_devices \
  --device=apollo-hexagon://0
```

## 작업 레인 4: Contracts, Negative Tests, and Evidence

소유 파일:

- `scripts/check_buildroot_arm64_lane.sh`
- `scripts/check_iree_cnn_pipeline_readiness.py`
- `scripts/run_iree_apko_*_hexagon_qbox_guest_smoke.sh`
- `doc/verification/`
- `build/verification/`

작업:

- fixed compatibility checks와 generic v2 checks를 계속 분리한다.
- 새 UAPI가 추가될 때마다 guest UAPI mirror, negative smoke, readiness checker를
  같이 갱신한다.
- unsupported ONNX op smoke를 추가하되, compiler 미설치 상태에서는 명확한
  `blocked_missing_tool` 분류를 사용한다.
- 완료: invalid IOVA fault-producing submit을 만들어 `GET_FAULT` positive
  retrieval을 검증하도록 추가했다.
- 날짜가 들어간 verification report를 갱신한다.

세부 태스크:

| ID | 태스크 | 선행 조건 | 완료 기준 |
| --- | --- | --- | --- |
| L4-1 | compat/generic marker 분리 유지 | 모든 lane | checker가 fixed ioctl pass와 generic v2 pass를 별도 항목으로 출력한다. |
| L4-2 | unsupported ONNX op negative 분류 | IREE compiler tool 존재 또는 missing-tool gate | tool 미설치면 `blocked_missing_tool`, 설치 후에는 compile-time reject evidence를 남긴다. |
| L4-5 | MNIST-shaped ONNX compile artifact 증거 | host IREE/ONNX tool 또는 venv install 가능 | `run_iree_mnist_host_smoke.sh`가 ONNX, MLIR, host VMFB, AArch64 VMFB, host run report를 생성하고 stage script가 그 VMFB를 APKO trailer base로 사용한다. |
| L4-3 | 완료: BO binding/CMD_SUBMIT happy path smoke 추가 | L1-3, L3-3 | APKO VADD/CNN smoke log가 BO bind, command BO submit, output BO copy marker를 요구한다. |
| L4-4 | 완료: VMFB-embedded APKO smoke 추가 | L3-4 | VADD/CNN smoke가 sidecar artifact 없이 VMFB path를 사용했음을 로그로 증명한다. |

2026-05-20 추가 slice:

- `run_iree_apko_vadd_vmfb_hexagon_qbox_guest_smoke.sh`를 추가했다.
- smoke는 `/opt/qbox/iree/vector-add/run_vector_add_vmfb_apko_hexagon_guest.sh`를
  호출하고, `executable_source=vmfb-embedded-apko`와 기존 VADD
  `LOAD_EXECUTABLE -> DISPATCH(exec-slot)` marker를 요구한다.

2026-05-21 리뷰 반영:

- `run_iree_apko_cnn_vmfb_hexagon_qbox_guest_smoke.sh`를 추가했다.
- 기존 `run_iree_apko_cnn_hexagon_qbox_guest_smoke.sh`도 `APKO CMD_SUBMIT CNN ok`,
  `command dispatch executable slot=1 kind=1`, `command dispatch cnn` marker를
  요구하도록 갱신했다.
- readiness checker는 host venv 기준 PASS 67로 갱신됐고, 당시 남은 blocker는 true
  hardware BO mapping, full APKO code execution, MNIST Linux/UMD CMDQ binding,
  upstream VMFB HAL executable backend packaging으로 좁혔다.

2026-05-21 추가 리뷰 반영:

- readiness/check_buildroot/APKO-VMFB checker가 MNIST APKO staging과 smoke
  계약을 추적한다.
- 남은 blocker 표현은 MNIST Linux/UMD binding이 아니라 full APKO interpreter와
  upstream IREE packaging으로 좁힌다.

2026-05-21 계속 진행:

- readiness/check_buildroot/APKO-VMFB checker가 MNIST-shaped ONNX host compile
  script와 `mnist_aarch64.vmfb` staging 계약을 추적한다.
- 남은 blocker 표현은 "ONNX compile artifact 없음"이 아니라 "Apollo payload가
  아직 host ONNX graph semantics를 실행하지 않음"으로 더 좁힌다.

완료 기준:

- `check_buildroot_arm64_lane.sh`가 fixed path와 generic path를 별도 marker로
  보고한다.
- readiness checker는 host tool missing과 driver/runtime 미구현을 구분한다.
- smoke log는 command packet path, BO binding, fence wait, fault retrieval marker를
  포함한다.

검증:

```bash
git diff --check && git -C sources/linux diff --check
bash -n scripts/*.sh
PYTHONPYCACHEPREFIX=/tmp/qbox-pycache python3 -m py_compile \
  scripts/qbox_pty_runner.py \
  scripts/check_qbox_smmuv3_compliance.py \
  scripts/check_iree_cnn_pipeline_readiness.py
./scripts/check_buildroot_arm64_lane.sh
python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . \
  --json build/verification/iree-readiness.json
```

## 권장 Team 시작

tmux leader 안에서 다음 형태로 시작한다.

```bash
omx team 4:executor "Apollo Hexagon DNN generic execution을 완료한다. 기준 문서는 doc/analysis/apollo-hexagon-dnn-kernel-execution-plan-2026-05-18.md 와 doc/analysis/apollo-hexagon-dnn-kernel-task-breakdown-2026-05-20.md 이다. 현재 context/BO/executable/generic submit/WAIT foundation은 구현되어 있고, 남은 작업은 Linux driver v2 BO binding/command submit, QBox command queue/APKO payload semantics, Apollo IREE HAL UMD/VMFB bridge, contract/negative/evidence lane이다. 고정 CNN/VADD compatibility smoke는 유지하고, kernel 변경은 kernel-review 후 검증한다."
```

권장 작업자 배치:

- 작업자 1: Linux driver v2 resource model.
- 작업자 2: QBox command queue and firmware contract.
- 작업자 3: Apollo IREE HAL UMD and VMFB bridge.
- 작업자 4: contracts, negative tests, evidence.

리뷰 반영 후 team 시작 성공 판정:

- `omx team status <team-name>`가 leader와 4개 작업자 pane을 보여준다.
- 각 작업자가 위 lane 중 하나만 claim한다.
- 작업자별 첫 update에 소유 파일, 첫 태스크 ID, 검증 계획이 남는다.
- tmux 밖에서 hook에 의해 차단된 `omx team` 시도는 team 생성으로 보지 않는다.

## 현재 Team 실행 상태

2026-05-20 현재 이 문서는 `continue-apollo-hexag-e808b943` 팀의 live worker
검토 결과를 반영한다. 작업 기준은 repository root `b07b60ce348a`,
`sources/linux` gitlink `7f510a9e2872`, `sources/qbox` gitlink
`b8875d31a71f`이다. 현재 worker-3 worktree에서는 `git submodule status`가
`sources/linux`, `sources/qbox` 등 source submodule 앞에 `-`를 표시하므로
submodule working tree는 아직 checkout되지 않았다. 따라서 source 내부 line-level
code review와 build/smoke 재검증은 submodule init/update 이후 수행해야 하며,
이번 worker-3 범위는 top-level docs/scripts/config evidence 기반의 lane assignment와
contract review로 제한한다.

현재 task 상태와 lane 배치는 다음과 같다. lane은 충돌을 줄이기 위해 소유 파일
범위가 겹치지 않도록 잡는다.

| Team task | Worker | Primary lane | 소유/초점 | 완료 증거 |
| --- | --- | --- | --- | --- |
| task-1 `Implement` | worker-1 | Lane 1 + Lane 3 boundary | Linux driver v2 resource model과 UAPI를 구현한다. `sources/linux/**` 및 Linux UAPI가 주 범위이며, guest-tools/stage script는 worker-3 범위로 분리한다. | Linux build, UAPI 정합성, fixed compat smoke 보존. |
| task-2 `Test` | worker-2 | Lane 4 verification | checker/smoke/readiness를 실행하고 missing tool 또는 uninitialized submodule은 `blocked_missing_prerequisite`로 분류한다. `build/verification/` 로그와 `doc/verification/` report가 주 범위다. | `git diff --check`, shell syntax/py_compile, `check_buildroot_arm64_lane.sh`, APKO positive/negative smoke 결과. |
| task-3 `Review and document` | worker-3 | Lane 3 UMD/IREE + docs | `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/**`, `scripts/stage_iree_*guest_artifacts.sh`, `doc/analysis/**`에서 VMFB-embedded APKO load/unload와 generic submit bridge를 정리한다. Linux/QBox model file은 수정하지 않는다. | guest-tools/stage script build 또는 syntax evidence, 문서 diff, subagent review evidence, lifecycle result. |
| task-4 `Additional work` | worker-4 | Lane 2 QBox command queue | `apollo_hexagon_dma` command queue/APKO payload semantics와 firmware contract를 worker-1 Linux/UMD 변경과 맞춘다. `sources/qbox/`와 firmware/component tests가 주 범위다. | QBox component build/test, firmware/platform build, APKO command queue smoke markers. |

Cross-lane contract gates:

- worker-1과 worker-4는 `LOAD_EXECUTABLE -> DISPATCH(exec-slot)` packet ABI,
  fence/status/fault code layout, and `max_command_bytes` 값을 동시에 변경하지 않는다.
  ABI 변경이 필요하면 worker-3이 guest-tools/stage script 계약을 갱신하고,
  worker-2가 negative smoke를 추가한다.
- 2026-05-21 리뷰 반영 후 command ABI는
  `LOAD_EXECUTABLE -> LOAD_PAYLOAD -> LOAD_CODE -> DISPATCH(exec-slot)` 4-packet 계약이다.
  `LOAD_EXECUTABLE`은 executable slot과 tensor geometry만 로드하고,
  APKO payload opcode는 APKO 파일의 `PAYL` descriptor를 UMD가 읽어
  `LOAD_PAYLOAD` packet으로 명시적으로 전달한다. APKO code entry instruction은
  `CODE` descriptor를 UMD가 읽어 `LOAD_CODE` packet으로 별도 전달한다.
  2026-05-21 추가 리뷰 반영 후 `CODE` payload는 1-word marker가 아니라
  `MODEL_DISPATCH | model-kind`, `APKO_CODE_OP_END`의 2-word mini program으로
  검증한다. Linux validator, guest UMD, QBox DMA model은 entry와 end instruction이
  모두 맞는 경우에만 executable-slot dispatch를 허용한다. QBox는 `LOAD_PAYLOAD`,
  `LOAD_CODE`, 또는 `APKO_CODE_OP_END`가 없는 executable-slot dispatch를 malformed
  packet으로 처리해야 한다.
- worker-2는 fixed compatibility path와 generic v2 path를 반드시 별도 PASS/FAIL로
  기록한다. `SUBMIT_CNN`/`SUBMIT_VADD` marker가 generic smoke 성공 근거로 섞이면
  regression으로 본다.
- worker-3 review는 QBox SMMUv3를 functional integration slice로만 표현한다.
  bit-exact Arm SMMUv3 compliance 또는 upstream IREE HAL 통합 완료로 과장하지 않는다.
- source submodule이 uninitialized인 worker worktree에서는 code-quality verdict를
  최종 PASS로 쓰지 않는다. `git submodule update --init sources/linux sources/qbox`
  또는 leader root의 initialized checkout evidence가 있어야 source-level review/build가
  유효하다.

## 완료 판정

이 goal은 다음 증거가 모두 있어야 완료로 볼 수 있다.

- VMFB-driven VADD smoke가 Apollo Hexagon hardware path에서 통과한다.
- CNN 또는 MNIST smoke가 VMFB-driven APKO dispatch로 통과한다.
- MNIST의 경우 host-side `ONNX -> MLIR -> VMFB` compile artifact와 Apollo APKO
  payload semantics가 같은 graph를 대표한다는 증거가 있어야 한다. 2026-05-21
  추가 구현은 이를 `Flatten+Gemm(zero weights, bias 0..9)` smoke로 맞추지만,
  완료 판정에는 QBox guest smoke와 checker evidence가 함께 필요하다.
- driver v2는 context, BO binding, executable, command submit, wait/fence,
  fault retrieval을 모두 제공한다.
- QBox command queue path가 fixed byte-count dispatcher 없이 generic dispatch를
  수행한다.
- IREE runtime의 `apollo-hexagon` device path가 guest에서 query와 run을 모두
  통과한다.
- fixed compatibility path는 유지되거나, 동일 범위의 generic smoke로 대체된 뒤
  명시적으로 축소된다.
- 정적 검사, Linux build, Buildroot/rootfs staging, QBox guest smoke, readiness
  report, SMMUv3 compliance check가 최신 로그로 남아 있다.

## 2026-05-21 리뷰 반영 결과

이번 반영은 full APKO interpreter나 upstream IREE HAL executable packaging 완료가
아니라, 기존 entry-kind 기반 자동 payload 선택을 제거하는 중간 단계다.

- Linux/guest UAPI의 `APOLLO_HEXAGON_CMDQ_SUBMIT_MAX_PACKETS`를 4로 늘리고
  `APOLLO_HEXAGON_CMDQ_OPCODE_LOAD_PAYLOAD`, `APOLLO_HEXAGON_CMDQ_OPCODE_LOAD_CODE`,
  APKO `PAYL`/`CODE` descriptor 상수를 추가했다.
- Linux driver `CMD_SUBMIT` scanner는 valid `LOAD_PAYLOAD`와 `LOAD_CODE`를 모두 본
  경우에만 executable-slot dispatch를 BO binding copy shim 대상으로 인정한다.
- QBox `apollo_hexagon_dma`는 `LOAD_EXECUTABLE`에서 payload opcode를 더 이상
  자동 생성하지 않는다. `LOAD_PAYLOAD` 또는 `LOAD_CODE`가 없거나 payload opcode와
  code entry kind가 맞지 않으면 malformed fault를 낸다.
- guest HAL은 staged APKO/VMFB-embedded APKO에서 `PAYL`/`CODE` descriptor를 읽고,
  `LOAD_EXECUTABLE -> LOAD_PAYLOAD -> LOAD_CODE -> DISPATCH(exec-slot)` command BO를
  제출한다.
  descriptor가 없는 기존 APKO v0 artifact는 ABI 호환을 위해 legacy submit path로
  fallback하고, descriptor가 존재하지만 malformed이면 오류로 처리한다.
- VADD, CNN, MNIST staging script는 48-byte APKO header 뒤에 16-byte `PAYL`
  descriptor를 붙였고, 이어지는 추가 slice에서 `CODE` descriptor와 최소 code word를
  붙이도록 확장했다.
- negative coverage는 bad `LOAD_PAYLOAD`, bad `LOAD_CODE`,
  executable-slot-without-payload, executable-slot-without-code component test를
  추가했다.

## 2026-05-21 APKO CODE descriptor 진행 결과

이번 반영은 full APKO interpreter 완료가 아니라, APKO byte stream에 code section
존재를 강제하고 command packet에 code metadata를 싣는 중간 ABI다.

- Linux/guest UAPI와 QBox model에 `APOLLO_HEXAGON_APKO_CODE_MAGIC`,
  `APOLLO_HEXAGON_APKO_CODE_VERSION`, `APOLLO_HEXAGON_APKO_CODE_DESCRIPTOR_WORDS`
  상수를 추가했다.
- VADD, CNN, MNIST staging script는 APKO header 뒤에 `PAYL` descriptor,
  `CODE` descriptor, 최소 1-word code payload를 붙인다. 현재 code word는
  `MODEL_DISPATCH | payload-kind` 형태의 transition instruction이며, 실제 Hexagon
  instruction stream은 아니다.
- guest HAL은 `PAYL`만 있는 artifact를 malformed로 보고, `CODE` word count와
  첫 code word의 `MODEL_DISPATCH` opcode 및 payload kind field가 맞을 때만
  `LOAD_PAYLOAD`와 `LOAD_CODE`를 제출한다.
- Linux driver와 QBox command queue는 `LOAD_PAYLOAD` packet의 code word count와
  `LOAD_CODE` packet의 encoded entry instruction을 검증한다. QBox component test는
  missing code words와 missing `LOAD_CODE`를 malformed fault로 확인한다.
- 추가 진행으로 Linux driver와 QBox model은 executable-slot dispatch kind를
  `LOAD_EXECUTABLE.entry_kind`에서 자동 선택하지 않고, 검증된 `CODE` entry
  instruction을 decode해 실행 선택 기준으로 사용한다. QBox component test는 bad
  code entry를 별도 malformed `LOAD_CODE` fault로 확인한다.

남은 gap은 그대로 유지한다.

- APKO payload는 이제 최소 code section 계약을 갖지만, 아직 실제 Hexagon code
  blob/interpreter가 아니라 opcode word 기반 transition program이다.
- command BO input/output은 여전히 Linux driver의 QBox shared-window copy shim을
  거친다. true hardware BO/SMMU/TBU page mapping은 별도 작업이다.
- VMFB trailer는 repo-local transition ABI다. upstream IREE HAL executable section
  packaging 완료로 주장하지 않는다.
