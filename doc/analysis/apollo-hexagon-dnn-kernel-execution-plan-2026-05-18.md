# Apollo Hexagon DNN Kernel 실행 구조 개선안

날짜: 2026-05-18
작업공간: `/build/qbox_dev`
상태: 설계/전환 계획. 이 문서는 코드 구현을 포함하지 않는다.

## 결론

현재 Apollo Hexagon 경로는 `CNN`, `VADD`, `DMA_STRESS`를 직접 실행하는
고정 smoke path이다. 이 구조로는 `ONNX -> IREE compile -> VMFB -> IREE
runtime`에서 생성된 DNN kernel binary를 일반적으로 실행할 수 없다.

개선 방향은 다음과 같다.

```text
ONNX model
  -> iree-import-onnx
  -> iree-compile
  -> VMFB
  -> IREE runtime
  -> Apollo Hexagon IREE HAL UMD
  -> Apollo Hexagon DRM accel driver v2
  -> QBox Apollo Hexagon command queue
  -> Apollo Hexagon firmware/hardware
```

핵심 원칙은 `VMFB`와 graph 의미를 kernel driver로 밀어 넣지 않는 것이다.
`VMFB`는 IREE runtime/UMD 영역에 남기고, Linux driver는 device resource,
buffer, IOVA, executable handle, command submission, fence, fault reporting만
담당해야 한다.

기존 driver도 부분 확장이 아니라 전면 재개편 대상으로 둔다. 현재 fixed
job ioctl path는 새 driver core 위의 일시적 compatibility shim으로만 남기고,
새 기능은 모두 generic executable/dispatch ABI로만 추가한다.

## 현재 구현 근거

현재 구현은 SMMU, DMA, IRQ, queue를 확인하는 functional slice로는 의미가
있지만, DNN kernel binary 실행 구조는 아니다.

1. Userspace tool/UMD shim이 graph 이름에 고정되어 있다.
   - `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_run_module.c:36`
     는 `tiny_cnn_graph|vector_add_graph`만 사용법으로 제시한다.
   - `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_run_module.c:240`
     이후는 `vector_add_graph`와 tiny-CNN fallback으로 분기한다.
   - `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hexagon_hal.c:67`
     은 metadata를 읽지만 기본값이 `tiny_cnn_aarch64.vmfb`,
     `tiny_cnn_graph`, 고정 expected output이다.
   - `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hexagon_hal.c:259`
     와 `:287`은 fixed CNN/VADD ioctl을 호출한다.

2. Linux UAPI와 driver가 fixed job 구조다.
   - `sources/linux/include/uapi/drm/apollo_hexagon_accel.h:8`은 fixed tensor
     크기를 define한다.
   - `sources/linux/include/uapi/drm/apollo_hexagon_accel.h:25`와 `:34`는
     fixed CNN/VADD job struct를 정의한다.
   - `sources/linux/include/uapi/drm/apollo_hexagon_accel.h:55`는 `QUERY`,
     `SUBMIT_CNN`, `SUBMIT_VADD`, `DMA_STRESS`만 노출한다.
   - `sources/linux/drivers/accel/apollo_hexagon/apollo-hexagon.c:460`와
     `:518`은 CNN/VADD input/output byte size, queue, result code를 직접
     program한다.

3. QBox Hexagon firmware도 byte count로 job을 선택한다.
   - `sources/qbox/platforms/buildroot/fw/hexagon_dma_smoke.s:47`에서 fixed
     job loop가 시작된다.
   - `sources/qbox/platforms/buildroot/fw/hexagon_dma_smoke.s:59`는 `32/16`
     byte request를 VADD로 해석한다.
   - `sources/qbox/platforms/buildroot/fw/hexagon_dma_smoke.s:64`는 `64/16`
     byte request를 CNN으로 해석한다.
   - `sources/qbox/platforms/buildroot/fw/hexagon_dma_smoke.s:276`은 그 외
     equal-size request를 DMA copy로 처리한다.

따라서 현재 `VMFB`와 `.vmfb.meta`는 device executable의 source가 아니라
sidecar evidence에 가깝다.

## IREE 구조 검토

IREE의 구조상 Apollo는 `iree-run-module`을 흉내 내는 wrapper가 아니라 실제
HAL runtime driver/device로 붙어야 한다.

확인한 공식 문서 기준:

