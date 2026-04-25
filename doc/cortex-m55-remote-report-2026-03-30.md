# Cortex-M55 remote target build and validation report

Date: 2026-03-30
Workspace root: `/build/qbox_dev`
Repo: `/build/qbox_dev/qbox`
Repo commit: `76669c159b5964ee8bc1dd8409c7e4834235a8f2`
Target: `platforms/cortex-m55-remote`

## Executive summary
I completed the missing environment setup, rebuilt the Cortex-M55 firmware from source, and re-ran the official validation.

Final status:
- Python test dependency fixed: `pexpect 4.9.0` installed for the interpreter used by CTest
- ARM bare-metal compiler acquired locally and used successfully
- Firmware rebuild succeeded
- Official test passed: `ctest -R cortex_m55`
- Direct runtime validation passed with expected UART/interrupt output

## Environment setup performed

### 1) Python dependency for the packaged test
CTests use this interpreter:
- `/home/cometzero/.local/bin/python3.12`

Installed packages:
```bash
/home/cometzero/.local/bin/python3.12 -m pip install --user pexpect
```

Verified:
```bash
/home/cometzero/.local/bin/python3.12 -c 'import pexpect,ptyprocess; print(pexpect.__version__); print(ptyprocess.__version__)'
```
Output:
- `4.9.0`
- `0.7.0`

### 2) ARM compiler acquisition
Passwordless sudo was unavailable, so I installed the toolchain locally by downloading Ubuntu packages and extracting them under the workspace:

Toolchain root:
- `/build/qbox_dev/.tools/arm-none-eabi/root`

Downloaded packages:
- `binutils-arm-none-eabi_2.42-1ubuntu1+23_amd64.deb`
- `gcc-arm-none-eabi_15:13.2.rel1-2_amd64.deb`

Acquisition command:
```bash
mkdir -p /build/qbox_dev/.tools/arm-none-eabi/debs /build/qbox_dev/.tools/arm-none-eabi/root
cd /build/qbox_dev/.tools/arm-none-eabi/debs
apt download gcc-arm-none-eabi binutils-arm-none-eabi
for deb in *.deb; do dpkg-deb -x "$deb" ../root; done
```

Verified versions:
```bash
/build/qbox_dev/.tools/arm-none-eabi/root/usr/bin/arm-none-eabi-gcc --version | head -n 1
/build/qbox_dev/.tools/arm-none-eabi/root/usr/bin/arm-none-eabi-objcopy --version | head -n 1
```
Output:
- `arm-none-eabi-gcc (15:13.2.rel1-2) 13.2.1 20231009`
- `GNU objcopy (2.42-1ubuntu1+23) 2.42`

## Build steps executed

### 1) Host executables
```bash
cmake --build /build/qbox_dev/qbox/build --target cortex-m55-vp remote_cpu --parallel 8
```
Artifacts:
- `/build/qbox_dev/qbox/build/cortex-m55-vp`
- `/build/qbox_dev/qbox/build/remote_cpu`

### 2) Runtime-loaded modules required by the Lua platform
The platform does not run with only the two executables; the Lua-loaded shared modules must also be present in the build root.

Confirmed runtime modules:
- `/build/qbox_dev/qbox/build/char_backend_stdio.so`
- `/build/qbox_dev/qbox/build/gs_memory.so`
- `/build/qbox_dev/qbox/build/keep_alive.so`
- `/build/qbox_dev/qbox/build/uart-pl011.so`
- `/build/qbox_dev/qbox/build/router.so`
- `/build/qbox_dev/qbox/build/pass.so`

### 3) Firmware rebuild from source
```bash
PATH=/build/qbox_dev/.tools/arm-none-eabi/root/usr/bin:$PATH \
make -C /build/qbox_dev/qbox/platforms/cortex-m55-remote/fw/cortex-m55 clean all
```

Result: success

Rebuilt firmware artifacts:
- `/build/qbox_dev/qbox/platforms/cortex-m55-remote/fw/cortex-m55/cortex-m55.bin`
- `/build/qbox_dev/qbox/platforms/cortex-m55-remote/fw/cortex-m55/cortex-m55.elf`

Checksums:
- `368c68659452025a2fc8fbc02c47678aa6b9a563a5c774c4ef9e3d98a86f1bad  platforms/cortex-m55-remote/fw/cortex-m55/cortex-m55.bin`
- `3fa4db176487179cdc64947ce4cf288249dcca0fce1c7024541297c4518ddf38  platforms/cortex-m55-remote/fw/cortex-m55/cortex-m55.elf`

