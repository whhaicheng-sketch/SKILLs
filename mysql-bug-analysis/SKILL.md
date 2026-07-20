---
name: mysql-bug-analysis
description: Use when a MySQL server defect or version upgrade problem requires official evidence, local source builds, reproducible diagnosis, version comparison, or source-level analysis.
---

# MySQL BUG Analysis

## Objective

Investigate MySQL BUGs as evidence-backed database engineering cases. Prefer real reproduction and dynamic debugging; when that is impossible, continue through MTR, instrumentation, controlled failure simulation, official patch analysis, and version-pinned static source analysis. Never present inference as experiment.

## Required outputs

For each BUG investigation, complete exactly two primary Markdown reports. Skill maintenance, audit, installation, and documentation tasks are not BUG investigations and do not produce these reports.

1. `BUG-<id>-analysis.md` — symptom, trigger, affected/fixed versions, root cause, call chain, source and dynamic evidence, fix semantics, validation, workaround, limitations, confidence, and evidence index.
2. `BUG-<id>-reproduction.md` — beginner-executable environment preparation, Debug build, isolated instance, baseline, reproduction, GDB/core/MTR, fixed-version comparison, cleanup, expected results, and troubleshooting.

Raw BUG pages, Release Notes, commits, diffs, logs, SQL, GDB sessions, core metadata, build manifests, and failed experiments remain under the task workspace and are referenced by the reports.

## Configuration and entry point

Use `scripts/mysql_bug.py`. Configuration precedence is:

`task arguments > selected YAML > built-in defaults`

Resolve YAML in this order:

1. `--config`
2. `$MYSQL_BUG_SKILL_CONFIG`
3. `./mysql-bug-skill.yaml`
4. `~/.codex/mysql-bug-skill.yaml`
5. built-in defaults

Run before any managed action. Omit `--config` when using automatic configuration discovery:

```bash
python3 scripts/mysql_bug.py config-check [--config <CONFIG>]
```

The user may provide only a BUG ID, URL, description, error log, core, version, SQL, reproduction steps, source directory, or binary. Automatically discover the remaining environment. Create a local ID such as `LOCAL-YYYYMMDD-NNN` when no official BUG ID exists.

## Mandatory workflow

Read [references/workflow.md](references/workflow.md) at task start and follow its state machine. Do not silently skip `BASELINE`, source evidence, fix validation, confidence grading, or report quality checks. If a phase is impossible or inapplicable, record it with `skip-phase --phase <PHASE> --reason '<REASON>'`, explain the limitation, and lower confidence; never mark it completed.

## Progress reporting

Keep the user informed throughout long-running investigations. Treat 30 minutes as the maximum interval between progress updates while work is active, not as a fixed schedule. Report sooner when a phase completes, a command fails, the investigation becomes blocked, the working hypothesis changes, or material evidence appears. Each update should state the current phase, concrete evidence or progress since the previous update, whether the active process is healthy, and the next action. Do not claim that a process is still running without checking its current state. If the execution environment cannot send unsolicited updates after a turn ends, explain that limitation and report whenever control returns.

### 1. Initialize and discover

```bash
python3 scripts/mysql_bug.py init-task --bug-id <ID> --description '<SYMPTOM>' --config <CONFIG>
python3 scripts/mysql_bug.py discover --bug-id <ID> --config <CONFIG>
```

Inspect the generated workspace, `state.json`, environment inventory, local source inventory, running processes, tool availability, disk/memory limits, debug symbols, core settings, and port availability. Existing mysqld processes are observation-only.

### 2. Establish official evidence

Read [references/official-source-policy.md](references/official-source-policy.md) and [references/mysql-versioning.md](references/mysql-versioning.md).

Search and preserve, in order:

1. MySQL official BUG page.
2. MySQL Reference Manual and Release Notes.
3. Official `mysql-server` tags, commits, diffs, and tests.
4. Official upstream dependency evidence when applicable.

Use current web/search tools when available. Restrict final status, affected-range, and fixed-version claims to official evidence. Secondary sources can identify search terms but cannot close the conclusion.