- ONNX는 `iree-import-onnx`를 통해 IREE로 들어오고, `iree-compile` 후
  runtime tool이 HAL device를 선택해 실행한다.
  https://iree.dev/guides/ml-frameworks/onnx/
- VMFB는 serialized VM bytecode module이며, runtime은 HAL module과 VMFB
  bytecode module을 VM context에 함께 올린다.
  https://iree.dev/developers/design-docs/vm/
- IREE deployment는 compiler target backend와 runtime HAL driver를 분리하며,
  out-of-tree HAL driver는 `IREE_EXTERNAL_HAL_DRIVERS`로 구성할 수 있다.
  https://iree.dev/guides/deployment-configurations/
- HAL dialect는 executable, buffer, semaphore, command buffer, dispatch의
  추상화를 제공한다.
  https://iree.dev/reference/mlir-dialects/HAL/
- HIP/Metal HAL driver 설계 문서는 device API 위의 얇은 HAL driver, allocator,
  command buffer, executable cache, synchronization object 구조를 보여준다.
  https://iree.dev/developers/design-docs/hip-hal-driver/
  https://iree.dev/developers/design-docs/metal-hal-driver/

현재 local IREE checkout 근거:

- `sources/iree/runtime/src/iree/tooling/context_util.c:35`는 `--module`로
  VMFB bytecode module을 load한다.
- `sources/iree/runtime/src/iree/tooling/context_util.c:713`은 HAL dependency
  module을 자동으로 load한다.
- `sources/iree/runtime/src/iree/hal/executable_cache.h:74`는 executable
  format, executable data, queue affinity, constants를 포함한 executable
  preparation parameter를 정의한다.
- `sources/iree/runtime/src/iree/hal/command_buffer.h:962`는 3D workgroup
  grid, constants, bindings를 받는 generic dispatch를 정의한다.
- `sources/iree/runtime/src/iree/hal/device.h:596`은 queue-ordered allocation,
  execution, deallocation을 HAL device 동작으로 모델링한다.

## 목표 구조

```text
Host build side
===============

model.onnx
  -> iree-import-onnx --opset-version 17 -o model.mlir
  -> iree-compile model.mlir
       --iree-hal-target-device=apollo-hexagon
       --iree-hal-target-backends=apollo-hexagon
       -o model_apollo.vmfb

Guest runtime side
==================

iree-run-module --module=model_apollo.vmfb --device=apollo-hexagon://0
  -> IREE VM bytecode module
  -> IREE HAL module
  -> apollo-hexagon HAL driver
       - allocator: Apollo/SMMU visible buffers
       - executable cache: Apollo kernel container loader
       - command buffer: copy, fill, dispatch, barrier
       - queue execute: DRM accel generic submit
       - semaphore/fence: IRQ-backed completion
  -> /dev/accel/accelN
  -> apollo_hexagon DRM accel driver v2
       - context, BO, IOVA, executable, submit, wait, fault
  -> QBox Apollo Hexagon command queue
  -> Apollo kernel object runs on firmware/hardware
```

## 책임 분리

| 계층 | 담당 | 담당하지 말아야 할 것 |
| --- | --- | --- |
| IREE importer/compiler | ONNX import, graph lowering, dispatch 형성, target executable packaging | Linux device lifetime, QBox register programming |
| VMFB | VM program, HAL executable metadata, host/device scheduling | raw kernel ioctl ABI |
| Apollo IREE HAL UMD | IREE `driver/device/allocator/executable_cache/command_buffer/queue` 구현 | ONNX parsing, firmware policy |
| Apollo DRM accel driver v2 | context, BO/GEM, IOVA, executable handle, generic submit, fence, fault reporting | VMFB parsing, graph compile, model-specific math |
| QBox firmware/hardware | command queue 해석, code/data DMA, kernel launch, completion IRQ | IREE VM semantics |

## Compiler와 Executable Format

Apollo target backend은 IREE HAL executable 안에 Apollo executable payload를
넣어야 한다. 초기 format은 versioned container로 둔다.

```text
executable_format = "apollo-hexagon-apko-v0"
file extension     = .apko
```

`APKO`는 Apollo Kernel Object container이다. 장기적으로는 little-endian
Hexagon ELF64 또는 그에 가까운 object form이 가장 바람직하다. 그러나 현재
QBox Apollo runtime에는 per-dispatch object loader ABI가 없다.
`sources/qbox/systemc-components/common/include/loader.h:215`에는 boot-time
`elf_file`, `bin_file` loading helper가 있지만, 이것은 device runtime dispatch
ABI가 아니다.

