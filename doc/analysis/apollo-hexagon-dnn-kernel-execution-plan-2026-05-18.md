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

2026-05-20 추가 진행으로 sidecar metadata 의존성을 줄이는 transition path를
추가했다. staging script는 `vector_add_apollo.vmfb`와 `tiny_cnn_apollo.vmfb` 뒤에
repo-local APKO trailer를 붙이고, guest HAL loader는 metadata path가 비어 있을 때
VMFB footer를 찾아 APKO v0 payload를 추출한다. 이 경로는
`executable_source=vmfb-embedded-apko` marker로 구분한다. 단, 이것은 아직 upstream
IREE compiler가 HAL executable section에 APKO를 packaging했다는 뜻이 아니며,
그 target backend packaging은 별도 남은 작업이다.

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

2026-05-19 리뷰 반영으로 1차 split은 완료됐다. 현재 source layout은
`apollo-hexagon.c`가 DRM core/probe/ioctl table, `apollo-hexagon-context.c`가
per-file generic context handle, `apollo-hexagon-bo.c`가 GEM SHMEM buffer object
생성/삭제, `apollo-hexagon-exec.c`가 APKO executable handle/generic
submit/`GET_FAULT`, `apollo-hexagon-compat.c`가 fixed CNN/VADD/DMA stress
compatibility submit을 담당한다. 이 단계는 behavior-preserving 분리와
context/BO foundation이며, 아래 v2 구조 중 IOMMU binding, command ring, wait,
fence, fault module 분리는 다음 구현 단계로 남아 있다.

같은 날 다음 foundation slice로 `DRM_APOLLO_HEXAGON_QUERY_CAPS`도 append-only로
추가했다. 이 ioctl은 `generic_abi_version`, supported executable format bitmap,
queue depth/count, fence model, SMMU page granularity, fault record size를
userspace에 노출한다. 2026-05-20 APKO VADD CMDQ 연결 이후
`max_command_bytes`는 현재 지원하는 1개 32-byte `DISPATCH/VADD` packet 크기를
보고한다. 추가 진행으로 VADD `CMD_SUBMIT` path가 input/output BO binding 2개를
소비하는 transitional copy shim을 갖게 되어 `max_bindings_per_dispatch=2`를
보고한다. 이는 true hardware BO page mapping 완료를 뜻하지 않는다.

추가 리뷰 반영으로 `DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_CREATE`와
`DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_DESTROY`도 append-only로 추가했다. 현재 context는
per-file xarray handle lifetime, ABI version validation, queue/fence capability
return, stale-handle rejection을 제공하는 foundation이다. 아직 address space,
hardware BO mapping, command queue ownership까지 context에 연결하지는 않는다.

2026-05-20 리뷰 반영으로 `DRM_IOCTL_APOLLO_HEXAGON_BO_CREATE`와
`DRM_IOCTL_APOLLO_HEXAGON_BO_DESTROY`도 append-only로 추가했다. 현재 BO는 DRM GEM
SHMEM helper를 이용해 per-file GEM handle과 `mmap_offset`을 반환하고,
`drm_gem_handle_delete()`로 lifetime을 종료하는 foundation이다. 아직 Apollo TBU
hardware IOVA mapping, per-context address-space ownership, dma-buf import/export는
남아 있다. 다만 VADD command BO path는 staged IOVA를 binding table에서 찾아
input BO를 shared SRAM으로 복사하고 output BO로 결과를 되돌리는 transitional
shim으로 먼저 연결했다.
추가 리뷰 반영으로 이 `CMD_SUBMIT` VADD shim은 file-level `afile->lock`을 잡은
채 QBox CMDQ completion을 기다리지 않는다. Binding table lookup과 input snapshot은
lock 안에서 끝내고, output BO는 GEM object ref를 잡아 lock 밖의 hardware wait와
copy-back 동안 lifetime을 보장한다.

