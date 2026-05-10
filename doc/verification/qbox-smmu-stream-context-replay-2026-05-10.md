# QBox Apollo ARM SMMUv3 stream/context/fault replay 검증 리포트

- 날짜: 2026-05-10
- 대상: `/build/qbox_dev`
- 목표: Apollo Hexagon DMA/IREE offload 경로의 SMMUv3 모델을 Stream Table
  Entry, Context Descriptor, 4-level page-table descriptor walk, ATS/PRI 응답,
  fault queue/replay가 보이는 compliance-oriented slice로 확장한다.

## 결론

PASS. 이번 범위에서 QBox Apollo SMMU TBU와 Linux probe는 다음 항목을
동일 booted guest smoke에서 검증했다.

1. Stream table base에서 Stream Table Entry를 fetch/decode한다.
2. STE가 가리키는 Context Descriptor를 fetch/decode하고 TTBR을 얻는다.
3. 4KB granule 4-level table descriptor chain을 walk해서 최종 PA를 얻는다.
4. 성공/실패 경로 모두에서 architected ATS/PRI response counter를 갱신한다.
5. invalid STE negative test가 fault queue와 replay counter를 갱신한다.
6. 같은 guest run에서 128KiB/8-segment SG DMA, queue 0/1 async fence,
   dynamic C HAL plugin, tiny-CNN Hexagon offload 결과를 확인했다.

범위 경계: 이 결과는 **full ARM SMMUv3 compliance model을 향한
compliance-oriented integration slice**이다. 전체 SMMUv3 register file,
command/event/PRI queue의 bit-exact 프로토콜, 모든 STE/CD format, stage-1/2
조합, interrupt semantics 전체를 구현한 upstream-grade IP 모델은 아직 별도
architecture work로 남아 있다.

## 구현 요약

| 영역 | 파일 | 내용 |
| --- | --- | --- |
| QBox TBU | `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h` | STE/CD base registers, STE/CD fetch, 4-level descriptor walk, ATS/PRI protocol status, fault reason/replay registers, negative replay control |
| Linux probe | `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c` | shared SRAM에 STE/CD/page-table staging, positive descriptor probe 검증, invalid STE negative fault replay suite |
| Linux UAPI | `sources/linux/include/uapi/linux/apollo_hexagon.h` | multi-queue/async/large transfer ABI 확장 유지 |
| Smoke contract | `scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` | STE/CD walk, ATS/PRI, fault replay, 128KiB SG DMA, async fence, dynamic HAL plugin marker 검증 |
| Lane contract | `scripts/check_buildroot_arm64_lane.sh` | SMMUv3 stream/context/fault replay 구현 marker 정적 검사 |
| Readiness | `scripts/check_iree_cnn_pipeline_readiness.py` | `tbu_stream_context_descriptor_walk`, `tbu_arch_fault_replay_protocol`, Linux negative replay checks 추가 |
| Spec | `doc/spec/qbox-iree-cnn-pipeline-tasks.md` | 완료 slice와 남은 full bit-exact SMMUv3 범위 구분 |

## 검증 명령

```bash
./scripts/build_qbox_linux_arm64.sh \
  2>&1 | tee build/verification/linux-smmu-stream-context-20260510.log

./scripts/build_qbox_buildroot_platform.sh \
  2>&1 | tee build/verification/qbox-platform-smmu-stream-context-20260510-retry1.log

./scripts/stage_buildroot_artifacts.sh \
  2>&1 | tee build/verification/stage-artifacts-smmu-stream-context-20260510.log

./scripts/build_apollo_hexagon_guest_tools.sh \
  2>&1 | tee build/verification/apollo-hexagon-guest-tools-smmu-stream-context-20260510.log

QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260510-smmu-stream-context-retry2 \
QBOX_IREE_LOGIN_DELAY=24 \
QBOX_IREE_COMMAND_DELAY=3 \
QBOX_IREE_AFTER_COMMAND_DELAY=20 \
QBOX_BOOT_TIMEOUT=180 \
  ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh \
  2>&1 | tee build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-stream-context-retry2.driver.log

bash -n scripts/*.sh \
  configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/post-build.sh
python3 -m py_compile \
  scripts/check_iree_cnn_pipeline_readiness.py scripts/qbox_pty_runner.py
./scripts/check_buildroot_arm64_lane.sh
./scripts/check_iree_cnn_pipeline_readiness.py \
  --json build/verification/iree-cnn-readiness-smmu-stream-context-final.json
git diff --check
git -C sources/qbox diff --check
git -C sources/linux diff --check
```

## 증거 로그

- Linux Image build: `build/verification/linux-smmu-stream-context-20260510.log`
- QBox platform build:
  `build/verification/qbox-platform-smmu-stream-context-20260510-retry1.log`
- Artifact staging: `build/verification/stage-artifacts-smmu-stream-context-20260510.log`
- Guest tools build:
  `build/verification/apollo-hexagon-guest-tools-smmu-stream-context-20260510.log`
