# QBox SMMUv3 IREE dynamic HAL registry verification (2026-05-11)

## Scope

SMMU-COMP-090 dynamic C HAL plugin registry functional slice.

This slice keeps the claim boundary as a QBox repo-local, upstream-style IREE
HAL registry bridge. It does **not** claim that the Apollo Hexagon HAL backend
has been merged into upstream IREE source. The implemented path now makes the
normal guest `iree-run-module --device=apollo-hexagon` flow dynamically load and
register the staged Apollo Hexagon C HAL plugin before dispatching work to the
Apollo Hexagon queues.

Validated behavior:

- `run_tiny_cnn_hexagon_guest.sh` passes `--executable_plugin` pointing at the
  staged `libapollo_iree_hexagon_hal_plugin.so`.
- `apollo_iree_hal_registry_lookup()` rejects CPU fallback device names and uses
  `dlopen()`/`dlsym()` to resolve the Apollo C HAL plugin query export.
- `apollo-iree-run-module` logs the dynamic plugin path, driver name, and ABI
  version before queue submission.
- Negative host checks fail closed for CPU fallback and missing plugin paths.
- The QBox guest tiny-CNN smoke reaches the dynamic registry marker, completes
  queue 0/1 offloads, and produces the expected tensor output.

Open blocker for full SMMU-COMP-090 completion:

- A true upstream IREE source tree integration is still pending: native HAL
  driver registry entry, upstream build-system integration, and upstream HAL
  tests are not present in this workspace.

## Changed implementation

- `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hal_registry.h`
  - Added `plugin_path` to the registered device descriptor.
  - Extended registry lookup to receive an executable plugin path and return
    structured errors.
- `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_hal_registry.c`
  - Added dynamic plugin loading through `dlopen(plugin_path, RTLD_NOW |
    RTLD_LOCAL)`.
  - Resolved `APOLLO_IREE_HEXAGON_PLUGIN_EXPORT_NAME` through `dlsym()` and
    validated queue operation hooks before registration.
  - Preserved CPU fallback rejection for Apollo proof runs.
- `configs/buildroot/external/apollo_qbox/board/apollo/apollo-qbox/guest-tools/apollo_iree_run_module.c`
  - Added `--executable_plugin`/`--plugin` parsing.
  - Loaded VMFB metadata first, then dynamically registered the staged plugin.
  - Logged `dynamically registered C HAL plugin=` with driver and ABI version.
- `scripts/build_apollo_hexagon_guest_tools.sh`
  - Linked the AArch64 and host registry frontend with `-ldl`.
- `scripts/stage_iree_tiny_cnn_guest_artifacts.sh`
  - Staged the generated Hexagon guest command with `--executable_plugin`.
- `scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh`
  - Added dynamic plugin registration markers to the required smoke log checks.
- `scripts/check_buildroot_arm64_lane.sh`
  - Added lane contract checks for the dynamic plugin loading path.
- `scripts/check_qbox_smmuv3_compliance.py`
  - Extended `iree:hal-registry-dispatch` with dynamic C HAL plugin evidence.
- `scripts/check_iree_cnn_pipeline_readiness.py`
  - Updated readiness classification for the repo-local dynamic registry slice.
- `doc/spec/qbox-smmuv3-compliance-checklist.md`
  - Updated SMMU-COMP-090 source/runtime evidence and claim boundary.
- `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`
  - Added this progress note and preserved the upstream IREE blocker.

## Verification evidence

