# Apollo Hexagon Direct BO TBU 리뷰 반영 검증

날짜: 2026-05-21
작업공간: `/build/qbox_dev`
브랜치: `feature/qbox_dev`

## 반영 범위

- Linux Apollo Hexagon `CMD_SUBMIT` bound dispatch에서 input/output tensor BO를
  shared-window copy shim으로 옮기지 않고, active dispatch 동안 original BO IOVA로
  Apollo TBU에 직접 매핑한다.
- command BO packet 자체는 기존처럼 shared CMDQ window에 stage한다. 이번 변경은
  tensor BO data path에 한정하며, complete per-context address space와 command ring
  scheduler 완료로 주장하지 않는다.
- `apollo_hexagon_bo_map_tbu()`는 GEM SHMEM sg_table을 순회해 page-aligned TBU entry를
  추가하고, completion 후 output BO를 CPU로 sync한 뒤 TBU entry를 제거한다.
- smoke/checker 계약은 `command BO TBU map`, `uses BO IOVA`, `output ready`,
  `direct-tbu=yes` marker를 요구하도록 갱신했다.

## 검증 결과

| 명령 | 결과 |
| --- | --- |
| `git -C sources/linux diff --check` | PASS |
| `git diff --check` | PASS |
| `python3 -m py_compile scripts/check_iree_cnn_pipeline_readiness.py scripts/check_apko_vmfb_verification_lane.py` | PASS |
| `bash -n scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh scripts/run_iree_apko_cnn_hexagon_qbox_guest_smoke.sh scripts/run_iree_apko_mnist_hexagon_qbox_guest_smoke.sh scripts/run_iree_apko_vadd_vmfb_hexagon_qbox_guest_smoke.sh scripts/run_iree_apko_cnn_vmfb_hexagon_qbox_guest_smoke.sh scripts/check_buildroot_arm64_lane.sh` | PASS |
| `./scripts/check_buildroot_arm64_lane.sh` | PASS |
| `python3 scripts/check_iree_cnn_pipeline_readiness.py --repo . --json build/verification/iree-readiness-direct-bo-tbu-20260521.json` | PASS, `SUMMARY {"pass": 70}` |
| `python3 scripts/check_apko_vmfb_verification_lane.py --repo . --json build/verification/apko-vmfb-lane-direct-bo-tbu-20260521.json` | PASS, `SUMMARY {"pass": 15}` |
| `./scripts/build_qbox_linux_arm64.sh` | PASS, `Image` rebuilt under `build/linux-a710/arch/arm64/boot/Image` |
| `./scripts/stage_buildroot_artifacts.sh` | PASS |
| `python3 scripts/check_qbox_smmuv3_compliance.py --repo .` | PASS, `SUMMARY {"pass": 1063}` |
| `QBOX_BOOT_TIMEOUT=80 QBOX_APKO_VADD_HEXAGON_GUEST_SMOKE_STAMP=20260521-direct-bo-tbu ./scripts/run_iree_apko_vadd_hexagon_qbox_guest_smoke.sh` | PASS |

## Runtime Evidence

주요 로그:

- `build/verification/qbox-iree-apko-vadd-hexagon-guest-20260521-direct-bo-tbu.log`
- `build/verification/qbox-iree-apko-vadd-hexagon-guest-boot-20260521-direct-bo-tbu.log`
- `build/verification/iree-readiness-direct-bo-tbu-20260521.json`
- `build/verification/apko-vmfb-lane-direct-bo-tbu-20260521.json`

확인 marker:

```text
command BO bound VADD dispatch ctx=1 input=0x10300000 output=0x10301000 bytes=32/16 direct-tbu=yes
command BO TBU map iova=0x10300000 object-offset=0x0 bytes=32 mapped-bytes=0x1000 segments=1
command BO TBU map iova=0x10301000 object-offset=0x0 bytes=16 mapped-bytes=0x1000 segments=1
command BO bound VADD dispatch uses BO IOVA input=0x10300000 output=0x10301000
command BO bound VADD output ready ctx=1 output=0x10301000 bytes=16 direct-tbu=yes
IREE Apollo Hexagon HAL: APKO CMD_SUBMIT VADD ok
4xf32=11 22 33 44
```

## 남은 Blocker

- command packet은 아직 shared CMDQ window에 stage한다. command BO/ring scheduler와
  per-context address-space ownership은 다음 driver slice다.
- TBU map table exhaustion, overlapping binding 정책, dma-buf import/export,
  persistent BO map lifecycle은 아직 제품화 정책으로 정리되지 않았다.
- APKO `CODE` program은 2-word transition ABI다. full nontrivial APKO instruction
  execution 또는 실제 Hexagon binary execution은 아직 미완료다.
- VMFB trailer는 repo-local transition packaging이다. upstream IREE HAL executable
  section packaging 완료로 주장하지 않는다.