따라서 APKO v0는 다음 단계적 구조로 시작한다.

```text
magic/version
target_arch = apollo-hexagon-qbox
abi_version
entry_count
entry table:
  name
  ordinal
  code_offset/code_size
  workgroup_size[3]
  binding_count
  constant_count
  local_memory_bytes
  required_caps
code/data blobs
relocation records, optional in v0
debug/provenance notes, optional
```

IREE HAL executable은 APKO를 opaque executable data로 보관한다. Runtime에서
Apollo executable cache가 APKO header와 ABI version을 검증하고, driver의
executable handle을 만든 뒤 export ordinal로 dispatch한다.

`.vmfb.meta`는 staging/provenance artifact로만 유지한다. device ABI로 사용하지
않는다.

## Apollo IREE HAL UMD 재구성

현재 guest shim은 `iree-run-module` 일부 option을 직접 parsing하고 fixed ioctl을
호출한다. 최종 구조에서는 real IREE HAL driver 이름을 `apollo-hexagon`으로
등록한다.

필수 UMD object:

- `iree_hal_driver_t`: `/dev/accel/accel*` enumerate, `apollo-hexagon://0`
  또는 explicit path로 device 생성.
- `iree_hal_device_t`: queue count, memory capability, dispatch support,
  queue execution expose.
- `iree_hal_allocator_t`: Apollo/SMMU visible buffer allocate/import.
  초기에는 driver-owned host-visible DMA buffer로 시작하고, 이후 dma-buf
  import/export를 추가한다.
- `iree_hal_executable_cache_t`: `apollo-hexagon-apko-v0` executable data를
  validate/load하고 `iree_hal_executable_t`를 반환한다.
- `iree_hal_command_buffer_t`: `copy_buffer`, `fill_buffer`, `dispatch`,
  `barrier`를 Apollo command list로 record한다.
- `iree_hal_semaphore_t`: IREE timeline wait/signal을 driver fence로 연결한다.

기존 plugin/registry path는 transition smoke lane으로만 유지한다. 새 generic
DNN 실행 경로는 IREE HAL object를 통해 들어와야 한다.

### UMD/Buildroot 전환 작업

UMD 전환은 guest C file 하나만 바꾸는 작업이 아니다. 현재 guest plugin ABI는
`queue_submit_cnn`, `queue_submit_vadd`, `queue_submit_dma_stress`만 노출하므로,
다음 작업을 별도 lane으로 분리한다.

- `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/`
  아래 fixed `apollo_iree_*` shim을 real IREE HAL driver source와 transition
  shim으로 분리한다.
- `apollo_iree_hexagon_plugin.h`의 v1 fixed queue API를 v2 generic executable,
  buffer, command-buffer, fence API로 확장하거나 새 plugin ABI로 대체한다.
- `configs/buildroot/external/apollo_qbox/package/iree-runtime/iree-runtime.mk`가
  `apollo-hexagon` external HAL driver를 link하도록 build option을 추가한다.
- `scripts/build_apollo_hexagon_guest_tools.sh`는 transition runner와 v2 HAL
  driver artifact를 모두 빌드하거나, 최종적으로 v2 HAL driver만 빌드하도록
  단계화한다.
- `scripts/stage_iree_tiny_cnn_guest_artifacts.sh`와
  `scripts/stage_iree_vector_add_guest_artifacts.sh`는 `.vmfb.meta` 중심 staging에서
  APKO/VMFB generic artifact staging으로 전환한다.
- Buildroot rootfs에는 `iree-run-module`, `apollo-hexagon` HAL driver/plugin,
  APKO sample, v2 smoke wrapper를 명시적으로 포함한다.
- transition 기간에는 기존 `apollo-iree-hexagon-runner`를 compat lane으로 남기되,
  generic smoke는 `iree-run-module --device=apollo-hexagon://0`만 성공 조건으로
  본다.

## Device Driver 전면 재개편안

기존 driver는 fixed smoke job을 중심으로 작성되어 있다. 새 DNN kernel 실행을
위해서는 기존 file에 ioctl만 추가하는 방식이 아니라 driver core를 다시 나누는
것이 맞다.

### 새 driver 내부 구조

제안하는 Linux driver module split:

