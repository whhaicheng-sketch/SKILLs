# GDB and Core Playbook

## General capture

```gdb
set pagination off
set confirm off
set print pretty on
set logging overwrite on
set logging enabled on
handle SIGPIPE nostop noprint pass
thread apply all bt full
info registers
```

## Crash or assertion

Capture signal, frame 0, `bt full`, arguments, locals, relevant object contents, all threads, registers, loaded libraries, and matching binary Build ID. Trace backward to the earliest invalid state.

## Hang or deadlock

Attach without changing the process, capture `info threads` and `thread apply all bt full` at least twice with an interval, and compare progress. Map waiters/holders through mutex, latch, MDL, InnoDB lock, condition variable, or I/O wait data.

## Conditional breakpoint pattern

```gdb
break target_function
condition $bpnum <predicate>
commands
  silent
  printf "key=%p state=%d\n", key, state
  bt 8
  continue
end
```

Avoid unconditional breakpoints in hot functions. Prefer conditions, command lists, or temporary instrumentation.

## Core validation

The core, mysqld, debug symbols, and shared libraries must correspond. State any mismatch. Use core analysis before trying to reproduce a crash already captured in a valid core.

## Safety

Do not weaken Yama/ptrace, SELinux, AppArmor, firewall, or system-wide core settings automatically. Prefer launching mysqld under GDB or applying process-local `ulimit` settings.
