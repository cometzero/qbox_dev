# QBox IOMMU runtime driver 검증 리포트

- 날짜: 2026-05-17
- 대상: `/build/qbox_dev`
- 목표: Linux device driver 레벨에서 QBox Apollo ARM SMMUv3 경로의 IOMMU
  subsystem/functionality/interface를 runtime으로 검증하고, QBox SystemC
  `APOLLO_SMMU_TBU` data-plane read/write까지 직접 증거로 남긴다.

## 결론

PASS. Linux 커널에 `apollo,iommu-runtime-test` platform driver를 추가하고,
QBox Apollo DTS의 ARM SMMUv3 뒤에 stream-id `0x3` synthetic test device를
붙여 부팅 중 자동 selftest를 수행했다. 보강 후에는 Linux
`dma_map_resource()`/IOMMU API 검증에 그치지 않고, QBox platform에
`apollo_hexagon_dma` -> `apollo_smmu_tbu` endpoint를 추가해 같은 stream-id
`0x3`으로 DMA copy를 발생시켰다.

최종 QBox boot smoke에서 다음을 같은 run에서 확인했다.

- Linux `arm-smmu-v3` probe 및 `1c320000.iommu-runtime-test` IOMMU group attach.
- `iommu-test`의 coherent/streaming/resource DMA translation 검증.
- QBox `APOLLO_HEXAGON_DMA`가 `path=smmu-translated stream-id=0x3`으로 동작.
- QBox `APOLLO_SMMU_TBU`가 stream-id `0x3` read/write IOVA를 PA로 변환.
- Buildroot `/sbin/init` 실행 및 `apollo-qbox login:` prompt 도달.

범위 경계: 이번 결과는 QBox SystemC TBU data-plane까지 포함하는 bounded boot
smoke이다. 다만 SMMUv3 전체 compliance suite나 모든 fault/ATS/PRI corner case를
대체하지는 않는다. 그 범위는 기존 `apollo-hexagon-test`와 별도 SMMUv3 검증
suite가 계속 담당한다.

## 구현 요약

| 영역 | 파일 | 내용 |
| --- | --- | --- |
| Linux driver | `sources/linux/drivers/iommu/iommu-test.c` | IOMMU group/domain, DMA-domain, coherent DMA, streaming DMA, reserved-resource DMA mapping, QBox DMA/TBU MMIO data-plane copy, sysfs rerun/result |
| Linux Kconfig | `sources/linux/drivers/iommu/Kconfig` | `CONFIG_IOMMU_TEST` 추가 |
| Linux build | `sources/linux/drivers/iommu/Makefile` | `iommu-test.o` 빌드 연결 |
| Kernel config | `configs/linux/linux.config` | `CONFIG_IOMMU_TEST=y` 활성화 |
| Device tree | `configs/linux/apollo_soc.dts` | `iommu-runtime-test@1c320000`, `reg`, `iommus = <&smmu 0x3>`, `apollo,smmu-stream-id = <0x3>` 추가 |
| QBox platform | `sources/qbox/platforms/buildroot/conf_aarch64.lua` | stream-id `0x3` 전용 `iommu_test_dma_0` 및 `iommu_test_smmu_tbu_0` 연결 |
| Smoke script | `scripts/run_qbox_iommu_runtime_test.sh` | Linux selftest와 QBox DMA/TBU stream-id `0x3` marker 검사 자동화 |
| Lane contract | `scripts/check_buildroot_arm64_lane.sh` | driver/DTS/QBox config/script marker 정적 검사 |

## 드라이버 검증 내용

`iommu-test` probe는 실패 시 probe를 실패시켜 boot log에 명확한 에러를
남기고, 성공 시 `/sys/devices/platform/1c320000.iommu-runtime-test/result`와
`run`을 제공한다.

검증 항목:

1. `device_iommu_mapped()`와 `iommu_group_get()`으로 test device가 IOMMU
   group에 attach되었는지 확인한다.
2. `iommu_get_domain_for_dev()`와 `iommu_is_dma_domain()`으로 DMA domain을
   확인한다.
3. `dma_alloc_coherent()` 결과 IOVA가 `iommu_iova_to_phys()`로 변환되는지
   확인한다.
4. `dma_map_page()` streaming mapping의 translated PA가 `page_to_phys()`와
   일치하는지 확인한다.
5. DTS `memory-region = <&shared_sram>`의 상단 page에 대해
   `dma_map_resource()`를 수행하고 translated PA가 reserved SRAM PA와
   일치하는지 확인한다.
6. QBox `apollo_smmu_tbu` dynamic map register에 Linux가 받은 IOVA -> SRAM PA
   mapping을 설치한다.
7. QBox `apollo_hexagon_dma` MMIO register를 통해 같은 IOVA page 안의 source를
   destination으로 복사하고, destination payload가 일치하는지 확인한다.