| Evidence | Command | Result |
| --- | --- | --- |
| Shell syntax | `bash -n scripts/build_apollo_hexagon_guest_tools.sh scripts/stage_iree_tiny_cnn_guest_artifacts.sh scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh scripts/check_buildroot_arm64_lane.sh` | Pass; see `build/verification/smmu-iree-dynamic-registry-bashn-20260511.log`. |
| Python syntax | `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py scripts/check_iree_cnn_pipeline_readiness.py` | Pass; see `build/verification/smmu-iree-dynamic-registry-pycompile-20260511.log`. |
| Guest tool build | `./scripts/build_apollo_hexagon_guest_tools.sh` | Pass; built AArch64 `apollo-iree-run-module`, AArch64 `libapollo_iree_hexagon_hal_plugin.so`, and host `apollo-iree-run-module`. See `build/verification/smmu-iree-dynamic-registry-tools-build-20260511.log`. |
| Negative CPU fallback | `build/apollo-hexagon-guest-tools/host-bin/apollo-iree-run-module --device=local-task --metadata build/iree-guest-artifacts/tiny-cnn/apollo_hexagon.vmfb.meta` | Expected failure; `CPU fallback device is disabled for Apollo proof: local-task`. See `build/verification/smmu-iree-dynamic-registry-negative-cpu-20260511.log` and summary log. |
| Negative missing plugin | `build/apollo-hexagon-guest-tools/host-bin/apollo-iree-run-module --device=apollo-hexagon --metadata build/iree-guest-artifacts/tiny-cnn/apollo_hexagon.vmfb.meta --executable_plugin /no/such/plugin.so` | Expected failure; `failed to dlopen Apollo HAL plugin /no/such/plugin.so`. See `build/verification/smmu-iree-dynamic-registry-negative-missing-plugin-20260511.log` and summary log. |
| Guest IREE artifact staging | `./scripts/stage_iree_tiny_cnn_guest_artifacts.sh` | Pass; staged `bin/apollo-iree-run-module`, `bin/iree-run-module`, and `lib/libapollo_iree_hexagon_hal_plugin.so`. See `build/verification/smmu-iree-dynamic-registry-stage-iree-20260511.log`. |
| Buildroot rootfs rebuild | `QBOX_IREE_GUEST_ARTIFACTS_DIR=/build/qbox_dev/build/iree-guest-artifacts/tiny-cnn ./scripts/build_qbox_buildroot_arm64.sh` | Pass; regenerated Buildroot rootfs/DTB images. See `build/verification/smmu-iree-dynamic-registry-buildroot-20260511.log`. |
| Artifact staging | `./scripts/stage_buildroot_artifacts.sh` | Pass; staged Linux, Buildroot, and Hexagon firmware artifacts into the QBox platform artifact directory. See `build/verification/smmu-iree-dynamic-registry-stage-artifacts-20260511.log`. |
| QBox guest IREE Hexagon smoke | `QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260511-iree-dynamic-registry QBOX_BOOT_TIMEOUT=70 QBOX_IREE_LOGIN_DELAY=24 QBOX_IREE_AFTER_COMMAND_DELAY=24 ./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` | Pass; output matched `1x1x2x2xf32=[[[54 63][90 99]]]`, dynamic plugin registration marker appeared, and queue 0/1 async fences signaled. See `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260511-iree-dynamic-registry.driver.log` and `.log`. |
| Buildroot lane contract | `./scripts/check_buildroot_arm64_lane.sh` | Pass; includes dynamic plugin loading/staging/smoke marker gates. See `build/verification/smmu-iree-dynamic-registry-lane-20260511.log`. |
| SMMUv3 static compliance checker | `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/qbox-smmuv3-compliance-iree-dynamic-registry-final-20260511.json` | Pass, `SUMMARY {"pass": 602}` and `iree:hal-registry-dispatch` passed. Full SMMUv3 compliance remains `not_claimed`. See `build/verification/smmu-iree-dynamic-registry-static-final-20260511.log`. |
| IREE CNN readiness checker | `python3 scripts/check_iree_cnn_pipeline_readiness.py --json build/verification/iree-cnn-pipeline-readiness-dynamic-registry-20260511.json` | Pass for `repo_iree_hexagon_hal_registry`; overall summary remains `{"missing": 5, "pass": 39}` due pre-existing optional/proxy pipeline gaps. See `build/verification/iree-cnn-pipeline-readiness-dynamic-registry-20260511.log`. |

## Runtime markers

The QBox guest smoke log contains:

- `IREE Apollo Hexagon HAL: dynamically registered C HAL plugin=/opt/qbox/iree/tiny-cnn/lib/libapollo_iree_hexagon_hal_plugin.so driver=apollo-hexagon-hal api=1`
- `async fence irq wait signaled queue=0 irq=18`
- `async fence irq wait signaled queue=1 irq=18`
- `1x1x2x2xf32=[[[54 63][90 99]]]`
- `PASS: QBox guest IREE Hexagon tiny-CNN output matched`

## Current classification

- SMMU-COMP-090 remains a **functional slice**.
- The default QBox guest tiny-CNN path now exercises a dynamically loaded C HAL
  plugin rather than only static repo-local registry operations.
- The remaining blocker is upstream IREE integration and upstream test coverage,
  not the QBox guest dynamic-plugin proof path.