```bash
python3 scripts/mysql_bug.py research --bug-id <ID> --config <CONFIG>
```

Verify the saved page manually because HTML extraction is best-effort. Record reported, verified, affected, fixed, and locally tested versions separately.

### 3. Resolve and acquire versions

Use at least one affected candidate and one fixed candidate when official evidence allows. Prefer the user's version for reproduction, then the official verified version, then the nearest pre-fix release.

```bash
python3 scripts/mysql_bug.py resolve-versions --bug-id <ID> --affected-version <VERSION> --fixed-version <VERSION> --config <CONFIG>
python3 scripts/mysql_bug.py acquire-source --bug-id <ID> --version <VERSION> --config <CONFIG>
```

Local source directories are selected by internal `MYSQL_VERSION`, not their names. Missing versions are cloned from the official repository into `managed_source_root`. Do not modify existing source trees. Use a managed instrumentation copy when needed.

### 4. Build and prepare isolated instances

Read [references/build-playbook.md](references/build-playbook.md) and [references/safety.md](references/safety.md).

```bash
python3 scripts/mysql_bug.py build --bug-id <ID> --version <VERSION> --role affected --config <CONFIG>
python3 scripts/mysql_bug.py prepare-instance --bug-id <ID> --version <VERSION> --role affected --build-manifest <MANIFEST> --config <CONFIG>
```

Use independent source/build/install/data/tmp/log/core paths, ports, sockets, and PID files for each version and role. Verify `mysqld --version`, symbols, binary type, build options, and source commit. Never use a pre-existing datadir or system MySQL service.

### 5. Establish baseline

Start only the manifest-owned instance, run basic connection/DDL/DML checks, inspect its error log, then preserve baseline results.

```bash
python3 scripts/mysql_bug.py start --instance-manifest <MANIFEST>
python3 scripts/mysql_bug.py baseline --bug-id <ID> --instance-manifest <MANIFEST>
```

If baseline fails, diagnose that failure first. Do not attribute subsequent behavior to the target BUG.

### 6. Reproduce and minimize

Read [references/reproduction-scenario.md](references/reproduction-scenario.md). Build the scenario from official steps or official MTR first, then user steps, then source/patch-derived conditions.

```bash
python3 scripts/mysql_bug.py reproduce --bug-id <ID> --instance-manifest <MANIFEST> --scenario <SCENARIO.YAML> --config <CONFIG>
```

Define non-empty success criteria supported by the generic runner: `error_log_contains` or `client_completed`. Use a BUG-specific driver for signal/core, process exit, wrong result, stable wait state, replication state, corruption, or measured regression until typed runner support exists. On first success, minimize data, SQL, sessions, configuration, and time while retaining the failure.

Each logical scenario session uses one persistent `mysql` client process, so transactions, locks, temporary tables, and session variables survive across that session's SQL steps. Use separate session names for independent connections; use a BUG-specific driver only when the scenario needs protocol behavior the generic runner cannot express.

### 7. Debug dynamically

Read [references/gdb-playbook.md](references/gdb-playbook.md).

Use this order:

1. Existing error log and backtrace.
2. Existing core with matching binary/symbols/libraries.
3. GDB batch launch or attach.
4. Targeted conditional breakpoints and variable capture.
5. Minimal managed-copy instrumentation.
6. Sanitizer or controlled database failure simulation.

```bash
python3 scripts/mysql_bug.py gdb --bug-id <ID> --mode launch --instance-manifest <MANIFEST> --breakpoint <FUNCTION> --config <CONFIG>
python3 scripts/mysql_bug.py gdb --bug-id <ID> --mode attach --instance-manifest <MANIFEST> --config <CONFIG>
python3 scripts/mysql_bug.py gdb --bug-id <ID> --mode core --mysqld <MYSQLD> --core-file <CORE> --config <CONFIG>
```

Capture the earliest invalid object/state, ownership/lifetime transition, missing error check, lock/latch relationship, transaction transition, or race ordering. The final assertion/SIGSEGV/wait is usually not the root cause.

