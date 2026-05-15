# QBox SMMUv3 MPAM/VMS discovery verification - 2026-05-11

## Scope

SMMU-COMP-020/050 MPAM/VMS discovery functional slice.

This slice makes the guest-visible SMMUv3 discovery registers coherent with the
modeled VMS path. The Apollo TBU now advertises `SMMU_IDR3.MPAM` while keeping
`SMMU_IDR3.DPT` clear, exposes `SMMU_MPAMIDR`, and reports a nonzero
`PARTID_MAX` so VMS/MPAM functional slices are discoverable without claiming
DPT support.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `ARCH_IDR3_MPAM = 1u << 7`
  - `ARCH_IDR3_DPT = 1u << 15`
  - `ARCH_IDR3 = ARCH_IDR3_MPAM`
  - `SMMUV3_MPAMIDR = 0x130`
  - `ARCH_MPAMIDR_PARTID_MAX = 31`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `ArchitectedRegisterMmioSurface`
  - `MpamDiscoveryAdvertisesVmsPrerequisites`
  - `DptiCommandsSetGerrorWhenDptUnsupported` now checks only `IDR3.DPT==0`
    instead of assuming all of `IDR3` is zero.
- `sources/linux/drivers/soc/apollo/apollo-hexagon-test.c`
  - `APOLLO_SMMUV3_ARCH_IDR3 0x00000080`

## Validation evidence

| Check | Evidence |
| --- | --- |
| Build | `build/verification/apollo-smmu-tbu-mpam-discovery-build-20260511.log` (`Built target apollo_smmu_tbu`, `Built target apollo-smmu-tbu-tests`) |
| Component CTest | `build/verification/apollo-smmu-tbu-mpam-discovery-ctest-20260511.log` (`100% tests passed, 0 tests failed out of 1`) |
| Focused gTest | `build/verification/apollo-smmu-tbu-mpam-discovery-gtest-20260511.log` (`[  PASSED  ] 1 test.`) |
| Syntax checks | `build/verification/smmu-mpam-discovery-syntax-20260511.log` |
| Static/lane checker | `build/verification/smmu-mpam-discovery-static-final-20260511.log` (`PASS  tbu:mpam-vms-discovery`, `SUMMARY {"pass": 479}`) |
| Compliance JSON | `build/verification/qbox-smmuv3-compliance-mpam-discovery-final-20260511.json` (`full_smmuv3_compliance: not_claimed`) |

## Result

`MpamDiscoveryAdvertisesVmsPrerequisites` proves the ID register surface now
reports MPAM discovery, leaves DPT disabled, exposes the MPAMIDR PARTID range,
and keeps the modeled VMS fetch plus `CMD_CFGI_VMS_PIDM` feature bits visible.
The full component CTest also proves that the existing DPT unsupported command
path still rejects `CMD_DPTI_ALL`/`CMD_DPTI_PA` based on `IDR3.DPT==0`.

Remaining blockers: SMMU-originated MPAM transaction attributes,
GMPAM/GBPMPAM programming behavior, physical PARTID remapping through the VMS
PARTID_MAP, Secure/Realm MPAMIDR variants, PMG behavior, and full MPAM
transaction propagation remain open.
