# Evidence and Confidence Rules

## Claim labels

| Label | Required basis |
|---|---|
| `[实验验证]` | Locally executed and preserved command/output proves the claim. |
| `[官方确认]` | MySQL official BUG, manual, Release Notes, source repository, or test explicitly states it. |
| `[源码确认]` | Version-pinned source directly demonstrates the behavior. |
| `[补丁推导]` | The claim is inferred from the official fix diff or added test. |
| `[合理推断]` | Multiple facts support the conclusion but no direct observation proves it. |
| `[待验证]` | A hypothesis or missing-data item. |

## Confidence levels

- **L1:** affected version reproduces; fixed version passes the same trigger; dynamic and source evidence agree.
- **L2:** MTR, instrumentation, Debug Sync, or fault injection triggers the mechanism; source/patch agrees.
- **L3:** official BUG, official fix/test, and source call chain agree; local natural reproduction is absent.
- **L4:** static source analysis explains the symptom, but dynamic or fix evidence is incomplete.
- **L5:** evidence supports only possible causes.

## Evidence integrity

- Record version, commit, build type, binary path, Build ID where available, command, cwd, environment changes, start/end time, exit code, stdout, stderr, and artifact checksum.
- Quote only the minimum official/source fragment needed. Preserve complete raw evidence separately.
- Never silently edit logs. Redact credentials in a derived copy and retain a checksum record of the source when policy permits.
- “Not reproduced” is not “not affected.” State test count, runtime, path coverage, and environment differences.
- A fix version from Release Notes is an official claim until locally validated.
- A SIGSEGV, assertion, timeout, or deadlock is a symptom. Root cause is the earliest incorrect state or violated invariant that explains it.
