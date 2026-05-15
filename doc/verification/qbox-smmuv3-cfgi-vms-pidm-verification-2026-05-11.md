# QBox SMMUv3 `CMD_CFGI_VMS_PIDM` verification - 2026-05-11

## Scope

SMMU-COMP-020 CMD_CFGI_VMS_PIDM functional slice.

This slice adds a conservative model of the SMMUv3 `CMD_CFGI_VMS_PIDM`
command. The Apollo TBU accepts opcode `0x07`, decodes the VMID operand, and
invalidates the currently modeled VMID-indexed VMS/PARTID_MAP cache state when
that VMID matches the last fetched VMS state. It does not claim full MPAM or
multi-entry VMS cache compliance.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `FEATURE_ARCH_CFGI_VMS_PIDM`
  - `ARCH_CMD_CFGI_VMS_PIDM = 0x07`
  - `handle_cmdq_cfgi_vms_pidm`
  - `clear_modeled_vms_state_for_vmid`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `CmdqCfgiVmsPidmInvalidatesModeledVmsState`

## Validation evidence

| Check | Evidence |
| --- | --- |
| Build | `build/verification/apollo-smmu-tbu-cfgi-vms-pidm-build-20260511.log` (`Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`) |
| Focused CTest | `build/verification/apollo-smmu-tbu-cfgi-vms-pidm-ctest-20260511.log` (`100% tests passed, 0 tests failed out of 1`) |
| Focused gTest | `build/verification/apollo-smmu-tbu-cfgi-vms-pidm-gtest-20260511.log` (`[  PASSED  ] 1 test.`) |
| Syntax checks | `build/verification/smmu-cfgi-vms-pidm-syntax-20260511.log` |
| Static/lane checker | `build/verification/smmu-cfgi-vms-pidm-static-final-20260511.log` (`PASS  tbu:cmdq-cfgi-vms-pidm`, `SUMMARY {"pass": 467}`) |
| Compliance JSON | `build/verification/qbox-smmuv3-compliance-cfgi-vms-pidm-final-20260511.json` (`full_smmuv3_compliance: not_claimed`) |

## Result

The new component vector verifies both sides of the modeled VMID filter:

- command VMID `0x23` does not match the modeled VMS state VMID `0x22`, so the
  VMS state remains present and the invalidation count is zero;
- command VMID `0x22` matches, so the modeled VMS state is cleared and the
  command records one invalidation while leaving ATS entries untouched.

Remaining blockers: real multi-entry VMS/PARTID_MAP caching, MPAM PARTID_MAP
translation semantics, Secure/Realm VMS state, and upstream Linux
`CMD_CFGI_VMS_PIDM` lifecycle parity remain open.
