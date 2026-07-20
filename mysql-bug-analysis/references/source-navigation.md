# MySQL Source Navigation

## Common entry areas

| Area | Typical paths |
|---|---|
| SQL parsing/execution | `sql/sql_parse.cc`, `sql/sql_class.*`, `sql/sql_*` |
| Handler interface | `sql/handler.*` |
| Data dictionary | `sql/dd/` |
| Metadata locking | `sql/mdl.*` |
| Replication | `sql/rpl_*`, `sql/binlog.*` |
| InnoDB | `storage/innobase/` |
| InnoDB handler bridge | `storage/innobase/handler/ha_innodb.cc` |
| InnoDB row operations | `storage/innobase/row/` |
| Recovery/log | `storage/innobase/log/`, `storage/innobase/recv/` where present |
| MySQL system utilities | `mysys/` |
| Server tests | `mysql-test/` |
| Unit tests | `unittest/` |

## Investigation pattern

1. Start from error text, assertion, symbol, SQL command class, or official patch.
2. Use `rg -n` for BUG ID, error text, function, DBUG token, and test name.
3. Build a version-pinned call chain from user entry to earliest invalid state.
4. Track object ownership, lifetime, transaction state, locks/latches, reference counts, error returns, and cleanup order.
5. Compare pre-fix and fixed code plus the official test. Explain the semantic change rather than pasting the diff.

## Citation format

Always include version, commit, file, function, and line range. Line numbers alone are unstable.