- QBox guest smoke:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-stream-context-retry2.log`
- QBox guest smoke driver:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-stream-context-retry2.driver.log`
- QBox boot log:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-boot-20260510-smmu-stream-context-retry2.log`
- Final static/readiness log:
  `build/verification/smmu-stream-context-final-static-20260510.log`
- Readiness JSON:
  `build/verification/iree-cnn-readiness-smmu-stream-context-final.json`

## 핵심 runtime 출력

```text
APOLLO_SMMU_TBU: architectural stream table walk stream-id=0x1 ste-pa=0xa1c040 ste=0x3 cd-table=0xa1d000
APOLLO_SMMU_TBU: architectural context descriptor walk stream-id=0x1 cd-pa=0xa1d000 cd=0x1 ttbr=0xa18000
APOLLO_SMMU_TBU: architectural descriptor walk stream-id=0x1 levels=4 ttbr=0xa18000 desc-pa=0xa1b000 desc=0xa00703 iova=0x10000000 pa=0xa00000
APOLLO_SMMU_TBU: architected ATS translation response stream-id=0x1 iova=0x10000000 pa=0xa00000 status=success reason=none
APOLLO_SMMU_TBU: architected PRI response stream-id=0x1 iova=0x10000000 status=success reason=none
APOLLO_SMMU_TBU: invalid architectural stream descriptor stream-id=0x1 ste-pa=0xa1c040 ste=0x0 cd-table=0xa1d000
APOLLO_SMMU_TBU: architected fault replay queued stream-id=0x1 reason=stream-descriptor-invalid replay=1 iova=0x10000000
apollo-hexagon-test 1c220000.hexagon: SMMUv3 architectural descriptor probe ok 4-level ttbr=0xa18000 iova=0x10000000 l0=0 l1=0 l2=128 l3=0 desc=0xa00703 pa=0xa00000 levels=4
apollo-hexagon-test 1c220000.hexagon: SMMUv3 stream/context descriptor probe ok stream-id=0x1 ste-base=0xa1c000 ste=0x3 cd-base=0xa1d000 cd=0x1 protocol=0x10001
apollo-hexagon-test 1c220000.hexagon: SMMUv3 negative fault replay ok reason=stream-descriptor-invalid faultq=1 replay=1
apollo-hexagon-test 1c220000.hexagon: SMMUv3 page-table walker/ATS/PRI/fault queue ready features=0x3ff ats=0x20002 pri=1 faultq=1 fault_iova=0x10601000
apollo-hexagon-test 1c220000.hexagon: dynamic SMMU SG map refreshed bytes=131072 segments=8 segment-bytes=16384 count=16
apollo-hexagon-test 1c220000.hexagon: SG DMA stress ok queue=0 fence=1 bytes=131072 segments=8 checksum=0xfda40000 status=0x53474f4b
apollo-hexagon-test 1c220000.hexagon: accelerator tiny cnn ok queue=1 fence=2 status=0x434e4e4f out=42580000,427c0000,42b40000,42c60000
IREE Apollo Hexagon HAL: dynamic C HAL plugin=/opt/qbox/iree/tiny-cnn/lib/libapollo_iree_hexagon_hal_plugin.so name=apollo-hexagon-hal api=1
IREE Apollo Hexagon HAL: upstream executable_plugin export=iree_hal_executable_plugin_query available
IREE Apollo Hexagon HAL: queues=2 command-buffer=fixed fence=async-irq-poll
EXEC @tiny_cnn_graph [apollo-hexagon]
1x1x2x2xf32=[[[54 63][90 99]]]
PASS: QBox guest IREE Hexagon tiny-CNN output matched
```

## Static readiness 결과

```text
SUMMARY {"missing": 5, "pass": 38}
CLASSIFICATION {"architectural_smmuv3_model": "compliance_slice_advanced: current model includes STE/CD fetch, a descriptor-backed 4KB-granule 4-level page-table probe, architected ATS/PRI response accounting, and a negative fault replay suite; full bit-exact ARM SMMUv3 register/protocol coverage remains upstream-scale work"}
```

남은 missing 5개는 host-side IREE/ONNX 개발 도구 부재이다.

- `iree-import-onnx`
- `iree-compile`
- `iree-run-module`
- Python `onnx`
- Python `numpy`

이번 SMMUv3/QBox guest runtime 검증은 staged artifacts와 booted guest smoke로 통과했다.

## 재시도 기록

- `20260510-smmu-stream-context`: invalid STE negative replay가 SystemC `SCP_ERR`
  abort를 유발했다. Expected architectural fault path이므로 TBU fault logs를
  non-fatal warning으로 낮추고 QBox platform을 재빌드했다.
- `20260510-smmu-stream-context-retry1`: SMMUv3 probe는 통과했지만
  `QBOX_IREE_LOGIN_DELAY=9`가 짧아 guest command가 login prompt 전에 입력됐다.
- `20260510-smmu-stream-context-retry2`: `QBOX_IREE_LOGIN_DELAY=24`로 재시도하여
  Hexagon offload와 SMMUv3 marker 전체가 PASS했다. Smoke script 기본 delay도
  같은 값으로 조정했다.
