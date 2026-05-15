# QBox SMMUv3 Endpoint PASID/SSID Verification - 2026-05-10

## Scope

Endpoint PASID/SSID functional slice for SMMU-COMP-030 and SMMU-COMP-080.

The slice propagates endpoint-derived SubstreamID/PASID metadata from the Apollo
Hexagon DMA endpoint through the shared TLM extension into the Apollo SMMU TBU.
The TBU uses this metadata to tag modeled ATS cache entries and EVENTQ common
record SSV/SubstreamID fields.

This is not full Arm SMMUv3 PASID compliance. PCIe PASID request semantics,
Linux arm-smmu-v3 generated CD invalidation, full endpoint/CD table parity,
platform-visible multi-master topology, and transaction re-drive remain open.

## Implementation

- `sources/qbox/systemc-components/common/include/tlm-extensions/apollo-smmu-stream-id.h`
  carries optional `substream_id`/`substream_id_valid` metadata with translated
  transactions.
- `sources/qbox/systemc-components/apollo_hexagon_dma/include/apollo_hexagon_dma.h`
  advertises `CAP_ENDPOINT_PASID`, exposes a PASID register/parameters, logs the
  endpoint PASID, and attaches it to translated DMA requests.
- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  advertises `FEATURE_ENDPOINT_SUBSTREAM_ID`, decodes endpoint SSID metadata,
  and uses it for ATS and EVENTQ records.
- `sources/qbox/platforms/buildroot/conf_aarch64.lua` configures the Hexagon DMA
  endpoint with `substream_id = 0x3` and `substream_id_valid = true`.
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc` adds
  `EndpointSubstreamIdTagsAtsAndFaultEvents`.
- `scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh` now gates the guest
  smoke on robust stream/context descriptor and endpoint PASID/SSID markers.

## Evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Component build | PASS | `build/verification/apollo-smmuv3-endpoint-ssid-build-20260510.log`: `Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`, `Built target apollo_hexagon_dma` |
| Component CTest | PASS | `build/verification/apollo-smmuv3-endpoint-ssid-ctest-20260510.log`: `100% tests passed, 0 tests failed out of 1` |
| Static/checker/lane | PASS | `build/verification/smmu-endpoint-ssid-static-final-20260510.log`: shell/Python syntax pass, `SUMMARY {"pass": 173}`, Buildroot lane `PASS`, and superproject/QBox/Linux diff checks pass. |
| Platform build | PASS | `build/verification/qbox-platform-smmu-endpoint-ssid-20260510.log`: `QBox Buildroot platform runtime built in /build/qbox_dev/sources/qbox/build`. |
| Guest smoke | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-endpoint-ssid.driver.log`: `PASS: QBox guest IREE Hexagon tiny-CNN output matched`, `Expected: 1x1x2x2xf32=[[[54 63][90 99]]]`. |
| Runtime PASID/SSID | PASS | `build/verification/qbox-iree-tiny-cnn-hexagon-guest-20260510-smmu-endpoint-ssid.log`: `features=0x3ffff`, `pasid-valid=1 pasid=0x3`, `ssid=0x3`, and `endpoint-ssid=0x3`. |

## Commands

```bash
cmake --build sources/qbox/build --target apollo-smmu-tbu-tests \
  apollo_smmu_tbu apollo_hexagon_dma -j"$(nproc)"
ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests \
  --output-on-failure
./scripts/build_qbox_buildroot_platform.sh
QBOX_HEXAGON_GUEST_SMOKE_STAMP=20260510-smmu-endpoint-ssid \
QBOX_BOOT_TIMEOUT=55 QBOX_IREE_LOGIN_DELAY=24 \
QBOX_IREE_AFTER_COMMAND_DELAY=15 \
./scripts/run_iree_tiny_cnn_hexagon_qbox_guest_smoke.sh
scripts/check_qbox_smmuv3_compliance.py --self-test-negative \
  --json build/verification/qbox-smmuv3-compliance-endpoint-ssid-final-20260510.json
./scripts/check_buildroot_arm64_lane.sh
```

## Remaining blockers

- PCIe/ATS PASID request semantics beyond a modeled endpoint field.
- Linux `arm-smmu-v3` generated CD invalidation and PASID lifecycle coverage.
- Full CD-table parity for endpoint PASID traffic.
- Platform-visible multi-master topology and runtime smoke.
- True stalled endpoint transaction buffering and re-drive.
- Byte-exact event formats for every Arm SMMUv3 event type.
- True upstream IREE source integration rather than a repo-local guest helper.
