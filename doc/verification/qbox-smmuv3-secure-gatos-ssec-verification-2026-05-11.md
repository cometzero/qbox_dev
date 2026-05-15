# QBox SMMUv3 S_GATOS.SSEC verification

- Date: 2026-05-11
- Scope: Attempt 94, SMMU-COMP-030/080 ATOS register parity slice
- Marker: SMMU-COMP-030/080 S_GATOS.SSEC stream-selection slice.

## Ground truth

Local SMMUv3 reference material in `sources/smmu` is the ground truth:

- `sources/smmu/wiki/concepts/atos.md`: Secure ATOS can query Secure or
  Non-secure streams through `SMMU_S_GATOS_SID.SSEC`; ATOS faults do not record
  events or stall.
- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`:
  `SMMU_S_GATOS_SID.SSEC` bit 53 selects Secure versus Non-secure StreamID
  lookup, and a Secure-interface Non-secure stream ATOS request requires both
  `SMMU_S_CR0.SMMUEN` and `SMMU_CR0.SMMUEN`.

## Implemented behavior

- `ARCH_ATOS_SID_SECURE_STREAM` models `SMMU_S_GATOS_SID.SSEC` bit 53.
- `run_arch_gatos_register_translate(true)` now selects the Secure stream-table
  bank only when SSEC is set; SSEC clear performs a Non-secure StreamID lookup
  while still returning the result through the Secure `SMMU_S_GATOS_PAR` bank.
- Secure-interface Non-secure lookups return modeled `INTERNAL_ERR` PAR
  (`FAULTCODE=0xfd`) when `SMMU_S_CR0.SMMUEN` is clear, preserving the
  architected Secure-interface gate before the Non-secure stream lookup.
- `SecureSmmuv3GatosSsecSelectsNonsecureStream` covers both the Secure-CR0 gate
  and successful Non-secure stream-table selection from the Secure ATOS
  interface. Existing Secure GATOS tests now set SSEC explicitly when they intend
  a Secure stream lookup.

## Validation evidence

- Build log: `build/verification/smmu-secure-gatos-ssec-build-20260511.log`
- Focused gTest log: `build/verification/smmu-secure-gatos-ssec-gtest-20260511.log`
- CTest log: `build/verification/smmu-secure-gatos-ssec-ctest-20260511.log`
- Static checker JSON: `build/verification/smmu-secure-gatos-ssec-static-20260511.json`
- Lane log: `build/verification/smmu-secure-gatos-ssec-lane-20260511.log`

## Remaining blockers

This is still a bounded ATOS parity slice, not a full SMMUv3 compliance claim.
Remaining aggregate gaps include VATOS/S_VATOS optional pages and VMID scoping,
remaining ATOS_ADDR fields beyond TYPE/RnW, PCIe ATS/PRI packet attributes,
Root/Realm RME/GPT/GPC, and upstream lifecycle parity.
