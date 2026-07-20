---
title: "MySQL Bug #{{BUG_ID}} 复现与调试报告"
bug_id: "{{BUG_ID}}"
analysis_date: "{{ANALYSIS_DATE}}"
affected_versions: "{{AFFECTED_VERSIONS}}"
fixed_versions: "{{FIXED_VERSIONS}}"
reproduction_status: "{{REPRODUCTION_STATUS}}"
fix_validation_status: "{{FIX_VALIDATION_STATUS}}"
---

# MySQL Bug #{{BUG_ID}} 复现与调试报告

## 1. 文档目标

本文档指导不了解该 BUG 的工程师，从环境检查开始，完成源码编译、隔离实例初始化、BUG 复现、GDB/core 调试和修复版本验证。

## 2. 实验结果摘要

| 版本 | 角色 | 预期现象 | 实际结果 |
|---|---|---|---|
| {{AFFECTED_VERSIONS}} | affected | 触发 BUG | {{REPRODUCTION_STATUS}} |
| {{FIXED_VERSIONS}} | fixed | 不再触发且执行到修复路径 | {{FIX_VALIDATION_STATUS}} |

## 3. 实验环境

### 3.1 操作系统、CPU、内存和文件系统

### 3.2 编译器、CMake、GDB 和 Git

### 3.3 源码 Commit 与构建参数

### 3.4 目录、端口和 Socket 规划

| 项目 | affected | fixed |
|---|---|---|
| 源码目录 | 待补充 | 待补充 |
| 构建目录 | 待补充 | 待补充 |
| 安装目录 | 待补充 | 待补充 |
| 数据目录 | 待补充 | 待补充 |
| 端口 | 待补充 | 待补充 |
| Socket | 待补充 | 待补充 |

## 4. 前置检查

对每个命令说明用途、预期输出和异常处理。

```bash
python3 scripts/mysql_bug.py config-check --config ~/.codex/mysql-bug-skill.yaml
python3 scripts/mysql_bug.py discover --bug-id {{BUG_ID}} --config ~/.codex/mysql-bug-skill.yaml
```

## 5. 获取并验证源码

```bash
python3 scripts/mysql_bug.py acquire-source --bug-id {{BUG_ID}} --version <VERSION> --config ~/.codex/mysql-bug-skill.yaml
```

记录源码内部版本、Git Commit、分支和工作区状态。

## 6. 编译 Debug 版本

```bash
python3 scripts/mysql_bug.py build --bug-id {{BUG_ID}} --version <VERSION> --role affected --config ~/.codex/mysql-bug-skill.yaml
```

说明 Debug Build、符号验证、常见依赖失败和实际构建日志位置。

## 7. 初始化隔离实例

```bash
python3 scripts/mysql_bug.py prepare-instance --bug-id {{BUG_ID}} --version <VERSION> --role affected --build-manifest <PATH> --config ~/.codex/mysql-bug-skill.yaml
```

不得使用现有生产或测试实例的数据目录。

## 8. 建立正常基线

```bash
python3 scripts/mysql_bug.py start --instance-manifest <PATH>
python3 scripts/mysql_bug.py baseline --bug-id {{BUG_ID}} --instance-manifest <PATH>
```

基线失败时停止，不得把环境错误认定为目标 BUG。

## 9. 最小复现场景

### 9.1 场景文件

```yaml
name: minimal-reproduction
setup:
  sql:
    - sql/prepare.sql
sessions:
  session_a:
    steps:
      - sql: "START TRANSACTION"
      - signal: a_ready
      - wait_for: b_done
  session_b:
    steps:
      - wait_for: a_ready
      - sql_file: sql/session-b.sql
      - signal: b_done
success_criteria:
  error_log_contains:
    - "expected error signature"
```

### 9.2 自动执行

```bash
python3 scripts/mysql_bug.py reproduce --bug-id {{BUG_ID}} --instance-manifest <PATH> --scenario <SCENARIO.YAML>
```

### 9.3 手工会话时间线

| 时间 | 会话 | 动作 | 预期状态 |
|---:|---|---|---|
| T1 | A | 待补充 | 待补充 |

### 9.4 复现成功判据

明确进程退出、错误日志、错误结果、超时、线程状态或数据校验标准。

## 10. GDB 启动式调试

```bash
python3 scripts/mysql_bug.py gdb --bug-id {{BUG_ID}} --mode launch --instance-manifest <PATH> --breakpoint <FUNCTION>
```

关键命令：`bt full`、`info args`、`info locals`、`thread apply all bt full`。

## 11. GDB 附加式调试

```bash
python3 scripts/mysql_bug.py gdb --bug-id {{BUG_ID}} --mode attach --instance-manifest <PATH>
```

说明 ptrace 限制。不得自动关闭系统安全策略。

## 12. Core Dump 分析

```bash
python3 scripts/mysql_bug.py gdb --bug-id {{BUG_ID}} --mode core --mysqld <PATH> --core-file <PATH>
```

记录 Build ID、二进制、共享库和 core 是否匹配。

## 13. MTR、插桩和故障注入

正常复现失败时依次尝试：官方 MTR、Debug Sync/DBUG、最小插桩、扩大竞态窗口、隔离实例内的受控异常状态模拟。所有修改必须保存 patch，并标记证据等级。

## 14. 修复版本验证

使用完全相同的 SQL、配置、并发度、数据量、顺序和超时。说明执行次数，并证明执行到修复代码路径。

## 15. 实验结果对比

| 观察项 | affected | fixed | 结论 |
|---|---|---|---|
| 触发次数/总次数 | 待补充 | 待补充 | 待补充 |
| 调用路径 | 待补充 | 待补充 | 待补充 |
| 错误日志 | 待补充 | 待补充 | 待补充 |

## 16. 环境清理

只允许清理由 Skill 创建且包含 `.mysql-bug-skill-owned` 标记的目录。

```bash
python3 scripts/mysql_bug.py cleanup --bug-id {{BUG_ID}} --target runtime --config ~/.codex/mysql-bug-skill.yaml
```

## 17. 常见问题

覆盖编译失败、Boost、GDB 无符号、core 未生成、端口占用、Socket 连接失败、竞态无法触发及 Debug/Release 差异。

## 18. 证据索引

工作目录：`{{WORKSPACE}}`

{{EVIDENCE_TABLE}}
