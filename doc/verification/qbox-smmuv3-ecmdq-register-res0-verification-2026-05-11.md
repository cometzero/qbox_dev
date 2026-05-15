# QBox SMMUv3 ECMDQ unsupported-register RES0 verification

- Date: 2026-05-11
- Scope: `SMMU-COMP-020/060 ECMDQ unsupported-register RES0 slice`
- Target: `/build/qbox_dev`
- Ground truth: Arm SMMUv3 IHI0070G.b `SMMU_IDR1.ECMDQ`, `SMMU_S_IDR0.ECMDQ`, `SMMU_IDR6`, and `SMMU_CMDQ_CONTROL_PAGE_*` register definitions captured in `sources/smmu`.

## Implemented behavior

QBox still does **not** advertise Enhanced Command Queue support.  The Apollo
TBU now makes that unsupported policy explicit and machine-checkable:

- `SMMU_IDR1.ECMDQ == 0` and `SMMU_S_IDR0.ECMDQ == 0` remain clear.
- `SMMU_IDR6` and `SMMU_S_IDR6` read as RES0 and ignore writes.
- The first Non-secure ECMDQ discovery/control page registers
  `SMMU_CMDQ_CONTROL_PAGE_BASE0`, `CFG0`, and `STATUS0` read as RES0 and ignore
  writes.
- The corresponding Secure control-page aperture is also exposed as RES0/WI.

This is intentionally an unsupported-feature compliance slice.  It does not
implement ECMDQ control pages, per-page queue controls, EN/ENACK transitions,
parallel command consumption, ECMDQ error toggles, CMDQP_ERR, or ECMDQ MSI
abort reporting.

## Verification evidence

| Command | Log | Result |
| --- | --- | --- |
| `cmake --build sources/qbox/build --target apollo-smmu-tbu-tests -j4` | `build/verification/smmu-ecmdq-register-res0-build-20260511.log` | `Built target apollo-smmu-tbu-tests` |
| `./sources/qbox/build/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests --gtest_filter='*EcmdqUnsupportedRegistersAreRes0:*ArchitectedRegisterWindowResetsAndAcks*'` | `build/verification/smmu-ecmdq-register-res0-gtest-20260511.log` | `[  PASSED  ] 1 test.` |
| `ctest --test-dir sources/qbox/build -R apollo-smmu-tbu-tests --output-on-failure` | `build/verification/smmu-ecmdq-register-res0-ctest-20260511.log` | `100% tests passed` |
| `python3 scripts/check_qbox_smmuv3_compliance.py --json build/verification/smmu-ecmdq-register-res0-static-20260511.json` | `build/verification/smmu-ecmdq-register-res0-static-20260511.log` / `.json` | `SUMMARY {"pass": 990}` and `tbu:ecmdq-unsupported-registers-res0` passed; full compliance remains `not_claimed` |
| `./scripts/check_buildroot_arm64_lane.sh` | `build/verification/smmu-ecmdq-register-res0-lane-20260511.log` | `Lane conclusion:` present and new ECMDQ greps passed |
| `bash -n scripts/*.sh` | `build/verification/smmu-ecmdq-register-res0-bash-syntax-20260511.log` | exit 0, empty log |
| `python3 -m py_compile scripts/check_qbox_smmuv3_compliance.py` | `build/verification/smmu-ecmdq-register-res0-pycompile-20260511.log` | exit 0, empty log |
| `{ git diff --check; git -C sources/qbox diff --check; }` | `build/verification/smmu-ecmdq-register-res0-diff-check-20260511.log` | exit 0, empty log |
| evidence summary script | `build/verification/smmu-ecmdq-register-res0-evidence-summary-20260511.log` | all slice checks PASS |

## No-overclaim boundary

Full ARM SMMUv3 compliance remains `not_claimed`.  This slice only fixes the
architected discovery behavior for an unsupported ECMDQ implementation.

Full ECMDQ support would require implementing `IDR6`-advertised control-page
counts, all ECMDQ register pages, queue enable/disable handshakes, per-queue
error protocol, ordering rules, GERROR.CMDQP_ERR/S_GERROR.CMDQP_ERR, and MSI
abort paths, then validating them against packet-level command ordering tests.
