# MySQL Version Resolution

## Roles

- `reported`: reporter's version.
- `verified`: version where MySQL developers confirmed the issue.
- `affected`: local version selected to demonstrate the problem.
- `fixed`: candidate release containing the repair.
- `last_known_good`, `first_known_bad`, `first_fixed`: optional boundary evidence.

## Resolution procedure

1. Parse the official BUG and Release Notes.
2. Locate commit/test references and identify target branches.
3. Scan local source trees by internal `MYSQL_VERSION` content.
4. Verify Git commit and dirty state.
5. Verify built binary with `mysqld --version`, `file`, and debug sections.
6. If boundaries remain unclear, test adjacent versions or bisect a managed Git tree.

## Tag convention

Official release tags generally use `mysql-X.Y.Z`. Verify tag existence before cloning. Never synthesize an affected range solely from one reported version.

## Cross-series cautions

MySQL 5.7, 8.0, 8.4 LTS, and Innovation releases can differ in CMake options, source layout, data dictionary behavior, MTR suites, defaults, and upgrade rules. Load version-specific build options from YAML and document any adaptation.
