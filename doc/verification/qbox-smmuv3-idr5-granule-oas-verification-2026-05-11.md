# QBox SMMUv3 IDR5 granule/OAS discovery verification

- Date: 2026-05-11
- Scope: `SMMU-COMP-020/040/050 IDR5 granule/OAS discovery slice`
- Target: `/build/qbox_dev`
- Ground truth: Arm SMMUv3 IHI0070G.b `SMMU_IDR5` fields for `GRAN4K`, `GRAN16K`, `GRAN64K`, and `OAS`.

## Implemented behavior

The Apollo TBU now advertises IDR5 values matching the modeled walker and output
address aperture:

- `SMMU_IDR5.GRAN4K`, `GRAN16K`, and `GRAN64K` are set because the component
  walker matrix covers selected 4K, 16K, and 64K translation granules.
- `SMMU_IDR5.OAS` reports 48-bit output addresses, matching
  `ARCH_DESC_OUTPUT_MASK == 0x0000fffffffff000` and the existing Translated
  address-size no-event abort boundary.
- No 52-bit/56-bit, DS, VAX, D128, or STALL_MAX capability is newly advertised.

This is a discovery-register alignment slice; it does not claim full descriptor
matrix parity or all OAS truncation/exception variants.

## Verification evidence

| Command | Log | Result |
| --- | --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j4` | `build/verification/smmu-idr5-granule-oas-build-20260511.log` | `Built target apollo-smmu-tbu-tests` |
| `./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*ArchitectedRegisterMmioSurface:*ArchitectedWalkerGranuleBlockAndFaultMatrix:*AtsTranslatedAddressSizeAbortIsNoEvent*'` | `build/verification/smmu-idr5-granule-oas-gtest-20260511.log` | `[  PASSED  ] 3 tests.` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/smmu-idr5-granule-oas-ctest-20260511.log` | `100% tests passed` |

| `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/smmu-idr5-granule-oas-static-20260511.json` | `build/verification/smmu-idr5-granule-oas-static-20260511.log` / `.json` | `SUMMARY {"pass": 1008}` and `tbu:idr5-granule-oas-discovery` passed; full compliance remains `not_claimed` |
| `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-idr5-granule-oas-lane-20260511.log` | `Lane conclusion:` present and new IDR5 greps passed |
| `bash -n scripts/*.sh` | `build/verification/smmu-idr5-granule-oas-bash-syntax-20260511.log` | exit 0, empty log |
| `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | `build/verification/smmu-idr5-granule-oas-pycompile-20260511.log` | exit 0, empty log |
| `{ git diff --check; git -C sources/qbox diff --check; }` | `build/verification/smmu-idr5-granule-oas-diff-check-20260511.log` | exit 0, empty log |

## No-overclaim boundary

Full ARM SMMUv3 compliance remains `not_claimed`.  IDR5 now advertises only the
bounded granules and 48-bit OAS behavior already modeled; complete page-table
attribute parity, D128/52-bit/56-bit address-size modes, DPT, RME/GPT/GPC, and
packet-level ATS/PRI/ECMDQ protocol remain open.
