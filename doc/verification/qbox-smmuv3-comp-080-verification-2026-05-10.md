# QBox SMMUv3 SMMU-COMP-080 verification report

- Date: 2026-05-10
- Scope: `/build/qbox_dev`
- Story: multi-master / multi-StreamID isolation functional slice
- Source plan: `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`
- Checklist: `doc/spec/qbox-smmuv3-compliance-checklist.md`

## Result

SMMU-COMP-080 advanced from `missing` to `functional-slice`.

Implemented in QBox:

- `sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h`
  - Adds `gs::ApolloSmmuStreamIdExtension` so translated TLM transactions can carry a master StreamID.
- `sources/qbox/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h`
  - Attaches the DMA master's configured `stream_id` to SMMU-translated transactions.
- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - Tags dynamic map entries with StreamID.
  - Filters dynamic translation by transaction StreamID.
  - Tracks ATS cache entries by StreamID.
  - Invalidates only the selected StreamID's ATS entries on per-SID unmap/remap.
  - Adds `REG_MAP_STREAM_ID` / `REG_MAP_STREAM_COUNT` compatibility registers and `FEATURE_MULTI_STREAM_ID`.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - Adds `MultiStreamIdMapsAreIsolated`.

This is not full ARM SMMUv3 multi-master compliance. The platform DTS still exposes one Linux-visible
Apollo Hexagon master with StreamID `0x1`; PCI RID/PASID, a second guest-visible master, and full STRTAB/CD
multi-SID command invalidation coverage remain open.

## Verification evidence

### Component unit regression

Command:

```sh
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j"$(nproc)"
ctest --test-dir sources/qbox/build -R '^apollo-smmu-tbu-tests$' --output-on-failure
```

Evidence:

- `build/verification/apollo-smmuv3-multi-sid-ctest-20260510.log`

Observed result:

- Target build reached `Built target apollo-smmu-tbu-tests`.
- CTest reached `100% tests passed, 0 tests failed out of 1`.
- New test `MultiStreamIdMapsAreIsolated` verifies:
  - SID `0x1` and SID `0x2` can map the same IOVA to different PAs.
  - SID `0x1` reads only SID `0x1` data.
  - SID `0x2` reads only SID `0x2` data.
  - Unknown SID `0x3` cannot debug-read either mapping.
  - Removing SID `0x1` invalidates SID `0x1` ATS state while SID `0x2` remains valid.

### Platform build regression

Command:

```sh
./scripts/build_qbox_buildroot_platform.sh
```

Evidence:

- `build/verification/qbox-platform-smmu-comp-080-multi-sid-20260510.log`

Observed result:

- Build reached `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`.
- This validates that the new common TLM extension and DMA/TBU headers compile in the full QBox runtime build.

### Guest IREE smoke regression

Command:

```sh
QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260510-smmu-comp-080-multi-sid \
QBOX_BOOT_TIMEOUT=180 \
QBOX_IREE_LOGIN_DELAY=24 \
QBOX_IREE_AFTER_COMMAND_DELAY=25 \
./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh
```

Evidence:

- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-080-multi-sid.driver.log`
- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-comp-080-multi-sid.log`
- `build/verification/qbox-iree-tiny-cnn-hexagon-guest-boot-20260510-smmu-comp-080-multi-sid.log`

Observed result:

- Driver reached `PASS: QBox guest IREE Hexagon tiny-CNN output matched`.
- Expected tensor matched: `1x1x2x2xf32=[[[54 63][90 99]]]`.
- Runtime log shows translated DMA still carries StreamID `0x1` and the TBU reports `features=0xfff`, which includes the new `FEATURE_MULTI_STREAM_ID` bit.

### Static/checker and lane gates

Commands:

```sh
python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py scripts/check_iree_cnn_pipeline_readiness.py scripts/qbox_pty_runner.py
scripts/check_qbox_smmuv3_compliance.py --self-test-negative --json build/verification/qbox-smmuv3-compliance-multi-sid-final-20260510.json
git diff --check
git -C sources/qbox diff --check
git -C sources/linux diff --check
./scripts/check_buildroot_arm64_lane.sh
```

Evidence:

- `build/verification/smmu-comp-080-multi-sid-static-final-20260510.log`
- `build/verification/qbox-smmuv3-compliance-multi-sid-final-20260510.json`
- `build/verification/check-buildroot-arm64-lane-smmu-comp-080-20260510.log`

Observed result:

- Compliance checker reached `SUMMARY {"pass": 77}`.
- Classification keeps `full_smmuv3_compliance` as `not_claimed`.
- Buildroot ARM64 lane checker completed with `PASS` records and preserved the external Linux/libqemu ownership contract.

## Remaining blockers

- No second Linux-visible platform/DTS master exists yet.
- No PCI RID/PASID or SSID/CD-index matrix is implemented.
- CMDQ invalidation opcodes do not yet drive full per-SID STRTAB/CD/TLB invalidation semantics.
- Full multi-master runtime smoke is still pending beyond the component functional slice.