8. sysfs `run` write path는 mutex로 직렬화되어 runtime 재검증을 수행한다.

## Linux device-driver 리뷰

리뷰 결과, 이번 변경 범위에서 수정이 필요한 blocker는 없었다.

- lifetime: driver private state는 `devm_kzalloc()`으로 관리되고 sysfs group도
  `devm_device_add_group()`으로 묶여 remove path에서 별도 해제가 필요 없다.
- concurrency: probe selftest와 sysfs rerun/result 접근은 같은 mutex로 보호한다.
- DMA/IOMMU API: coherent allocation, streaming page mapping, resource mapping은
  각각 정상 unmap/free 경로를 갖고, translation 확인은 mapping lifetime 안에서
  수행한다.
- QBox data-plane: TBU map은 DMA copy 전 설치하고 copy 완료 후 clear하여 다음
  run에 stale mapping을 남기지 않는다.
- OF/resource lifetime: `of_parse_phandle()` 결과는 `of_node_put()`으로 반환한다.
- failure signaling: probe-time failure는 probe 실패와 `dev_err_probe()` 로그로
  표면화하고, runtime rerun 실패는 sysfs write error와 result counter에 남긴다.

## 검증 명령

```bash
bash -n scripts/*.sh

git diff --check

git -C sources/linux diff --check

./scripts/check_buildroot_arm64_lane.sh

cd sources/linux
perl scripts/checkpatch.pl --no-tree -f \
  drivers/iommu/iommu-test.c

cd /build/qbox_dev
./scripts/build_qbox_linux_arm64.sh

configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/post-image.sh \
  build/buildroot-a710/images configs/linux/apollo_soc.dts

./scripts/stage_buildroot_artifacts.sh

./scripts/build_qbox_buildroot_platform.sh

QBOX_IOMMU_RUNTIME_TEST_STAMP=20260517-iommu-test-staged \
QBOX_BOOT_TIMEOUT=20 \
  ./scripts/run_qbox_iommu_runtime_test.sh
```

## 검증 결과

- Shell syntax: `bash -n scripts/*.sh` PASS.
- Diff whitespace: `git diff --check` 및 `git -C sources/linux diff --check` PASS.
- Lane contract: `./scripts/check_buildroot_arm64_lane.sh` PASS.
- checkpatch: `0 errors, 0 warnings, 552 lines checked`.
- Linux build: `build/linux-a710/drivers/iommu/iommu-test.o`
  생성 확인.
- Linux config: `CONFIG_ARM_SMMU_V3=y`, `CONFIG_IOMMU_TEST=y` 확인.
- DTB generation: `build/buildroot-a710/images/apollo_soc.generated.dts`에
  `iommu-runtime-test@1c320000`, `reg = <0x00 0x1c320000 0x00 0x3000>`,
  `iommus = <&smmu 0x3>`, `apollo,smmu-stream-id = <0x3>` 반영 확인.
- Artifact staging: `sources/qbox/platforms/buildroot/fw/Artifacts` 갱신 PASS.
- QBox platform build: `sources/qbox/build` 런타임 생성 PASS.
- QBox runtime smoke: `PASS: QBox IOMMU runtime driver selftest passed`.

## 증거 로그

- QBox smoke log:
  `build/verification/qbox-iommu-runtime-test-20260517-iommu-test-staged.log`
- QBox boot log:
  `build/verification/qbox-iommu-runtime-test-boot-20260517-iommu-test-staged.log`

핵심 runtime marker:

```text
APOLLO_HEXAGON_DMA: path=smmu-translated stream-id=0x3 pasid-valid=1 pasid=0x5 caps=0x7d
APOLLO_SMMU_TBU: stream-id=0x3 translate read iova=0xfffff040 pa=0xbf0040 len=0x20
APOLLO_SMMU_TBU: stream-id=0x3 translate write iova=0xfffff080 pa=0xbf0080 len=0x20
iommu-test 1c320000.iommu-runtime-test: IOMMU runtime selftest ok domain-type=0x3 coherent=0x00000000fffff000->0x000000010082c000 streaming=0x00000000fffff000->0x000000010082c000 dataplane=stream-id=0x3 0x00000000fffff000->0x0000000000bf0000
iommu-test 1c320000.iommu-runtime-test: runtime IOMMU sysfs ready: result, run
Run /sbin/init as init process
apollo-qbox login:
PASS: QBox IOMMU runtime driver selftest passed
```

## 남은 범위

- 이번 smoke는 stream-id `0x3`에 대한 single-page DMA copy data-plane 검증이다.
  긴 scatter-gather, multi-endpoint contention, fault injection, ATS/PRI stress는
  별도 suite로 확장해야 한다.
- Upstream 제출까지 목표로 확장할 경우 `apollo,iommu-runtime-test`에 대한
  devicetree binding 문서화와 selftest/debugfs 성격 정리가 추가로 필요하다.