Sizes:
- `cortex-m55.bin`: 965 bytes
- `cortex-m55.elf`: 6452 bytes

## Validation evidence

### 1) Official packaged test
Command:
```bash
ctest --test-dir /build/qbox_dev/qbox/build --output-on-failure -R cortex_m55
```
Result:
- `100% tests passed, 0 tests failed out of 1`

Verbose log saved at:
- `/tmp/cortex_m55_ctest.log`

Key evidence from that run:
- `Test program is running. Listening for interrupts.`
- `IRQ 17 happened`
- `NMI happened`
- `SysTick happened`

### 2) Direct runtime check
Command:
```bash
timeout --signal=SIGQUIT 20s /build/qbox_dev/qbox/build/cortex-m55-vp \
  --gs_luafile /build/qbox_dev/qbox/platforms/cortex-m55-remote/conf.lua \
  > /tmp/cortex_m55_vp.log 2>&1
```

Observed result:
- timeout exit code `124` after intentional termination at 20 seconds
- expected runtime messages were present before termination

Log saved at:
- `/tmp/cortex_m55_vp.log`

Key evidence:
- `Test program is running. Listening for interrupts.`
- `IRQ 17 happened`
- `NMI happened`
- `SysTick happened`
- `Simulation Duration: 19s (Wall Clock)`

## How the target works

### Process topology
- `build/cortex-m55-vp` is the host SystemC process
- `build/remote_cpu` is a separate remote CPU process
- `platforms/cortex-m55-remote/conf.lua` launches the remote CPU through:
  - `plugin_0.exec_path = EXECUTABLE_PATH..formatExecutable("remote_cpu")`
- Host and remote CPU communicate through `RemotePass` RPC/TLM bridging

### Host-side platform wiring
Defined mainly in:
- `platforms/cortex-m55-remote/conf.lua`
- `platforms/cortex-m55-remote/src/main.cc`

Main map:
- RAM at `0x00000000`, size `0x20000`
- Firmware binary loaded from `platforms/cortex-m55-remote/fw/cortex-m55/cortex-m55.bin`
- PL011 UART at `0xC0000000`
- IRQ generator MMIO block at `0xC0001000`

`IrqGenerator` in `src/main.cc` raises signals in this order:
1. IRQ
2. NMI
3. SysTick

### Remote CPU wiring
Defined in:
- `platforms/cortex-m55-remote/src/remote_cpu.cc`
- `platforms/cortex-m55-remote/src/remote_cpu.h`
- `qemu-components/cpu_arm/cpu_arm_cortex_m55/include/cortex-m55.h`

Behavior:
- The remote process constructs a `RemotePass` endpoint named `plugin_pass`
- It instantiates `RemoteCPU`
- `RemoteCPU` wraps a `cpu_arm_cortexM55` plus local router/NVIC connections
- NVIC is configured with `num_irq = 64`
- The CPU model uses the AArch64-backed QEMU integration with Cortex-M55-specific wiring

### Firmware behavior
Defined in:
- `platforms/cortex-m55-remote/fw/cortex-m55/main.c`
- `platforms/cortex-m55-remote/fw/cortex-m55/nvic.c`

Sequence:
1. Enable IRQ 0 and IRQ 17
2. Print `Test program is running. Listening for interrupts.` to UART MMIO `0xC0000000`
3. Write `1` to `0xC000100C` to request host-side interrupt generation
4. Handle and print:
   - `IRQ 17 happened`
   - `NMI happened`
   - `SysTick happened`
5. Clear each source by writing to:
   - `0xC0001000`
   - `0xC0001004`
   - `0xC0001008`

## Important findings
1. The original blockers were environmental, not platform logic defects.
2. `pexpect` was the only reason the packaged `ctest` path failed earlier.
3. The Cortex-M55 firmware can be rebuilt locally without root by extracting Ubuntu cross-toolchain packages into a workspace-local directory.
4. Running this platform requires both executables and the Lua-loaded `.so` modules in the build root.

## Files changed in the repo working tree
The build/rebuild changed firmware-generated artifacts in the repo:
- `platforms/cortex-m55-remote/fw/cortex-m55/cortex-m55.bin`
- `platforms/cortex-m55-remote/fw/cortex-m55/cortex-m55.elf`

No source files were edited.

## Remaining risks
- The local ARM toolchain lives under `/build/qbox_dev/.tools/arm-none-eabi/root` and is not system-wide installed; future shells must prepend that path when rebuilding firmware.
- Direct runtime validation still uses an intentional timeout to stop an otherwise idle firmware loop after confirming the expected interrupt sequence.