```text
sources/linux/drivers/accel/apollo_hexagon/
  apollo-hexagon-drv.c        # DRM device/probe/remove, file lifetime
  apollo-hexagon-uapi.c       # ioctl dispatch, ABI validation
  apollo-hexagon-context.c    # per-file context, VM/address-space lifetime
  apollo-hexagon-bo.c         # GEM/BO allocation, mmap, import, pin/map
  apollo-hexagon-iommu.c      # SMMU/IOVA mapping, stream/PASID policy
  apollo-hexagon-exec.c       # executable handle table, APKO validation
  apollo-hexagon-submit.c     # command queue submission and scheduler
  apollo-hexagon-fence.c      # timeline fence, IRQ completion, wait
  apollo-hexagon-fault.c      # fault/status decode and debug reporting
  apollo-hexagon-compat.c     # temporary CNN/VADD/DMA_STRESS wrappers
```

파일명은 제안이며, 구현 시 kernel tree style에 맞춰 조정할 수 있다. 중요한 점은
`apollo-hexagon.c` 한 파일에 fixed model logic, DMA setup, ioctl dispatch,
fence handling을 모두 넣는 구조를 끝내는 것이다.

driver split은 source file 추가만으로 끝나지 않는다. 현재
`sources/linux/drivers/accel/apollo_hexagon/Makefile`은
`apollo-hexagon-drm-y := apollo-hexagon.o` 단일 object 중심이고, `Kconfig` help도
repo-local CNN/VADD/DMA stress ABI를 설명한다. 따라서 1단계 refactor에는
다음을 반드시 포함한다.

- `Makefile`을 새 object list로 갱신한다.
- `Kconfig` help를 fixed smoke ABI 중심 설명에서 generic executable/dispatch
  driver 설명으로 바꾼다.
- 기존 selftest config는 유지하되 generic ABI selftest 또는 smoke config가
  필요하면 별도 option으로 추가한다.
- `configs/linux` fragment가 driver option을 계속 enable하는지 확인한다.
- kernel code 변경 단계마다 `kernel-review` post-change review를 수행한다.

### UAPI v2 원칙

새 UAPI는 inline tensor를 받지 않는다. handle과 IOVA-visible buffer descriptor를
사용한다.

```c
DRM_APOLLO_HEXAGON_QUERY_CAPS
DRM_APOLLO_HEXAGON_CREATE_CONTEXT
DRM_APOLLO_HEXAGON_DESTROY_CONTEXT
DRM_APOLLO_HEXAGON_CREATE_BO
DRM_APOLLO_HEXAGON_MMAP_BO
DRM_APOLLO_HEXAGON_IMPORT_BO
DRM_APOLLO_HEXAGON_CREATE_EXECUTABLE
DRM_APOLLO_HEXAGON_DESTROY_EXECUTABLE
DRM_APOLLO_HEXAGON_SUBMIT
DRM_APOLLO_HEXAGON_WAIT
DRM_APOLLO_HEXAGON_GET_FAULT
```

핵심 struct 초안:

```c
struct drm_apollo_hexagon_query_caps {
	__u32 size;
	__u32 flags;
	__u32 generic_abi_version;
	__u32 supported_executable_formats;
	__u32 max_command_bytes;
	__u32 max_bindings_per_dispatch;
	__u32 max_queue_depth;
	__u32 fence_model;
	__u32 smmu_page_granularity;
	__u32 coherency_flags;
	__u32 fault_record_size;
	__u32 reserved;
};

struct drm_apollo_hexagon_exec_create {
	__u32 size;
	__u32 ctx_id;
	__u32 flags;
	__u32 code_bo;
	__u32 metadata_bo;
	__u32 executable_handle;
	__u32 abi_version;
	__u32 reserved;
	__u64 code_offset;
	__u64 code_size;
	__u64 metadata_offset;
	__u64 metadata_size;
};

struct drm_apollo_hexagon_binding {
	__u32 index;
	__u32 bo_handle;
	__u32 usage;
	__u32 flags;
	__u64 offset;
	__u64 length;
};

struct drm_apollo_hexagon_dispatch {
	__u32 size;
	__u32 executable_handle;
	__u32 entry_ordinal;
	__u32 flags;
	__u32 grid_x;
	__u32 grid_y;
	__u32 grid_z;
	__u32 workgroup_x;
	__u32 workgroup_y;
	__u32 workgroup_z;
	__u64 constants_iova;
	__u32 constants_size;
	__u32 binding_count;
	__u64 bindings_iova;
	__u64 reserved;
};

struct drm_apollo_hexagon_submit {
	__u32 size;
	__u32 ctx_id;
	__u32 queue_id;
	__u32 command_bo;
	__u32 flags;
	__u32 fence_out;
	__u64 command_offset;
	__u64 command_size;
};

struct drm_apollo_hexagon_fault {
	__u32 size;
	__u32 ctx_id;
	__u32 queue_id;
	__u32 status;
	__u32 fault_code;
	__u32 executable_handle;
	__u32 entry_ordinal;
	__u32 reserved;
	__u64 fault_iova;
	__u64 fence_seq;
};
```

