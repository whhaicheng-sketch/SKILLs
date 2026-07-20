# Workflow

## State machine

`DISCOVER -> RESEARCH -> VERSION_RESOLUTION -> PREPARE -> BASELINE -> REPRODUCE -> DEBUG -> SOURCE_ANALYSIS -> FIX_VALIDATION -> CONCLUSION -> REPORT`

## Phase contracts

### DISCOVER

Input: BUG ID, URL, symptom, logs, core, SQL, version, or source path.  
Actions: validate config; create ownership-marked workspace; capture OS/tool/source inventory; inspect running mysqld processes without changing them.  
Exit: workspace and environment evidence exist. Missing compile/debug capability changes the mode to limited analysis; it does not justify guessing.

### RESEARCH

Actions: preserve the official BUG page, Reference Manual, Release Notes, official source/commit, official MTR, and linked BUGs. Extract reported, verified, affected, and fixed version statements separately.  
Exit: at least one official evidence source exists, or the report explicitly states that no public official BUG was found.

### VERSION_RESOLUTION

Determine roles: `suspected`, `affected`, `fixed`; when possible, `last_known_good`, `first_known_bad`, and `first_fixed`. Verify version from `MYSQL_VERSION`, `mysqld --version`, and Git commit rather than directory names.

### PREPARE

Acquire missing official tags into `managed_source_root`; build each role in independent build/install directories; initialize independent runtime directories, ports, sockets, logs, PID files, and core locations. Existing source trees remain read-only. Instrumentation uses a managed copy.

### BASELINE

Prove each instance starts, accepts a connection, executes basic DDL/DML, and shuts down normally. A failed baseline blocks BUG attribution.

### REPRODUCE

Start from official steps or official MTR, then user steps, then a minimized scenario. Save every command, SQL result, server log, timeout, process status, and success criterion. After first success, remove unnecessary data, SQL, concurrency, and configuration.

### DEBUG

Use this order: error log/backtrace -> core -> GDB batch -> targeted interactive GDB -> source instrumentation -> sanitizer -> controlled fault injection. Capture the earliest invalid state, not only the terminal crash.

### SOURCE_ANALYSIS

Explain normal design, invalid-state creation, missing validation/synchronization/lifetime protection, propagation, and user-visible failure. Distinguish root-cause location, propagation location, and final failure location.

### FIX_VALIDATION

Run the same minimized scenario against the candidate fixed version with equivalent configuration, data, concurrency, ordering, duration, and observation points. “Did not crash” is insufficient unless the trigger path was reached.

### CONCLUSION

Assign L1-L5 using `references/evidence-rules.md`. Tag each claim as `[实验验证]`, `[官方确认]`, `[源码确认]`, `[补丁推导]`, `[合理推断]`, or `[待验证]`.

### REPORT

Generate exactly two primary Markdown deliverables. Populate every material section; retain failed experiments and limitations. Run the report quality gate in `references/report-contract.md`.

## Degradation chain when natural reproduction fails

1. Recheck OS, architecture, compiler, build type, filesystem, configuration, data scale, concurrency, and timing.
2. Run or reconstruct the official MTR.
3. Add minimal logging or conditional GDB breakpoints.
4. Use Debug Sync/DBUG or a controlled sleep to expose the race window.
5. Perform controlled I/O, allocation, network, process, or timing fault injection.
6. Reverse-engineer the repair from the official patch and test.
7. Perform static call-chain analysis and lower confidence.

Never stop at “cannot reproduce” while source, patch, MTR, or official evidence can still answer the mechanism. Never convert a theoretical path into an experimental claim.