### 8. Use MTR, instrumentation, or controlled failure simulation when necessary

Read [references/mtr-playbook.md](references/mtr-playbook.md) and [references/fault-injection.md](references/fault-injection.md).

```bash
python3 scripts/mysql_bug.py mtr --bug-id <ID> --source-dir <SOURCE> --test <SUITE.TEST> --config <CONFIG>
```

Search BUG ID, error text, symbols, DBUG or Debug Sync points, and official added tests. Save every instrumentation patch and explain how it changes timing or conditions. Forced trigger evidence is L2, not natural production-frequency proof.

### 9. Analyze source and fix

Read [references/source-navigation.md](references/source-navigation.md).

Build a version-pinned chain:

`user action -> SQL/server entry -> target module -> earliest invalid state -> propagation -> final failure`

For every material source claim include version, commit, file, function, and line range. Explain normal design first. Then identify the violated invariant and why the fix prevents it. Compare source trees when helpful:

```bash
python3 scripts/mysql_bug.py source-diff --bug-id <ID> --before <AFFECTED_SOURCE> --after <FIXED_SOURCE> --config <CONFIG>
```

Do not paste a patch without semantic analysis. Determine whether the patch repairs the cause, adds defensive handling, changes synchronization/lifetime, or only changes the observed failure.

### 10. Validate the fix

Run the same minimized scenario on the candidate fixed version with equivalent configuration, data, concurrency, ordering, duration, and observation points. Confirm the trigger path was reached and the new branch/invariant held.

```bash
python3 scripts/mysql_bug.py validate-fix --bug-id <ID> --affected-manifest <AFFECTED> --fixed-manifest <FIXED> --scenario <SCENARIO> --iterations 10 --path-coverage-artifact <ARTIFACT> --config <CONFIG>
```

Pass `--path-coverage-artifact` only with an existing artifact that proves the fixed build reached the trigger path and held the repaired invariant; the validator records its SHA-256. If local validation or a fixed release is unavailable, explicitly skip `FIX_VALIDATION` with a reason and use `[官方确认]`, `[补丁推导]`, or `[待验证]` as supported—never `[实验验证]`.

### 11. Grade evidence and write reports

Read [references/evidence-rules.md](references/evidence-rules.md) and [references/report-contract.md](references/report-contract.md).

Update `metadata.json` and `state.json`, then:

```bash
python3 scripts/mysql_bug.py confidence --bug-id <ID> --config <CONFIG>
python3 scripts/mysql_bug.py report --bug-id <ID> --config <CONFIG>
```

Replace every material placeholder with a conclusion, `not available`, or `not verified` plus the attempted method and reason. Do not leave `TBD`-style content in final delivery.

## Evidence rules

Every important conclusion must carry one or more labels:

- `[实验验证]`
- `[官方确认]`
- `[源码确认]`
- `[补丁推导]`
- `[合理推断]`
- `[待验证]`

Assign L1-L5 exactly as defined in `references/evidence-rules.md`. Lower confidence when reproduction, path coverage, official fix evidence, or fixed-version verification is missing.

## Automatic execution boundaries

Automatic execution does not remove safety controls. Never:

- operate on an existing MySQL service or datadir;
- stop or restart system `mysql`/`mysqld` services;
- modify existing source for instrumentation;
- delete outside configured roots or without `.mysql-bug-skill-owned`;
- weaken host protection settings or make persistent system-policy changes;
- expose secrets in commands, evidence, or reports.

Use process-local settings, independent runtimes, managed source copies, and manifest-owned PIDs only.

## Completion gate

Before declaring completion, run:

```bash
python3 scripts/self_check.py
python3 -m unittest discover -s tests -v
python3 scripts/mysql_bug.py report-check --bug-id <ID> --config <CONFIG>
```

BUG-investigation completion requires both Markdown reports, valid evidence links, explicit limitations, evidence labels, an L1-L5 rating, and no claim presented at a stronger evidence level than its artifacts support. Skipped phases and their reasons must appear in the limitations.