같은 날 추가 리뷰 반영으로 `DRM_IOCTL_APOLLO_HEXAGON_BO_BIND`와
`DRM_IOCTL_APOLLO_HEXAGON_BO_UNBIND`도 append-only로 추가했다. 현재 BO binding은
context-owned xarray에 GEM BO reference, offset, length, usage, staged IOVA를
저장하는 metadata foundation이다. 아직 GEM page를 Apollo TBU/SMMU hardware
mapping에 install하지는 않는다. VADD `CMD_SUBMIT` slice에서는 이 metadata를
transitional copy shim으로 먼저 소비한다.
추가 리뷰 refresh에서는 BO_UNBIND도 `size/flags`를 검증하게 했고, staged IOVA
계산에 `check_add_overflow()` guard를 추가했다.

같은 날 추가 진행으로 `DRM_IOCTL_APOLLO_HEXAGON_WAIT`도 append-only로 추가했다.
현재 WAIT은 synchronous submit 이후 완료된 fence를 확인하고, `status`,
`result`, `current_fence_seq`를 snapshot으로 돌려주는 foundation이다. future
fence에 대한 zero-timeout path는 `-ETIMEDOUT`으로 검증한다. 아직 command ring
기반 async submit과 timeline semaphore ownership이 구현된 것은 아니다.

driver split은 source file 추가만으로 끝나지 않는다. 초기 plan 작성 시점에는
`sources/linux/drivers/accel/apollo_hexagon/Makefile`이
`apollo-hexagon-drm-y := apollo-hexagon.o` 단일 object 중심이었다. 현재는
`apollo-hexagon.o`, `apollo-hexagon-bo.o`, `apollo-hexagon-context.o`,
`apollo-hexagon-compat.o`, `apollo-hexagon-exec.o`, `apollo-hexagon-fence.o`가
같은 DRM driver object로
link된다. 남은 refactor에는 다음을 포함한다.

- v2 IOMMU/submit/fault object list를 `Makefile`에 추가한다.
- `Kconfig` help는 generic APKO/context/GEM BO ABI와 fixed compat ioctl의
  transition 관계를 설명하도록 갱신했다. 이후 command ring이 추가되면
  설명을 다시 좁혀야 한다.
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
DRM_APOLLO_HEXAGON_CREATE_BO    // 구현 이름은 BO_CREATE
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

2026-05-20 리뷰 반영으로 위 register foundation의 QBox component side를 먼저
추가했고, 이어서 command packet의 최소 실행 subset을 붙였다. 현재
`CMDQ_DOORBELL`은 선형 non-wrapping queue에서 `NOP`, `COPY`, `BARRIER`,
`SIGNAL_FENCE`, `LOAD_EXECUTABLE`, `DISPATCH/VADD`를 fetch/decode/execute하고,
empty queue, unsupported packet, malformed packet, DMA/TLM 실패는 fault register에
남긴 뒤 기존 async IRQ/fence path로 completion을 만든다. `LOAD_EXECUTABLE`은
APKO v0 metadata를 QBox-side executable slot에 적재하고, executable-slot
`DISPATCH`가 그 metadata를 참조해 VADD를 실행한다. 추가 리뷰 반영으로 queue
geometry 검증 순서를 조정해 out-of-range head/tail이 empty queue로 오분류되지 않게
했고, command queue 주소 계산에는 base+offset overflow guard를 넣었다. Component
test도 malformed geometry, COPY DMA fault, LOAD_EXECUTABLE valid/invalid,
DISPATCH/VADD 성공, DISPATCH/VADD DMA fault 경로를 포함한다. APKO VADD sidecar
smoke 경로는 Linux driver가 GEM SHMEM command BO에서 2-packet
`LOAD_EXECUTABLE -> DISPATCH(exec-slot)` command buffer를 fetch해 QBox
`CMDQ_DOORBELL`을 울리는 path로 연결했다. APKO negative smoke는 malformed
`LOAD_EXECUTABLE`과 invalid IOVA `COPY` packet을 command BO로 제출해 fault record를
검증한다. 추가 리뷰 반영으로 CNN/MNIST-like CMDQ dispatch는 Linux/UMD
`CMD_SUBMIT` 경계에 연결됐다. 아직 true APKO code/payload loading, true hardware
BO mapping, true MNIST ONNX model semantics는 다음 단계다.

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
   - `DRM_IOCTL_APOLLO_HEXAGON_EXEC_CREATE`
   - `DRM_IOCTL_APOLLO_HEXAGON_SUBMIT`
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
   - 2026-05-18 리뷰 반영 후 repository에는 APKO v0 executable handle,
     generic submit ioctl, guest HAL APKO loader, APKO VADD/CNN smoke가
     추가되었다. compat lane은 유지하되 generic APKO smoke는 별도 PASS
     기준으로 검증한다.
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

