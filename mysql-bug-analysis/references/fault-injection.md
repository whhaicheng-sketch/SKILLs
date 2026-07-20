# Instrumentation and Controlled Failure Simulation

Use only after natural reproduction and official MTR attempts.

## Preferred order

1. Conditional GDB breakpoint and logging.
2. Existing DBUG or Debug Sync point.
3. Minimal source log with function, object identity, state, and thread.
4. Controlled sleep to widen a verified race window.
5. Scoped I/O, allocation, connection, or process failure inside the owned test instance.
6. Sanitizer build when the suspected defect matches the sanitizer and overhead is acceptable.

## Requirements

- Instrument only a managed copy.
- Save the exact patch, build manifest, and scenario.
- Explain how the simulation changes timing or conditions.
- Confirm the unmodified fixed version no longer enters the faulty path.
- Remove instrumentation from final fix verification unless it is an observation-only probe applied equivalently.
