# Apollo Hexagon SMMU Reference Execution Report

Date: 2026-04-26
Scope: execute the follow-up plan from
`sources/qbox/tests/qbox/cpu/hexagon/HEXAGON_SMMU_README.md` against the
current Apollo/QBox implementation.

## Result

Status: **PASS with scope boundary**

- The QBox upstream-style `hexagon-smmu-stress-test-v2` reference target is now
  buildable on this Linux host with open-source LLVM tools.
- All listed Hexagon SMMU reference CTest variants pass: **9/9**.
- Apollo Buildroot boot regression still reaches the login prompt and proves:
  - QBox Hexagon firmware-triggered DMA smoke path,
  - Linux-visible SMMUv3 probe,
  - `apollo-hexagon-test` IOMMU group attach,
  - Linux driver verification of the firmware DMA destination pattern.
- Scope boundary: the Apollo SoC runtime path still uses the existing
  `apollo_hexagon_dma` SystemC/TLM DMA smoke path. The QBox reference stress
  tester is a separate CPU test bench and is not yet wired as Apollo's runtime
  production Hexagon/SMMU driver ABI.

## What Changed

### Root workspace

- Added `scripts/check_qbox_hexagon_smmu_reference.sh`.
  - Builds the reference firmware with `llvm-mc -arch=hexagon
    -mcpu=hexagonv68`, `ld.lld`, and `llvm-objcopy`.
  - Emits a durable status line such as `STATUS buildable_with_llvm`.
- Updated `scripts/check_buildroot_arm64_lane.sh`.
  - Adds the new preflight script to the lane contract.
  - Adds checks that the Hexagon SMMU reference path uses v68 and documents it.

### QBox submodule

- Updated `sources/qbox/tests/qbox/cpu/hexagon/CMakeLists.txt`.
  - Added `HEXAGON_SMMU_MCPU=hexagonv68`.
  - Uses `-mcpu=${HEXAGON_SMMU_MCPU}` for both configure-time probe and real
    firmware assembly.
  - Keeps explicit configure diagnostics if the host toolchain cannot assemble
    the v68 firmware.
- Updated `sources/qbox/tests/qbox/cpu/hexagon/HEXAGON_SMMU_README.md`.
  - Corrected the practical minimum from v67 to v68.
  - Added the LLVM `llvm-mc -mcpu=hexagonv68` flow.
- Cleaned `sources/qbox/tests/qbox/cpu/hexagon/hexagon_smmu_stress_test_v2.cc`.
  - Removed an unused direct Keystone include.

## Key Findings

- `llvm-mc -arch=hexagon -mcpu=hexagonv67` fails on this firmware because
  `dmwait` and `dmlink` are not accepted for v67.
- `llvm-mc -arch=hexagon -mcpu=hexagonv68` assembles successfully, and the
  resulting firmware binary is 30,720 bytes.
- The earlier configure-time skip was caused by assembling with generic
  `-arch=hexagon` instead of selecting v68.

## Verification Evidence

### Firmware/toolchain preflight

Command:

```bash
./scripts/check_qbox_hexagon_smmu_reference.sh
```

Evidence:

- Log: `build/verification/hexagon-smmu-reference-preflight-2026-04-26-234321.log`
- Result: `STATUS buildable_with_llvm`
- Binary: `build/verification/hexagon-smmu-reference/hexagon_smmu_firmware.bin`
  `(30720 bytes)`

### QBox platform build

Command:

```bash
./scripts/build_qbox_buildroot_platform.sh
```

Evidence:

- Log: `build/verification/qbox-platform-hexagon-smmu-reference-2026-04-26-234332.log`
- Result: `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`
- Confirmed local libqemu source: `/build/qbox_dev/sources/qemu`
- Confirmed libqemu targets: `aarch64;hexagon`

### Hexagon SMMU reference build and tests

Commands:

```bash
cmake --build --preset gcc --target hexagon-smmu-stress-test-v2 --parallel
ctest --test-dir build -R '^hexagon-smmu-stress-test-v2' --output-on-failure
```

Evidence:

- Build log:
  `build/verification/qbox-rebuild-hexagon-smmu-after-cleanup-2026-04-26-234809.log`
- Test log:
  `build/verification/qbox-rerun-hexagon-smmu-after-cleanup-2026-04-26-234809.log`
- Result: `100% tests passed, 0 tests failed out of 9`
- Total CTest time: `30.83 sec`

### Apollo boot regression

Command:

```bash
QBOX_BOOT_TIMEOUT=60 \
QBOX_BOOT_LOG=build/verification/qbox-boot-hexagon-smmu-reference-2026-04-26-234619.log \
./scripts/run_qbox_buildroot_boot.sh
```

Evidence:

- Boot log: `build/verification/qbox-boot-hexagon-smmu-reference-2026-04-26-234619.log`
- Return code: `124` because the bounded smoke run intentionally stops QBox at
  the 60-second timeout after reaching login.
- Required boot markers observed:
  - `APOLLO_HEXAGON_DMA: firmware requested DMA src=0xc01000 dst=0xa00000 len=0x20`
  - `APOLLO_HEXAGON_DMA: DMA copy complete src=0xc01000 dst=0xa00000 len=0x20 first=0x48455831`
  - `APOLLO_HEXAGON_DMA: firmware done magic=0x48455844`
  - `arm-smmu-v3 1c200000.iommu: oas 44-bit (features 0x01008305)`
  - `apollo-hexagon-test 1c220000.hexagon: iommu group attached`
  - `apollo-hexagon-test 1c220000.hexagon: firmware dma traffic ok dst=0x0000000000a00000 words=8 first=0x48455831`
  - `apollo-hexagon-test 1c220000.hexagon: dma selftest ok dma=0x0000fffffffff000 size=4096`
  - `apollo-hexagon-test 1c220000.hexagon: probe ok`
  - `Run /sbin/init as init process`
  - `apollo-qbox login:`

### Static/contract checks

Command:

```bash
bash -n scripts/*.sh
python3 -m py_compile scripts/qbox_pty_runner.py
./scripts/check_buildroot_arm64_lane.sh
git diff --check
git -C sources/qbox diff --check
```

Evidence:

- Log: `build/verification/static-final-hexagon-smmu-reference-2026-04-26-234908.log`
- Result: all commands completed successfully.

## Remaining Work

1. Decide whether the QBox `hexagon-smmu-stress-test-v2` tester architecture
   should be embedded into the Apollo platform runtime or kept as an upstream
   regression-only test.
2. If embedding, define an Apollo production ABI for Hexagon reset/power,
   mailbox/doorbell, StreamID ownership, and Linux driver control.
3. Extend `apollo_hexagon_dma` or add a new SystemC DMA master so traffic can be
   forced through an SMMUv3 translated stream, not only through the existing
   direct TLM smoke path.
4. Add negative tests for SMMU faults, invalid StreamIDs, and translation
   permission failures after the translated DMA path exists.
