# QBox SMMUv3 SMMU-COMP-090 verification — 2026-05-10

## Scope

SMMU-COMP-090 remains a functional slice. The repository still does **not**
claim that Apollo Hexagon is merged into the upstream IREE source tree. This
slice removes the guest smoke dependency on invoking the legacy
`apollo-iree-hexagon-runner` directly and adds a repo-local, upstream-style HAL
registry dispatch path:

- `iree-run-module --device=apollo-hexagon` is staged as the guest entry point.
- The `iree-run-module` wrapper dispatches Apollo device requests to
  `apollo-iree-run-module` and forwards non-Apollo devices to the extracted
  upstream IREE runtime binary at `iree-run-module.real`.
- `apollo-iree-run-module` discovers `apollo-hexagon` through
  `apollo_iree_hal_registry_lookup()` and submits via the Apollo HAL queue API.
- CPU fallback names such as `local-task` are rejected for Apollo execution
  proof.
- The existing `iree_hal_executable_plugin_query` export remains staged as
  compatibility evidence, not as a full upstream HAL registry claim.

Open blockers:

- No upstream IREE source tree is present in this workspace, so this slice does
  not modify IREE's native HAL driver registry or CMake/Bazel build.
- Upstream IREE tests for a first-class `apollo-hexagon` HAL device are still
  pending.
- The repo-local wrapper is a compatibility bridge; it is not a substitute for
  an upstreamable IREE HAL backend review.

## Changed files

- `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hal_registry.c`
- `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hal_registry.h`
- `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_run_module.c`
- `scripts/build_apollo_hexagon_guest_tools.sh`
- `scripts/stage_iree_tiny_cnn_guest_artifacts.sh`
- `scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh`
- `scripts/check_iree_cnn_pipeline_readiness.py`
- `scripts/check_qbox_smmuv3_compliance.py`
- `scripts/check_buildroot_arm64_lane.sh`
- `doc/spec/qbox-smmuv3-compliance-checklist.md`

## Validation evidence

### Guest tool build

```bash
./scripts/build_apollo_hexagon_guest_tools.sh \
  2>&1 | tee build/verification/apollo-iree-hal-registry-build-20260510.log
```

Result:

- `build/verification/apollo-iree-hal-registry-build-20260510.log` records
  AArch64 `apollo-iree-run-module`, legacy runner, dynamic plugin, and x86-64
  host negative-test binary builds.

### Negative registry tests

```bash
build/apollo-hexagon-guest-tools/host-bin/apollo-iree-run-module \
  --device=unknown \
  --module=build/verification/iree-tiny-cnn-host/tiny_cnn_aarch64.vmfb \
  --function=tiny_cnn_graph
build/apollo-hexagon-guest-tools/host-bin/apollo-iree-run-module \
  --device=local-task \
  --module=build/verification/iree-tiny-cnn-host/tiny_cnn_aarch64.vmfb \
  --function=tiny_cnn_graph
build/apollo-hexagon-guest-tools/host-bin/apollo-iree-run-module \
  --device=apollo-hexagon \
  --module=build/verification/iree-tiny-cnn-host/tiny_cnn_aarch64.vmfb \
  --function=wrong_entry
```

Result:

- `build/verification/apollo-iree-hal-registry-negative-20260510.log`:
  rejected unknown device, CPU fallback, and incompatible function entry.

### Guest artifact staging

```bash
./scripts/stage_iree_tiny_cnn_guest_artifacts.sh \
  2>&1 | tee build/verification/stage-iree-hal-registry-20260510.log
```

Result:

- `build/verification/stage-iree-hal-registry-20260510.log` records staged
  `bin/iree-run-module`, `bin/iree-run-module.real`, and
  `bin/apollo-iree-run-module`.
- Target rootfs contains the registry wrapper under
  `/opt/qbox/iree/tiny-cnn/bin/iree-run-module`.

### Rootfs, artifacts, and platform build

```bash
QBOX_IREE_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/tiny-cnn \
./scripts/build_qbox_buildroot_arm64.sh \
  2>&1 | tee build/verification/buildroot-iree-hal-registry-20260510.log
./scripts/stage_buildroot_artifacts.sh \
  2>&1 | tee build/verification/stage-buildroot-artifacts-iree-hal-registry-20260510.log
./scripts/build_qbox_buildroot_platform.sh \
  2>&1 | tee build/verification/qbox-platform-iree-hal-registry-20260510.log
```

Result:

