# Reproduction Scenario Schema

A scenario is YAML with optional setup SQL, named concurrent sessions, and non-empty explicit success criteria.

## Supported steps

- `sql`: execute inline SQL with the MySQL client.
- `sql_file`: execute a file relative to the scenario.
- `sleep`: wait seconds.
- `signal`: set a named in-process event.
- `wait_for`: wait for a named event.

## Supported success criteria

- `error_log_contains`: a non-empty list of strings that must all occur in the error log.
- `client_completed`: boolean stating whether all client sessions must complete without runner errors.

Other observations or shell/protocol actions require a reviewed BUG-specific driver and cannot be declared as generic-runner steps or criteria.

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

The runner opens one persistent client process per named session, so transactions, temporary tables, locks, and session variables survive across SQL steps. Different session names use independent connections.
