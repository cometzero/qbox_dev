# QBox SMMUv3 PRI Secure-stream auto-failure verification — 2026-05-11

## Scope

SMMU-COMP-060 PRI Secure-stream auto-failure slice.

This verifies the architected PRI miscellaneous rule for protocol Page Request
Packets (PPRs): incoming PPRs from a Secure stream receive Response Failure and
are not queued in PRIQ.  The implementation is intentionally limited to the
protocol PPR path (`push_pri_protocol_record`) so the older Secure PRIQ bank
compatibility helper can continue to test Secure queue/MSI plumbing separately.

## Ground truth

Local references:

- `sources/smmu/IHI0070G_b-System_Memory_Management_Unit_Architecture_Specification.md`
  states that Response Failure is returned for all incoming PPRs when the PPR is
  received from a Secure stream.
- `sources/smmu/wiki/concepts/pcie-ats-pri.md` summarizes the same PRIQ
  miscellaneous behavior with Secure-stream auto-failure.

## Implementation evidence

- `sources/qbox/systemc-components/apollo_smmu_tbu/include/apollo_smmu_tbu.h`
  - `arch_pri_secure_stream_auto_failure()`
  - `m_arch_pri_secure_auto_failures`
  - `secure-stream-pri` auto-response reason
- `sources/qbox/tests/components/apollo_smmu_tbu/apollo-smmu-tbu-tests.cc`
  - `PriProtocolSecureStreamAutoFailsWithoutQueueing`
- `scripts/check_qbox_smmuv3_compliance.py`
- `scripts/check_buildroot_arm64_lane.sh`

## Verification evidence

Expected durable logs for this slice:

- `build/verification/smmu-pri-secure-stream-auto-failure-build-20260511.log`
- `build/verification/smmu-pri-secure-stream-auto-failure-gtest-20260511.log`
- `build/verification/smmu-pri-secure-stream-auto-failure-ctest-20260511.log`
- `build/verification/smmu-pri-secure-stream-auto-failure-static-20260511.json`
- `build/verification/smmu-pri-secure-stream-auto-failure-lane-20260511.log`
- `build/verification/smmu-pri-secure-stream-auto-failure-final-closure-check-20260511.log`
- `build/verification/smmu-pri-secure-stream-auto-failure-evidence-summary-final-20260511.log`

## No-overclaim boundary

`full_smmuv3_compliance` must remain `not_claimed`.  This slice does not provide
full PCIe ATS/PRI packet transport, complete upstream driver lifecycle parity,
RME/GPT/GPC policy, or complete Secure/Realm command and event protocol parity.