- Buildroot regenerated `rootfs.cpio` and DTB with the new guest tools.
- Staging refreshed QBox `Image.bin`, DTB, `rootfs.cpio`, and Hexagon firmware.
- Platform build completed with `QBox Buildroot platform runtime built in
  /build/qbox_dev/sources/qbox/build`.

### Guest IREE Hexagon registry smoke

```bash
QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260510-smmu-comp-090-hal-registry-fixed \
QBOX_BOOT_TIMEOUT=80 \
QBOX_IREE_LOGIN_DELAY=24 \
QBOX_IREE_AFTER_COMMAND_DELAY=25 \
./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh \
  2>&1 | tee build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-090-hal-registry-fixed.driver.log
```

Result:

- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-090-hal-registry-fixed.driver.log`:
  `PASS: QBox guest IREE Hexagon tiny-CNN output matched`.
- Runtime log includes
  `IREE Apollo Hexagon HAL: upstream-style HAL registry device=apollo-hexagon driver=apollo-hexagon-hal-registry`.
- Output matched `1x1x2x2xf32=[[[54 63][90 99]]]`.
- Combined log:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-090-hal-registry-fixed.log`.
- Boot log:
  `build/verification/qbox-iree-tiny-cnn-hexagon-guest-boot-20260510-smmu-comp-090-hal-registry-fixed.log`.

## Claim boundary

This is an upstream-style registry dispatch slice in the QBox guest artifact
lane. It proves that the default guest command can use
`iree-run-module --device=apollo-hexagon` without directly invoking the legacy
runner and without counting CPU fallback. It does not claim a completed
upstream IREE HAL backend merge.

### Static checker and lane validation

```bash
rm -rf scripts/__pycache__
{
  bash -n scripts/*.sh
  python3 -m py_compile \
    scripts/check_qbox_smmuv3_compliance.py \
    scripts/check_iree_cnn_pipeline_readiness.py \
    scripts/qbox_pty_runner.py
  scripts/check_qbox_smmuv3_compliance.py \
    --self-test-negative \
    --json build/verification/qbox-smmuv3-compliance-hal-registry-final-20260510.json
  scripts/check_iree_cnn_pipeline_readiness.py \
    --json build/verification/iree-cnn-readiness-smmu-comp-090-hal-registry-20260510.json
  git diff --check
  git -C sources/qbox diff --check
  git -C sources/linux diff --check
} 2>&1 | tee build/verification/smmu-comp-090-hal-registry-static-final-20260510.log
rm -rf scripts/__pycache__
./scripts/check_buildroot_arm64_lane.sh \
  2>&1 | tee build/verification/check-buildroot-arm64-lane-smmu-comp-090-20260510.log
```

Result:

- `build/verification/smmu-comp-090-hal-registry-static-final-20260510.log`:
  `SUMMARY {"pass": 101}` for the SMMUv3 checker and no diff whitespace
  errors.
- `build/verification/qbox-smmuv3-compliance-hal-registry-final-20260510.json`:
  includes `iree:hal-registry-dispatch` with `status: pass`.
- `build/verification/iree-cnn-readiness-smmu-comp-090-hal-registry-20260510.json`:
  records `repo_iree_hexagon_hal_registry` as `pass`; host tools are still
  optional and reported separately when not on PATH.
- `build/verification/check-buildroot-arm64-lane-smmu-comp-090-20260510.log`:
  passed all lane contract checks, including the new HAL registry source,
  staging, dispatch, and CPU fallback rejection contracts.

## Final readiness validation

After the registry dispatch and guest-smoke validation, the IREE CNN readiness
checker was rerun with the IREE smoke virtualenv on `PATH` and
`--require-host-tools` enabled.

Command:

```bash
PATH=/build/qbox_dev/build/iree-smoke-venv/bin:$PATH \
/build/qbox_dev/build/iree-smoke-venv/bin/python \
  scripts/check_iree_cnn_pipeline_readiness.py \
  --require-host-tools \
  --json build/verification/iree-cnn-readiness-smmu-comp-090-hal-registry-final-20260510.json \
  2>&1 | tee build/verification/iree-cnn-readiness-smmu-comp-090-hal-registry-final-20260510.log
```

Result:

- `SUMMARY {"pass": 44}`.
- `repo_iree_hexagon_hal_registry`: PASS.
- `iree_import_onnx_tool`, `iree_compile_tool`, and `iree_run_module_tool`:
  PASS from `/build/qbox_dev/build/iree-smoke-venv/bin`.
- `python_onnx` and `python_numpy`: PASS.
