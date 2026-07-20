# Reproduction Scenario Schema

A scenario is YAML with optional setup SQL, named concurrent sessions, and explicit success criteria.

## Supported steps

- `sql`: execute inline SQL with the MySQL client.
- `sql_file`: execute a file relative to the scenario.
- `shell`: execute a shell command relative to the scenario.
- `sleep`: wait seconds.
- `signal`: set a named in-process event.
- `wait_for`: wait for a named event.

## Example

```yaml
name: ddl-race
setup:
  sql: [sql/prepare.sql]
sessions:
  session_a:
    steps:
      - sql: "START TRANSACTION"
      - sql_file: sql/query.sql
      - signal: query_started
      - wait_for: ddl_done
  session_b:
    steps:
      - wait_for: query_started
      - sql_file: sql/ddl.sql
      - signal: ddl_done
success_criteria:
  error_log_contains: ["mysqld got signal 11"]
```

The runner opens a new client process for each SQL step. For a transaction that must persist across statements, place all statements in one SQL step/file or create a BUG-specific driver script. Record manual session timing in the reproduction report.
