# QBox SMMUv3 PRI PPR/Stop Marker Verification (2026-05-11)

## Scope

SMMU-COMP-060 PRI PPR/Stop Marker slice.

This slice improves the Apollo TBU's modeled PCIe PRI protocol surface without
claiming full packet-level ATS/PRI compliance.  It adds explicit PPR metadata for
SSV, Last, Read, Write, Execute, Privileged, PRGIndex, and SubstreamID/PASID
storage in the memory-backed PRIQ record model.  It also models two protocol
corner cases from the local SMMUv3 reference set:

- Stop PASID Markers are `SSV==1` with `LWR==0b100`; they do not generate PRG
  responses.
- Non-last PPRs discarded during PRIQ overflow do not generate automatic PRG
  responses.

## Ground truth

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  describes PRI messages as carrying StreamID, SSV/SubstreamID, Page Address,
  PRGIndex, and Last/W/R/X/Priv fields, and states that Stop PASID Markers use
  `SSV==1` and `LWR==0b100`.
- `sources/smmu/wiki/synthesis/smmu-pcie-ats-integration.md` summarizes that
  Stop Markers receive no response and that non-last PPRs discarded by overflow
  are silently ignored.

## Changed paths

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
- `scripts/check_qbox_smmuv3_compliance.py`
- `scripts/check_buildroot_arm64_lane.sh`
- `doc/analysis/qbox-smmuv3-compliance-gap-plan-2026-05-10.md`
- `doc/spec/qbox-smmuv3-compliance-checklist.md`

## Planned evidence

- Build: `build/verification/smmu-pri-ppr-stop-marker-build-20260511.log`
- Focused gTest: `build/verification/smmu-pri-ppr-stop-marker-gtest-20260511.log`
- CTest: `build/verification/smmu-pri-ppr-stop-marker-ctest-20260511.log`
- Static checker: `build/verification/smmu-pri-ppr-stop-marker-static-20260511.{log,json}`
- Lane check: `build/verification/smmu-pri-ppr-stop-marker-lane-20260511.log`

## No-overclaim note

This remains a functional model slice.  Full PCIe packet transport, Root Complex
wire protocol, DPT/GPC interactions, complete PRI auto-response PASID-prefix
selection, and upstream `arm-smmu-v3` lifecycle parity remain open.