2026-05-20 현재 `QUERY_CAPS`, `CONTEXT_CREATE/DESTROY`,
`BO_CREATE/DESTROY`, `BO_BIND/UNBIND`, `EXEC_CREATE/DESTROY`, `SUBMIT`, `WAIT`,
`GET_FAULT`, 32-byte command BO `CMD_SUBMIT` foundation, VADD binding-table
copy shim은 구현되어 있다. 남은 작업은 true hardware BO mapping, executable
payload dispatch 연결, CNN/MNIST generic CMDQ dispatch다.

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

2026-05-18 리뷰 반영 구현 상태:

- APKO sidecar metadata를 통해 UMD가 `EXEC_CREATE -> SUBMIT -> EXEC_DESTROY`
  순서로 driver에 executable handle을 등록하고 generic submit을 호출한다.
- QBox guest VADD/CNN APKO smoke는 `command-buffer=generic-submit`,
  `generic submit ok`, `APKO dispatch complete` marker와 결과 tensor를 검증한다.
- QBox guest APKO negative smoke는 invalid APKO header, wrong command size,
  wrong queue, invalid user pointer, stale executable handle rejection, empty
  `GET_FAULT` retrieval, invalid IOVA fault-producing `GET_FAULT` retrieval을
  검증한다.
- 2026-05-20 BO foundation 추가 후 APKO negative smoke는 zero-size BO reject,
  GEM BO create/destroy, stale BO handle reject도 검증한다.
- 2026-05-20 WAIT foundation 추가 후 APKO negative smoke는 bad WAIT size,
  zero WAIT fence, bad WAIT queue, completed fence wait, future fence timeout도
  검증한다.
- 아직 VMFB 내부 HAL executable data에 APKO를 직접 packaging하는 IREE compiler
  backend는 구현되지 않았다. 현재 경로는 staged `.vmfb.meta`와 `.apko` sidecar를
  이용하는 repo-local bridge다.

성공 조건:

- VMFB 안의 HAL executable data가 APKO로 전달된다.
- UMD가 APKO를 executable handle로 load한다.
- driver가 generic submit으로 command queue를 program한다. APKO VADD/CNN/MNIST-like
  경로는 `LOAD_EXECUTABLE -> DISPATCH(exec-slot)` CMDQ submit으로 연결됐고, VMFB
  내부 upstream HAL executable data packaging과 true MNIST model semantics는 다음
  범위다.
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
- unsupported ONNX op에 대한 negative test와 invalid IOVA 기반 fault-producing
  retrieval positive test.
- context ABI mismatch, stale context handle, APKO ABI mismatch, wrong entry
  kind, wrong command size, invalid user pointer, stale executable handle, empty
  fault record rejection, bad BO size, BO create/destroy, stale BO handle
  rejection에 대한 negative smoke evidence.
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
  바로 payload로 둘지 결정해야 한다. 리뷰 반영 구현은 header-only APKO sidecar로
  시작했으며, payload semantics는 아직 고정하지 않았다.
- memory object는 driver-owned GEM SHMEM BO로 시작했다. dma-buf import/export와
  Apollo TBU IOVA binding은 별도 단계에서 추가해야 한다.
