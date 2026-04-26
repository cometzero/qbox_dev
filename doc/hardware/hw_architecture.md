# Apollo SoC / apollo-qbox 하드웨어 아키텍처

> 기준일: 2026-04-25
> 기준 구현: `sources/qbox/platforms/buildroot/conf_aarch64.lua` + `buildroot/external/apollo_qbox/board/apollo/apollo-qbox/apollo_soc.dts`

## 요약

현재 checkout에서 QBox가 플랫폼 구성을 자동으로 Graphviz/DOT/그림 파일로 export하는 사용자용 기능은 확인되지 않았습니다. 대신 현재 QBox Lua 플랫폼과 DTS를 기준으로 draw.io 원본 다이어그램을 작성했습니다.

- draw.io 원본: [`apollo-qbox-hw-architecture.drawio`](./apollo-qbox-hw-architecture.drawio)
- 문서용 SVG export: [`apollo-qbox-hw-architecture.svg`](./apollo-qbox-hw-architecture.svg)
- 1차 부팅 대상: 4 x Cortex-A710, GICv3, PL011 UART0, 4 GiB DRAM, initramfs 기반 Buildroot Linux
- 이후 확장 대상: 2 x Cortex-R52, 1 x Cortex-M55, UART1/2/3, 명시적 SRAM/SystemC TLM device model

## 하드웨어 구성 그림

![Apollo SoC / apollo-qbox hardware architecture](./apollo-qbox-hw-architecture.svg)

> 참고: 위 SVG는 draw.io 원본에서 export한 문서용 그림입니다. 아래 Mermaid는 Markdown에서 빠르게 보기 위한 요약 그림이고, 편집 가능한 원본 그림은 draw.io 파일을 사용하세요.

```mermaid
flowchart LR
    QEMU[QemuInstance\nAARCH64 / TCG MULTI]
    CPU[A710 application cluster\n2 clusters x 2 cores\nMPIDR 0x000,0x001,0x100,0x101]
    GIC[GICv3\nDistributor 0x17A00000\nRedistributors 0x17A60000]
    ROUTER[QBox router\nTLM address decode]
    UART0[PL011 UART0 console\n0x10000000 / 4 KiB\nSPI 379]
    NET[virtio-mmio-net\n0x1C120000 / 64 KiB\nSPI 18]
    GPEX[qemu_gpex PCIe host\nECAM/PIO/MMIO windows\nSPI 541-544]
    DRAM[DRAM gs_memory\n0x80000000-0x17FFFFFFF\n4 GiB]
    LOAD[loader\nbootloader @ 0x80000000\nImage @ 0x81200000\nDTB @ 0x87600000\nrootfs.cpio @ 0x8A800000]
    SRAM[Reserved SRAM in DTB\nA710/R52/M55/shared\nfuture explicit models]
    FUTURE[Future SystemC/TLM devices\nR52, M55, UART1/2/3]

    QEMU --> CPU
    CPU --> ROUTER
    ROUTER --> GIC
    ROUTER --> UART0
    UART0 --> GIC
    ROUTER --> NET
    NET --> GIC
    ROUTER --> GPEX
    GPEX --> GIC
    ROUTER --> DRAM
    LOAD --> DRAM
    SRAM -. reserved now .-> ROUTER
    FUTURE -. planned .-> SRAM
```

## QBox 내장 그림 출력 기능 확인 결과

현재 소스 트리에서 `graphviz`, `.dot`, topology dump/export, hardware diagram exporter 관련 키워드를 검색했지만, 현재 플랫폼 구성을 곧바로 그림으로 뽑는 명령이나 API는 찾지 못했습니다. 확인된 관련 기능은 다음 수준입니다.

- `router`는 TLM 주소 decode 및 address-map 관리를 담당합니다.
- QEMU wrapper 쪽에는 `AddressSpace::update_topology()`처럼 QEMU memory topology 갱신과 관련된 내부 API가 있습니다.
- 문서에는 base/networking/platform 설명이 있으나, 현재 구성을 자동으로 DOT/PNG/SVG로 export하는 사용자용 도구는 확인되지 않았습니다.

따라서 이 문서는 현재 source-of-truth 파일에서 주소/연결 정보를 추출해 수동으로 정리한 아키텍처 문서입니다.

## Source of truth

| 항목 | 파일 |
| --- | --- |
| QBox 플랫폼 구성 | `sources/qbox/platforms/buildroot/conf_aarch64.lua` |
| Linux device tree | `buildroot/external/apollo_qbox/board/apollo/apollo-qbox/apollo_soc.dts` |
| 편집 가능한 하드웨어 그림 | `doc/hardware/apollo-qbox-hw-architecture.drawio` |
| 커널 artifact load path | `sources/qbox/platforms/buildroot/fw/Artifacts/Image.bin` |
| DTB artifact load path | `sources/qbox/platforms/buildroot/fw/Artifacts/apollo_soc.dtb` |
| initramfs artifact load path | `sources/qbox/platforms/buildroot/fw/Artifacts/rootfs.cpio` |

