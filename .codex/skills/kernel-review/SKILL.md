---
name: kernel-review
description: Use when Codex writes, edits, reviews, or debugs Linux kernel code, kernel patches, Kconfig, devicetree, or Linux config fragments in this workspace, especially paths under sources/linux, configs/linux, drivers/, arch/, include/linux/, or Documentation/devicetree/bindings. Loads the vendored masoncl/review-prompts Linux kernel prompts and requires a post-change regression review before finalizing kernel work.
---

# Kernel Review

## Prompt Root

Resolve the kernel review prompt directory before doing kernel work:

1. Prefer `<repo-root>/.codex/review-prompts/kernel` when it exists.
2. In this workspace, the expected fallback is
   `/build/qbox_dev/.codex/review-prompts/kernel`.
3. Stop and report a setup blocker if neither path contains
   `technical-patterns.md` and `review-core.md`.

The vendored prompt source is recorded in
`<repo-root>/.codex/review-prompts/SOURCE.md`.

## Required Loading

For any kernel code implementation, review, or debugging task:

1. Read `technical-patterns.md` first.
2. For patch review or after editing kernel files, read `review-core.md` and
   follow its regression-review protocol.
3. Read `subsystem/subsystem.md` and load matching subsystem files for the
   changed paths or APIs.
4. For repeated mechanical kernel edits, read `coccinelle.md` and prefer a
   semantic patch when that is safer than hand-editing each file.
5. For oops, warning, crash, or stack-trace work, read `debugging.md`.

## QBox Path Mapping

Treat these paths as kernel review triggers:

- `sources/linux/**`
- `configs/linux/**`
- files named `Kconfig`, `Makefile`, `*.c`, `*.h`, `*.dts`, `*.dtsi`, or
  `linux.config` when they affect the Linux guest

Use these default subsystem prompts when relevant:

- Devicetree or OF APIs: `subsystem/of.md` and, for bindings,
  `subsystem/dt-bindings.md`
- Kconfig or config fragments: `subsystem/kconfig.md`
- MMIO/register access: `subsystem/io-accessors.md`
- Locking, lifetime, async work, or RCU: `subsystem/locking.md`,
  `subsystem/workqueue.md`, or `subsystem/rcu.md`
- Power/runtime PM or domains: `subsystem/pm.md` or
  `subsystem/pmdomain.md`
- Page table, translation, or IOMMU-adjacent changes:
  `subsystem/mm-pagetable.md`

## Completion Gate

Before finalizing kernel work, include review evidence in the response:

- prompt files loaded
- changed kernel paths reviewed
- concrete regressions found, or "no prompt-driven regressions found"
- verification commands run and any remaining blockers

Do not let the prompt review replace normal build, static, boot, or smoke
verification required by the repository.