- queue 0 transfer / queue 1 compute split은 compatibility 목적으로만 유지하고,
  새 path에서는 IREE HAL queue affinity로 표현해야 한다.
- fixed CNN/VADD ioctl 제거 시점은 APKO-VADD와 APKO-CNN/MNIST smoke가 모두
  안정화되고 negative coverage가 추가된 이후로 제한한다.
- QBox SMMU path는 functional integration slice로만 주장해야 한다. bit-exact
  Arm SMMUv3 구현이라고 과장하지 않는다.
- UAPI v2 ioctl number는 append-only 방식으로 시작했다. 이후 incompatible 변경이
  필요하면 새 ABI version 또는 driver minor gate로 분리해야 한다.
- APKO fault record는 초기 `GET_FAULT` ioctl 분리 방식으로 시작했고,
  현재 submit failure path는 `apollo_hexagon_wait_job()` 또는 `CMD_SUBMIT`
  completion snapshot이 읽은 final status/result/fence를 record에 저장한다.
  invalid IOVA command BO fault는 `GET_FAULT` clear retrieval smoke로 검증한다.
- generic v2 smoke script 이름은 `run_iree_apko_*` 계열로 시작했다. WAIT,
  BO binding, VMFB-embedded APKO 단계에서 artifact directory layout을 다시
  정리해야 한다.

## 권장 작업 순서

2026-05-20 계획 리뷰 반영:

- 실행 계획의 현재 상태와 최종 목표를 분리한다. 이미 구현된
  `QUERY_CAPS`, context, BO lifecycle, BO binding metadata, `WAIT`,
  `CMD_SUBMIT`, `GET_FAULT`, VADD/CNN/MNIST-like binding-table copy shim은
  foundation으로 기록하고, true hardware BO mapping, true APKO payload execution,
  true MNIST ONNX model semantics, upstream VMFB HAL executable packaging은 남은
  작업으로 유지한다.
- 기존 device driver는 부분 확장이 아니라 v2 resource manager로 전면 재개편한다.
  fixed CNN/VADD/DMA stress ioctl은 `apollo-hexagon-compat.c`의 transition shim으로
  한정하고, 새 중심 경로는 context, GEM BO, SMMU-visible binding, executable
  handle, command BO submit, wait/fence, fault record다.
- 이번 구현 순서는 APKO VADD sidecar smoke를 더 늘리는 것이 아니라 UMD happy
  path가 `BO_CREATE -> BO_BIND -> CMD_SUBMIT`을 사용하도록 전환하는 것이다.
  구현된 path는 QBox shared SRAM 상수 주소에 의존하는 transitional copy shim이며,
  실제 Apollo TBU/SMMU mapping과는 문서와 evidence에서 구분한다.
- VMFB-embedded APKO transition slice는 staged VMFB trailer에서 APKO를 추출하는
  repo-local ABI다. 리뷰 반영으로 APKO `header_bytes` 검증과 UMD executable unload
  path를 추가했지만, 여전히 upstream IREE compiler target backend가 생성하는 HAL
  executable section은 아니다.
- `$team` 실행은 tmux leader session에서만 정상 생성으로 인정한다. 현재 Codex
  App shell처럼 `$TMUX`가 비어 있는 환경에서는 launch command와 lane 배치만
  제공하고, team 생성 완료로 보고하지 않는다.
- 세부 task breakdown은
  `doc/analysis/apollo-hexagon-dnn-kernel-task-breakdown-2026-05-20.md`에 유지한다.
  해당 문서는 lane별 소유 파일, 선행 조건, 완료 기준, 검증 gate를 포함한다.

1. 완료: APKO executable table, generic submit, `GET_FAULT`는
   `apollo-hexagon-exec.c`, fixed compat submit/DMA stress path는
   `apollo-hexagon-compat.c`로 behavior-preserving 분리했다. 다음 driver 작업은
   IOMMU/command ring/fence/fault module 분리와 hardware BO mapping이다.