ABI hardening 규칙:

- 모든 ioctl struct는 `size`와 `reserved` field를 가진다.
- userspace pointer 대신 BO handle과 offset/size를 사용한다.
- 32-bit compat path에서도 layout이 깨지지 않도록 `__u64` alignment를 맞춘다.
- handle lifetime은 per-file context에 묶고, `DESTROY_*` 또는 file close에서
  정리한다.
- BO, executable, fence handle은 refcount를 가진다.
- unknown flag와 non-zero reserved field는 `-EINVAL`로 거부한다.
- `generic_abi_version` mismatch는 `QUERY_CAPS` 또는 `CREATE_CONTEXT` 단계에서
  명확히 실패시킨다.
- fault detail은 submit ioctl return value에 섞지 말고 `GET_FAULT`로 조회한다.
- fixed ioctl compatibility path는 v2 core 내부 helper를 호출하되 v2 ABI
  numbering과 object lifetime을 오염시키지 않는다.

### Query capability 확장

현재 query는 stream, queue, caps, DMA path 수준이다. UMD가 target support를
판단하려면 다음 항목이 필요하다.

```text
generic_abi_version
supported_executable_formats
max_command_bytes
max_bindings_per_dispatch
max_queue_depth
fence_model
smmu_page_granularity
coherency_flags
fault_record_size
```

### 기존 fixed ioctl 처리

`SUBMIT_CNN`, `SUBMIT_VADD`, `DMA_STRESS`는 즉시 삭제하지 않는다. 하지만 새
driver core의 중심 API가 되어서는 안 된다.

전환 원칙:

1. v2 core를 먼저 만든다.
2. fixed ioctl 구현은 `apollo-hexagon-compat.c`로 격리한다.
3. compat path는 내부에서 APKO 또는 built-in compatibility executable을 만들고
   generic submit으로 내려간다.
4. 기존 smoke script가 새 core 위에서 계속 통과하는지 확인한다.
5. generic APKO-VADD, APKO-CNN/MNIST smoke가 안정화되면 fixed ioctl 제거 또는
   test-only config로 축소한다.

### Fence와 fault model

Fence는 monotonic timeline value로 전환한다. IRQ 기반 completion을 기본으로
하고 polling은 timeout/recovery path로만 둔다.

Completion record에는 최소한 다음이 있어야 한다.

```text
queue_id
fence_seq
status
fault_code
fault_iova
executable_handle
entry_ordinal
```

`sources/qbox/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h:326`
의 async IRQ primitive는 재사용 가능하지만, CNN/VADD result magic이 아니라
generic command completion에 연결해야 한다.

### Memory와 coherency model

새 driver는 shared scratch window에 tensor를 써 넣는 구조를 중단해야 한다.
대신 다음 buffer class를 분리한다.

- code BO: executable code/object storage
- metadata BO: APKO manifest, relocation, entry table
- constant BO: runtime constant table
- tensor BO: input/output/intermediate tensor
- scratch BO: per-dispatch temporary storage
- command BO: command list and binding table

각 BO는 CPU/device ownership, cache maintenance, DMA sync rule을 명시해야 한다.
현재 SRAM-style window는 coherency 문제를 숨기므로 DNN path에는 부적합하다.

## QBox Firmware/Hardware Contract

`input_bytes/output_bytes` firmware dispatcher는 command processor로 교체한다.

현재 QBox component는 이미 job register, queue cap, PASID, stream ID, IRQ state를
가지고 있다. 예를 들어
`sources/qbox/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h:62`
에 register set이 있다. 이를 queue ring과 completion ring으로 발전시킨다.

최소 command queue register:

```text
CMDQ_BASE_LO/HI
CMDQ_SIZE
CMDQ_HEAD
CMDQ_TAIL
DOORBELL
STATUS
FENCE_VALUE
FAULT_CODE
FAULT_ADDR_LO/HI
CAPS
```

최소 command packet:

