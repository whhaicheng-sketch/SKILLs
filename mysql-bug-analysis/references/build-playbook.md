# Build and Runtime Playbook

## Build principles

- Use out-of-source builds and independent install directories per version/role.
- Default to Debug with symbols and assertions. Record all CMake options and compiler versions.
- Reuse a build only when source path, commit, generator, compiler, build type, and options match.
- Existing user source trees are not instrumented. Copy to a managed, ownership-marked tree.

## Binary verification

Run and preserve:

```bash
mysqld --version
file /path/to/mysqld
readelf -S /path/to/mysqld | grep -E 'debug|symtab'
ldd /path/to/mysqld
```

## Runtime isolation

Each version/role owns its `datadir`, `tmpdir`, error log, PID file, port, socket, and core directory. Never call `systemctl stop/restart mysql[d]`, never use `/var/lib/mysql`, and never alter the system `my.cnf`.

## Baseline

Start, connect, report `SELECT VERSION()`, run basic DDL/DML, inspect error log, and perform a clean shutdown. A baseline failure must be investigated independently.
