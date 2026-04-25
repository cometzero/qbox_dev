# QBox Buildroot ARM64 SoC Specification Set

This directory decomposes `doc/qbox-buildroot-arm64-soc-boot-plan-2026-04-25.md`
into implementation-oriented specification documents.

## Documents

| Document | Purpose |
| --- | --- |
| [`qbox-buildroot-arm64-prd.md`](qbox-buildroot-arm64-prd.md) | Product requirements, goals, non-goals, personas, milestones, and acceptance criteria. |
| [`qbox-buildroot-arm64-spec.md`](qbox-buildroot-arm64-spec.md) | Functional and technical specification for artifacts, platform behavior, boot contract, and verification gates. |
| [`qbox-buildroot-arm64-design.md`](qbox-buildroot-arm64-design.md) | System design for Buildroot, QBox platform wiring, memory map, boot flow, and future heterogeneous-core expansion. |
| [`qbox-buildroot-arm64-implementation.md`](qbox-buildroot-arm64-implementation.md) | Execution checklist, file ownership, command sequence, test plan, and delivery artifacts. |

## Source plan

- `doc/qbox-buildroot-arm64-soc-boot-plan-2026-04-25.md`

## Milestone policy

The first milestone is intentionally narrow: boot Buildroot Linux on the
AArch64 Cortex-A710 application cluster in QBox. Cortex-R52, Cortex-M55,
Zephyr, and custom SystemC devices are deferred until the Linux boot proof is
stable.
