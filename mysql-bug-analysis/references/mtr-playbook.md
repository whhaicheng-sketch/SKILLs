# MTR Playbook

## Locate relevant tests

```bash
rg -n "BUG_ID|error text|fixed function|DBUG token" mysql-test unittest
```

Inspect `.test`, `.result`, `.inc`, suite configuration, and any new test in the fix commit.

## Run narrowly

```bash
cd mysql-test
perl mysql-test-run.pl --force --retry=0 --max-test-fail=1 suite.test
```

Preserve command output and `var/log/`, `var/tmp/`, server logs, reject files, and result diffs.

## Interpretation

- An official new MTR reveals the intended trigger and expected behavior.
- A test passing on the affected version may mean wrong build, disabled feature, missing platform condition, or a different branch implementation.
- A forced DBUG/Debug Sync test is L2 evidence, not a natural production-frequency claim.