2. 완료: `DRM_APOLLO_HEXAGON_QUERY_CAPS`를 추가해 UMD가 generic ABI version,
   APKO executable format support, fence/fault capability를 질의하게 했다.
   `CREATE_CONTEXT/DESTROY_CONTEXT`, `BO_CREATE/BO_DESTROY`, `BO_BIND/BO_UNBIND`,
   `WAIT` foundation과 32-byte command BO `CMD_SUBMIT` foundation도 추가했다.
   VADD path는 command BO가 input/output BO binding table을 소비하는 transitional
   copy shim까지 갖는다. 추가 진행으로 `CMD_SUBMIT`은 2-packet command buffer를
   받아 `LOAD_EXECUTABLE -> DISPATCH(exec-slot)`을 제출한다. 남은 v2 foundation은
   true APKO code/payload loading과 true hardware BO mapping이다.
3. 완료: APKO VADD/CNN/MNIST-like generic submit은 `CMDQ_BASE/HEAD/TAIL/DOORBELL`
   register를 program하고 QBox `LOAD_EXECUTABLE -> DISPATCH(exec-slot)` packet으로
   실행한다. APKO UMD happy path는 이제 `BO_CREATE/BO_BIND/CMD_SUBMIT`을 사용한다.
4. 남은 negative tests를 추가한다. 이미 추가된 범위는 APKO ABI mismatch,
   context ABI mismatch, stale context handle, bad BO size, BO create/destroy,
   stale BO handle, bad BO bind size, bad bind context/BO handle, unaligned bind
   length, bad BO unbind size, BO bind/unbind, stale bind handle, bad WAIT size,
   zero WAIT fence, bad WAIT queue, completed fence wait, future fence timeout,
   wrong entry kind,
   wrong input/output size,
   invalid user pointer, wrong queue, stale executable handle, empty fault record
   retrieval, bad command BO submit size/context/handle/size, command BO
   `SIGNAL_FENCE` submit, invalid IOVA command BO `COPY` fault와 `GET_FAULT`
   retrieval이다. 남은 범위는 unsupported ONNX op이다.
5. repo contract checker와 smoke scripts에서 compat fixed path와 generic APKO
   path를 계속 분리한다.
6. Apollo IREE HAL UMD를 실제 IREE HAL driver로 붙이고 Buildroot rootfs staging을
   갱신한다.
7. IREE/Hexagon-MLIR bridge에서 APKO v0를 VMFB HAL executable data로 package한다.
8. VADD, CNN/MNIST-like fixed ioctl smoke를 VMFB-driven APKO dispatch로 이동했다.
   true MNIST ONNX compile artifact와 upstream IREE VMFB HAL executable section
   packaging은 별도 작업으로 남긴다.

2026-05-21 추가 리뷰 반영:

- kernel UAPI와 guest UAPI에 `APOLLO_HEXAGON_EXEC_KIND_MNIST` 및 MNIST-like
  smoke geometry를 추가했다.
- Linux driver `CMD_SUBMIT` scanner는 `LOAD_EXECUTABLE` metadata에서 MNIST-like
  executable slot을 인식하고, guest HAL은 `mnist_graph`를 APKO CMDQ 경로로 제출한다.
- 새 staging/smoke 계약은 `stage_iree_mnist_guest_artifacts.sh`와
  `run_iree_apko_mnist_hexagon_qbox_guest_smoke.sh`에 있다. 이 artifact는 DNN kernel
  ABI 연결 검증용 deterministic byte-invert stub이며, true MNIST ONNX 모델 compile
  성공으로 해석하지 않는다.

이 구조가 요청한 `iree compile -> VMFB -> IREE runtime -> Apollo Hexagon UMD
-> Apollo Hexagon driver -> Apollo Hexagon hardware` 경로와 가장 잘 맞는다.
driver는 graph runtime이 아니라 accelerator resource manager가 되고, DNN
kernel 실행 semantics는 IREE HAL UMD와 APKO executable ABI에 남는다.
