# Report Contract

## Primary deliverables

1. `BUG-<id>-analysis.md`: why it occurs, affected/fixed versions, call chain, root cause, source/dynamic evidence, patch semantics, validation, workaround, limitations, and confidence.
2. `BUG-<id>-reproduction.md`: beginner-executable environment preparation, debug build, isolated initialization, baseline, exact reproduction, GDB/core/MTR, fix validation, cleanup, expected output, and troubleshooting.

## Quality gate

### Analysis report

- Distinguishes reported, verified, affected, fixed, and locally tested versions.
- Explains the earliest invalid state and why the user-visible symptom follows.
- Provides version/commit/file/function/line for source evidence.
- Explains the fix semantically and identifies its official test.
- Separates official fix claim from local fix validation.
- Includes failed experiments, limitations, evidence labels, confidence, and evidence index.

### Reproduction report

- Contains complete commands, absolute or defined paths, prerequisites, expected output, and failure handling.
- Provides both automation and enough manual explanation to avoid a black box.
- Uses isolated directories/ports/sockets and ownership-marked cleanup.
- Explains each GDB command and captures evidence paths.
- Repeats the same trigger against the fixed version and proves path coverage.

Do not leave a material section as “TBD” in final delivery. Use “not available” or “not verified” with reason and attempted methods.