```text
NOP
LOAD_EXECUTABLE
DISPATCH
COPY
FILL
BARRIER
SIGNAL_FENCE
```

`DISPATCH` packet:

```text
executable_handle
entry_ordinal
grid[3]
workgroup[3]
binding_table_iova
binding_count
constant_data_iova
constant_data_size
flags
```

resident Hexagon firmware는 기존 platform boot path로 계속 load할 수 있다.
per-kernel binary는 새 executable/command ABI로 load한다.
`sources/qbox/qemu-components/hexagon_globalreg/include/hexagon_globalreg.h:51`은
Hexagon global register property를 설정하고,
`sources/qbox/qemu-components/cpu_hexagon/include/hexagon.h:75`는 CPU QOM type을
설정한다. 새 ABI는 fixed firmware blob 가정 대신 executable handle과 entry
ordinal을 전달해야 한다.

## Repo Contract Migration

현재 repo contract는 fixed CNN/VADD path를 정상 상태로 강제한다. 예를 들어
`scripts/check_buildroot_arm64_lane.sh`는 `DRM_IOCTL_APOLLO_HEXAGON_SUBMIT_CNN`,
`DRM_IOCTL_APOLLO_HEXAGON_SUBMIT_VADD`, `command_buffer=fixed`,
`EXEC @tiny_cnn_graph [apollo-hexagon]`, `EXEC @vector_add_graph [apollo-hexagon]`
같은 marker를 요구한다. generic DNN path를 구현하려면 contract도 단계적으로
바꿔야 한다.

전환 방식:

1. `check_buildroot_arm64_lane.sh`를 `compat fixed path`와 `generic v2 path`
   check로 분리한다.
2. 기존 fixed marker는 transition 기간에만 compat section에서 검사한다.
3. 새 generic section은 다음 marker를 요구한다.
   - `DRM_APOLLO_HEXAGON_CREATE_EXECUTABLE`
   - `DRM_APOLLO_HEXAGON_SUBMIT`
   - `apollo-hexagon-apko-v0`
   - `iree-run-module --device=apollo-hexagon://0`
   - `generic submit ok`
   - `APKO dispatch complete`
4. `scripts/check_iree_cnn_pipeline_readiness.py`는 fixed runner readiness와
   generic APKO/IREE HAL readiness를 별도 항목으로 보고해야 한다.
5. 기존 smoke scripts는 새 generic scripts와 병행한다.
   - compat: `run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh`,
     `run_iree_vector_add_hexagon_qbox_guest_smoke.sh`
   - generic: `run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh`,
     `run_iree_apko_cnn_hexagon_qbox_guest_smoke.sh`
   - 2026-05-18 현재 repository에는 위 generic script scaffold가 추가되었고,
     compat lane은 유지되며 generic APKO ABI/dispatch 부재는 blocked 메시지로
     명시한다.
6. `doc/verification/` report는 fixed compat 통과와 generic v2 통과를 혼동하지
   않도록 따로 기록한다.

## 단계별 전환 계획

### 1단계: driver 구조 분리, 동작 보존

- `apollo-hexagon.c`의 ioctl dispatch, DMA setup, fence, fixed job logic을
  내부 module 단위로 분리한다.
- `Makefile`, `Kconfig`, `configs/linux` fragment를 새 object layout에 맞춘다.
- 외부 UAPI behavior는 유지한다.
- 목표는 behavior change 없이 driver ownership boundary를 만드는 것이다.
- 검증: 기존 CNN/VADD/DMA stress smoke가 동일하게 동작해야 한다.

필수 검증:

```bash
./scripts/build_qbox_linux_arm64.sh
./scripts/check_buildroot_arm64_lane.sh
git diff --check
```

필수 log/contract marker:

```text
DRM_IOCTL_APOLLO_HEXAGON_SUBMIT_CNN
DRM_IOCTL_APOLLO_HEXAGON_SUBMIT_VADD
accelerator tiny cnn ok
accelerator vector add ok
```

### 2단계: UAPI v2와 core object 도입

- context, BO, executable, submit, wait ioctl을 추가한다.
- query caps에 generic ABI version과 executable format support를 추가한다.
- fixed ioctl은 `compat` layer로 이동한다.
- driver core는 inline tensor를 알지 못하게 한다.

필수 검증:

```bash
./scripts/build_qbox_linux_arm64.sh
python3 scripts/check_qbox_smmuv3_compliance.py --repo .
./scripts/check_buildroot_arm64_lane.sh
```

