# QBox SMMUv3 IDR1 discovery/limits verification

- Date: 2026-05-11
- Scope: `SMMU-COMP-020/030/050/060 IDR1 discovery/limits slice`
- Target: `/build/qbox_dev`
- Ground truth: Arm SMMUv3 IHI0070G.b `SMMU_IDR0.ST_LEVEL`, `SMMU_IDR1`, and `SMMU_S_IDR1` field definitions.

## Implemented behavior

The Apollo TBU now exposes a bounded architected discovery surface that matches
its modeled stream, substream, queue, and attribute-override behavior:

- `SMMU_IDR0.ST_LEVEL` advertises 2-level Stream Table support because the model
  already implements bounded linear and 2-level STRTAB selection, and Arm requires
  `ST_LEVEL != 0` when `SMMU_IDR1.SIDSIZE >= 7`.
- `SMMU_IDR1.SIDSIZE` reports 8 bits, covering the modeled and tested StreamID
  range while keeping larger physical StreamID widths out of scope.
- `SMMU_IDR1.SSIDSIZE` reports 20 bits, matching the modeled PASID/SSID masks
  used by PRI, ATS, and context-descriptor paths.
- `SMMU_IDR1.CMDQS`, `EVENTQS`, and `PRIQS` report log2 entries 15, matching the
  queue-base decoder limit.
- `SMMU_IDR1.ATTR_TYPES_OVR` and `ATTR_PERMS_OVR` are set to match the modeled
  GBPA/STE memory-attribute and access-override paths.
- `SMMU_S_IDR1` no longer mirrors Non-secure queue and attribute fields; it
  reports only `SECURE_IMPL`, `SEL2`, and Secure `S_SIDSIZE` while keeping
  bits[28:6] RES0.

The Apollo Linux selftest constants were updated to the same guest-visible
surface: `IDR0=0x098db70b` and `IDR1=0x0def7d08`.

## Verification evidence

| Command | Log | Result |
| --- | --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j4` | `build/verification/smmu-idr1-discovery-limits-build-20260511.log` | `Built target apollo-smmu-tbu-tests` |
| `./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*ArchitectedRegisterMmioSurface:*SecureRegisterBankConfiguresStrtabCmdqAndEventq*'` | `build/verification/smmu-idr1-discovery-limits-gtest-20260511.log` | `[  PASSED  ] 2 tests.` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/smmu-idr1-discovery-limits-ctest-20260511.log` | `100% tests passed` |
| `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/smmu-idr1-discovery-limits-static-20260511.json` | `build/verification/smmu-idr1-discovery-limits-static-20260511.log` / `.json` | `SUMMARY {"pass": 1013}` and `tbu:idr1-discovery-limits` passed; full compliance remains `not_claimed` |
| `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-idr1-discovery-limits-lane-20260511.log` | `Lane conclusion:` present and new IDR0/IDR1 greps passed |
| `bash -n scripts/*.sh` | `build/verification/smmu-idr1-discovery-limits-bash-syntax-20260511.log` | exit 0, empty log |
| `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | `build/verification/smmu-idr1-discovery-limits-pycompile-20260511.log` | exit 0, empty log |
| `{ git diff --check; git -C sources/qbox diff --check; }` | `build/verification/smmu-idr1-discovery-limits-diff-check-20260511.log` | exit 0, empty log |

## No-overclaim boundary

Full ARM SMMUv3 compliance remains `not_claimed`.  This slice only aligns the
bounded discovery fields for already-modeled StreamID/SSID, queue, and attribute
behavior.  Full upstream Linux `arm-smmu-v3` lifecycle parity, complete PCIe
ATS/PRI packet ordering, ECMDQ implementation, exhaustive out-of-range StreamID
and SubstreamID fault coverage, complete queue stress beyond log2<=15, DPT, and
RME/GPT/GPC remain open.