## 현재 모델링 범위

### 구현됨: 1차 Linux 부팅 경로

| 구성 | 현재 상태 | 근거 |
| --- | --- | --- |
| Cortex-A710 CPU | 4 cores, 2 clusters x 2 cores | Lua `ARM_NUM_CPUS = 4`, DTS `cpu-map` |
| Cluster 0 | CPU0 MPIDR `0x000`, CPU1 MPIDR `0x001` | Lua `mp_affinity`, DTS `cpu@0`, `cpu@1` |
| Cluster 1 | CPU2 MPIDR `0x100`, CPU3 MPIDR `0x101` | Lua `mp_affinity`, DTS `cpu@100`, `cpu@101` |
| Boot CPU | CPU0만 reset 시 powered-on | Lua `start_powered_off` override |
| Interrupt controller | GICv3 | Lua `arm_gicv3`, DTS `arm,gic-v3` |
| Console UART | PL011 UART0 | Lua `Pl011`, DTS `serial@10000000` |
| DRAM | 4 GiB @ `0x80000000` | Lua `ram_0`, DTS `memory@80000000` |
| Root filesystem | `rootfs.cpio` initramfs | Lua loader + DTS `linux,initrd-*` |
| Network | `virtio_mmio_net` with user-mode host forwards | Lua `virtionet0_0` |
| PCIe host | `qemu_gpex` | Lua `gpex_0` |

### 예약/향후 확장 범위

| 구성 | 현재 상태 | 향후 작업 |
| --- | --- | --- |
| Cortex-R52 x 2 | 아직 CPU model 미연결 | Zephyr RTOS용 remote/core model 추가 |
| Cortex-M55 x 1 | 아직 CPU model 미연결 | Zephyr RTOS용 M-profile model 추가 |
| UART1/2/3 | 아직 미연결 | R52용 2개, M55용 1개 PL011 또는 대체 UART 추가 |
| SRAM 8 MiB | DTS `reserved-memory`로 예약됨 | QBox `gs_memory` 또는 SystemC memory/device로 명시 모델링 |
| SystemC 기반 device | 아직 미연결 | router address window와 IRQ line을 추가하고 DTS 갱신 |

## 메모리 맵

### Low address / SRAM / MMIO

| 영역 | 시작 | 끝 | 크기 | 현재 모델 | 비고 |
| --- | ---: | ---: | ---: | --- | --- |
| Fallback low memory catch-all | `0x00000000` | `0x7FFFFFFFF` | 32 GiB | `fallback_0` (`gs_memory`) | priority 1, `dmi_allow=false`; 명시적 mapping 뒤의 broad fallback window입니다. DRAM/MMIO와 주소가 겹칠 수 있으므로 실제 device model 대체물이 아닙니다. |
| A710 SRAM reserved | `0x00400000` | `0x004FFFFF` | 1 MiB | DTS `reserved-memory` | A710용 예약 SRAM |
| R52 SRAM0 reserved | `0x00500000` | `0x006FFFFF` | 2 MiB | DTS `reserved-memory` | R52 core 0용 예정 |
| R52 SRAM1 reserved | `0x00700000` | `0x008FFFFF` | 2 MiB | DTS `reserved-memory` | R52 core 1용 예정 |
| M55 SRAM reserved | `0x00900000` | `0x009FFFFF` | 1 MiB | DTS `reserved-memory` | M55용 예정 |
| Shared SRAM reserved | `0x00A00000` | `0x00BFFFFF` | 2 MiB | DTS `reserved-memory` | Heterogeneous cores 공유용 예정 |
| PL011 UART0 | `0x10000000` | `0x10000FFF` | 4 KiB | QBox `Pl011` + DTS `serial@10000000` | Console, GIC SPI 379 |
| GIC Distributor | `0x17A00000` | `0x17A0FFFF` | 64 KiB | DTS `intc`; QBox `dist_iface` | QBox interface window는 `0x17A00000`-`0x17A5FFFF` |
| GIC Redistributors | `0x17A60000` | `0x17ADFFFF` | 512 KiB | DTS `intc`; QBox `redist_iface_0` | QBox interface window는 `0x17A60000`-`0x17C1FFFF` |
| virtio-mmio-net | `0x1C120000` | `0x1C12FFFF` | 64 KiB | QBox `virtio_mmio_net` | GIC SPI 18 |
| PCIe ECAM | `0x43B50000` | `0x53B4FFFF` | 256 MiB | QBox `qemu_gpex.ecam_iface` | PCI config space |
| PCIe PIO | `0x60200000` | `0x602FFFFF` | 1 MiB | QBox `qemu_gpex.pio_iface` | Programmed I/O window |
| PCIe MMIO | `0x60300000` | `0x7FFFFFFF` | 509 MiB | QBox `qemu_gpex.mmio_iface` | 32-bit MMIO window |