필수 log/contract marker:

```text
DRM_APOLLO_HEXAGON_QUERY_CAPS
DRM_APOLLO_HEXAGON_CREATE_CONTEXT
DRM_APOLLO_HEXAGON_CREATE_EXECUTABLE
DRM_APOLLO_HEXAGON_SUBMIT
generic_abi_version
```

### 3단계: QBox command queue 도입

- 기존 byte-count based firmware dispatch를 command queue parser로 교체한다.
- APKO-VADD를 첫 generic command로 실행한다.
- 이 단계의 성공 조건은 VADD가 `SUBMIT_VADD`가 아니라 generic executable
  handle과 dispatch descriptor로 실행되는 것이다.

필수 검증:

```bash
./scripts/build_qbox_hexagon_firmware.sh
./scripts/build_qbox_buildroot_platform.sh
./scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh
```

필수 log marker:

```text
APKO dispatch start
generic submit ok
APKO dispatch complete
async fence signaled
```

### 4단계: Apollo IREE HAL UMD 구현

- `apollo-hexagon` IREE HAL driver를 out-of-tree driver로 등록한다.
- allocator, executable cache, command buffer, queue execute, semaphore/fence를
  구현한다.
- `iree-run-module --list_drivers`에서 `apollo-hexagon`이 보여야 한다.
- `iree-run-module --dump_devices --device=apollo-hexagon://0`이 capability를
  출력해야 한다.

필수 검증:

```bash
./scripts/build_iree_runtime_buildroot.sh
./scripts/build_apollo_hexagon_guest_tools.sh
iree-run-module --list_drivers | grep apollo-hexagon
iree-run-module --dump_devices --device=apollo-hexagon://0
```

필수 log marker:

```text
apollo-hexagon
executable_format=apollo-hexagon-apko-v0
allocator=device-visible
queue_execute=drm-accel
```

### 5단계: IREE compiler/APKO bridge

- 우선 VADD와 작은 CNN/MNIST subset만 지원한다.
- IREE HAL executable data에 `apollo-hexagon-apko-v0`를 넣는다.
- unsupported op은 compile time에 실패시킨다. Apollo test에서 CPU fallback은
  허용하지 않는다.

필수 검증:

```bash
iree-import-onnx model.onnx --opset-version 17 -o model.mlir
iree-compile model.mlir \
  --iree-hal-target-device=apollo-hexagon \
  --iree-hal-target-backends=apollo-hexagon \
  -o model_apollo.vmfb
```

필수 artifact/marker:

```text
model_apollo.vmfb
apollo-hexagon-apko-v0
unsupported op rejected
CPU fallback disabled
```

### 6단계: end-to-end DNN smoke

새 happy path:

```bash
iree-import-onnx model.onnx --opset-version 17 -o model.mlir
iree-compile model.mlir \
  --iree-hal-target-device=apollo-hexagon \
  --iree-hal-target-backends=apollo-hexagon \
  -o model_apollo.vmfb
iree-run-module \
  --module=model_apollo.vmfb \
  --device=apollo-hexagon://0 \
  --function=<entry> \
  --input=<input>
```

성공 조건:

- VMFB 안의 HAL executable data가 APKO로 전달된다.
- UMD가 APKO를 executable handle로 load한다.
- driver가 generic submit으로 command queue를 program한다.
- QBox firmware/hardware가 `DISPATCH` packet을 해석한다.
- completion IRQ/fence가 돌아온다.
- guest log가 `tiny_cnn_graph`, `vector_add_graph`, `SUBMIT_CNN`,
  `SUBMIT_VADD` marker에 의존하지 않는다.

필수 검증:

```bash
./scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh
./scripts/run_iree_apko_cnn_hexagon_qbox_guest_smoke.sh
```

필수 log marker:

```text
EXEC @<entry> [apollo-hexagon]
APKO dispatch complete
generic submit ok
SMMU translated buffer
async fence signaled
```

## 검증 계획

driver refactor 단계에서는 기존 smoke를 보존해야 한다.

```bash
./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh
./scripts/run_iree_vector_add_hexagon_qbox_guest_smoke.sh
```

generic path 검증:

```bash
iree-run-module --list_drivers | grep apollo-hexagon
iree-run-module --dump_devices --device=apollo-hexagon://0
```

driver build와 contract 검증:

