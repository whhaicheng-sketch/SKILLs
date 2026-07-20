# Safety Boundaries

Automatic execution is allowed only inside configured managed roots.

## Never perform automatically

- Stop, restart, reconfigure, or delete an existing MySQL service or instance.
- Use or remove `/var/lib/mysql`, `/var/lib/mysqld`, `/`, `/etc`, or `/usr` as a managed directory.
- Modify an existing source tree for instrumentation.
- Remove a directory without root-containment validation and `.mysql-bug-skill-owned`.
- Disable SELinux, AppArmor, firewall, ptrace protection, or other system security.
- Remove OS packages or make persistent kernel/security changes.
- Expose passwords in commands, reports, logs, or copied evidence.

## Allowed

- Create independent workspaces, managed source copies, builds, installs, and runtimes.
- Use process-local resource limits and environment variables.
- Download official source tags when enabled.
- Start/stop only the exact PID from an ownership-marked instance manifest.