### DRAM / boot artifact layout

| 영역 | 시작 | 끝/주소 | 크기 | 현재 모델 | 비고 |
| --- | ---: | ---: | ---: | --- | --- |
| DRAM | `0x80000000` | `0x17FFFFFFF` | 4 GiB | QBox `ram_0`, DTS `memory@80000000` | Linux main memory |
| Bootloader data | `0x80000000` | fixed load address | - | QBox `loader` | `_bootloader_aarch64` |
| Linux Image | `0x81200000` | fixed load address | artifact-dependent | QBox `loader` | `Image.bin` |
| Device tree blob | `0x87600000` | fixed load address | artifact-dependent | QBox `loader` | `apollo_soc.dtb` |
| Initramfs rootfs | `0x8A800000` | generated in DTB | artifact-dependent | QBox `loader`, DTS `linux,initrd-*` | `rootfs.cpio`; end address는 rootfs 크기로 post-image 단계에서 생성 |
| PCIe high MMIO | `0x400000000` | `0x5FFFFFFFF` | 8 GiB | QBox `qemu_gpex.mmio_iface_high` | 64-bit PCIe MMIO window |

## Interrupt map

| Source | IRQ line | 연결 |
| --- | --- | --- |
| ARM generic timer virtual | PPI 27 | `gic_0.ppi_in_cpu_<n>_27` |
| ARM generic timer secure EL1 | PPI 29 | `gic_0.ppi_in_cpu_<n>_29` |
| ARM generic timer non-secure EL1 | PPI 30 | `gic_0.ppi_in_cpu_<n>_30` |
| ARM generic timer non-secure EL2 | PPI 26 | `gic_0.ppi_in_cpu_<n>_26` |
| GICv3 maintenance | PPI 25 | `gic_0.ppi_in_cpu_<n>_25` |
| PMU | PPI 23 / DTS PPI 7 | Lua PMU output + DTS `arm,armv8-pmuv3` |
| PL011 UART0 | SPI 379 | `pl011_uart_0.irq -> gic_0.spi_in_379` |
| virtio-mmio-net | SPI 18 | `virtionet0_0.irq_out -> gic_0.spi_in_18` |
| qemu_gpex | SPI 541-544 | `gpex_0.irq_out_0..3 -> gic_0.spi_in_541..544` |

## 부팅 관점의 연결 흐름

1. `QemuInstance`가 AARCH64 QEMU backend를 생성합니다.
2. 4개 Cortex-A710 CPU가 `router.target_socket`을 통해 시스템 주소 공간에 접근합니다.
3. `loader`가 bootloader, kernel, DTB, rootfs.cpio를 DRAM의 고정 주소에 배치합니다.
4. CPU0이 `rvbar = 0x80000000`에서 부팅을 시작합니다.
5. Linux는 DTB의 `console=ttyAMA0 earlycon=pl011,0x10000000` 설정으로 UART0에 로그를 출력합니다.
6. initramfs는 DTS의 `linux,initrd-start/end`로 전달되며, Buildroot post-image 단계에서 end address가 rootfs 크기에 맞게 채워집니다.

## 주의 사항

- `fallback_0`는 `0x0`부터 32 GiB까지 넓게 잡힌 fallback memory입니다. 현재 1차 부팅을 단순화하기 위한 안전망이며 DRAM/MMIO와 주소 범위가 겹칠 수 있습니다. R52/M55/SystemC device를 실제로 추가할 때는 해당 주소 window를 명시적인 memory/device model로 라우팅하도록 정리해야 합니다.
- DTS의 SRAM 영역은 Linux가 사용하지 않도록 `no-map`으로 예약한 상태입니다. 아직 QBox Lua 쪽에서 SRAM별 `gs_memory` 또는 SystemC TLM target으로 분리 모델링되지는 않았습니다.
- DTS의 GIC reg 크기와 QBox `arm_gicv3` interface window 크기는 표현 단위가 다릅니다. Linux에 노출되는 DTB reg와 QBox internal interface mapping을 구분해서 봐야 합니다.
- 이 문서는 현재 1차 목표인 A710 Linux/Buildroot 부팅 경로 기준입니다. R52/M55/추가 UART/디바이스 모델이 들어가면 draw.io와 메모리 맵을 함께 갱신해야 합니다.