```bash
./scripts/build_qbox_linux_arm64.sh
./scripts/build_qbox_buildroot_platform.sh
./scripts/build_apollo_hexagon_guest_tools.sh
./scripts/build_iree_runtime_buildroot.sh
./scripts/check_buildroot_arm64_lane.sh
python3 scripts/check_qbox_smmuv3_compliance.py --repo .
python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . \
  --json build/verification/iree-readiness.json
```

새 evidence는 `build/verification/`과 `doc/verification/`에 날짜를 포함해 남긴다.

필수 evidence:

- APKO-VADD가 generic submit으로 실행되고 `SUBMIT_VADD`를 사용하지 않았다는
  log.
- APKO-CNN 또는 MNIST가 generic submit으로 실행되고 fixed CNN byte-count
  branch를 사용하지 않았다는 log.
- SMMU translated buffer와 IRQ-backed fence completion log.
- unsupported ONNX op, APKO ABI mismatch, invalid IOVA에 대한 negative test.
- `check_buildroot_arm64_lane.sh`가 compat fixed path와 generic v2 path를 별도로
  보고한다는 JSON/text evidence.
- `Makefile`, `Kconfig`, `configs/linux` fragment가 새 driver object layout을
  반영한다는 build evidence.

코드 변경 후 기본 repo contract:

```bash
git diff --check
./scripts/check_buildroot_arm64_lane.sh
python3 scripts/check_qbox_smmuv3_compliance.py --repo .
```

kernel code를 실제로 수정하는 단계에서는 `kernel-review` skill의 post-change
review를 별도로 수행해야 한다.

## 열린 결정 사항

- APKO v0 payload를 QBox interpreter bytecode로 먼저 시작할지, Hexagon ELF64를
  바로 payload로 둘지 결정해야 한다. 현재 구현 리스크는 APKO/interpreter first가
  낮다.
- memory object를 driver-owned BO로 시작할지, 초기에 dma-buf import/export까지
  포함할지 결정해야 한다.
- queue 0 transfer / queue 1 compute split은 compatibility 목적으로만 유지하고,
  새 path에서는 IREE HAL queue affinity로 표현해야 한다.
- fixed CNN/VADD ioctl 제거 시점은 APKO-VADD와 APKO-CNN/MNIST smoke가 모두
  안정화된 이후로 제한한다.
- QBox SMMU path는 functional integration slice로만 주장해야 한다. bit-exact
  Arm SMMUv3 구현이라고 과장하지 않는다.
- UAPI v2 ioctl number는 fixed ioctl 뒤에 append할지, 새 driver major/minor ABI
  gate와 함께 재정렬할지 결정해야 한다. Upstream-friendly path는 existing ioctl
  numbering을 보존하고 새 ioctl을 append하는 것이다.
- APKO fault record를 command completion ring에 inline으로 둘지, `GET_FAULT`
  ioctl로 분리할지 결정해야 한다. 초기 계획은 `GET_FAULT` 분리 방식이다.
- generic v2 smoke script 이름과 artifact directory layout은 implementation 전에
  확정해야 한다. 이 문서는 `run_iree_apko_*` 이름을 제안으로 사용한다.

## 권장 작업 순서

1. 기존 `apollo-hexagon.c`를 driver core, UAPI, context, BO, executable,
   submit, fence, fault, compat module로 재구성하고 `Makefile`/`Kconfig`를
   갱신한다.
2. repo contract checker와 smoke scripts를 compat fixed path와 generic v2 path로
   분리한다.
3. behavior preserving refactor가 끝난 뒤 UAPI v2를 append-only 방식으로 추가한다.
4. QBox command queue와 APKO-VADD generic dispatch를 먼저 구현한다.
5. Apollo IREE HAL UMD를 실제 IREE HAL driver로 붙이고 Buildroot rootfs staging을
   갱신한다.
6. IREE/Hexagon-MLIR bridge에서 APKO v0를 VMFB HAL executable data로 package한다.
7. VADD, CNN/MNIST 순서로 fixed ioctl smoke를 VMFB-driven APKO dispatch로
   이동한다.

이 구조가 요청한 `iree compile -> VMFB -> IREE runtime -> Apollo Hexagon UMD
-> Apollo Hexagon driver -> Apollo Hexagon hardware` 경로와 가장 잘 맞는다.
driver는 graph runtime이 아니라 accelerator resource manager가 되고, DNN
kernel 실행 semantics는 IREE HAL UMD와 APKO executable ABI에 남는다.
