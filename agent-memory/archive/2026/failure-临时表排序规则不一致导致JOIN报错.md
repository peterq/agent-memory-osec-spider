---
title: 失败经验：临时表未指定排序规则导致 UPDATE ... JOIN 报 ERROR 1267
type: lesson
status: archived
created_at: 2026-09-06T09:40:00+08:00
updated_at: 2026-09-12T23:20:00+08:00
priority: high
keywords:
  - MySQL
  - collation
  - ERROR 1267
  - Illegal mix of collations
  - 临时表
  - utf8mb4_general_ci
  - utf8mb4_0900_ai_ci
  - lc_rollback_repair_marked
  - 生产回滚脚本
summary: MySQL 8 里 CREATE TEMPORARY TABLE 不写 COLLATE 会继承服务器默认 utf8mb4_0900_ai_ci, 与建表为 utf8mb4_general_ci 的业务表 JOIN 时报 ERROR 1267
load: rarely
related:
  - agent-memory/lessons/failure-repair对账在bootstrap未完成时误标数据.md
---

# 失败经验：临时表排序规则不一致导致 JOIN 报错

## 问题背景

2026-09-06 回滚 repair 作业 `id=9` 误标的 14.7 万行时，
`SPIDER/scripts/lc_rollback_repair_marked.sh --execute` 在**第 1 批**就失败。
该脚本的 dry-run（纯 `SELECT`）此前一路正常，掩盖了问题。

## 失败方法

```sql
CREATE TEMPORARY TABLE tmp_rb (id CHAR(32) PRIMARY KEY);   -- 没写 COLLATE
...
UPDATE `res_lc_bnd_00` t JOIN tmp_rb r ON t.id=r.id ...
```

## 失败表现

```text
ERROR 1267 (HY000) at line 8: Illegal mix of collations
(utf8mb4_general_ci,IMPLICIT) and (utf8mb4_0900_ai_ci,IMPLICIT) for operation '='
```

## 根本原因

- 业务表 `res_lc_*` 的 DDL 是 `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci`
  （见 `PRD/res-lifecycle/sql/res_lc_schema.sql`）。
- 生产是 **MySQL 8**，服务器默认排序规则是 `utf8mb4_0900_ai_ci`。
- `CREATE TEMPORARY TABLE` 不显式指定时**继承服务器默认值**，不会跟随被 JOIN 的业务表。
- 两个 IMPLICIT 排序规则做 `=` 比较，MySQL 无法裁决，直接报错。

## 规避方法

临时表列显式带上业务表的排序规则：

```sql
CREATE TEMPORARY TABLE tmp_rb (id CHAR(32) COLLATE utf8mb4_general_ci PRIMARY KEY);
```

已修入 `SPIDER/scripts/lc_rollback_repair_marked.sh`（SPIDER `82ef0d8`）。

## 下次行动建议

1. **凡是"临时表 + JOIN 业务表"的运维 SQL，临时表一律显式写 COLLATE**，不要依赖默认值。
2. **dry-run 只跑 SELECT 是不够的**：它验证不了写路径的 SQL。
   设计运维脚本时，写路径至少要能用 `--batch 1` 之类的方式做一次最小真实试跑。
3. 失败后**先判定有没有写入再决定要不要重试**：本次 SQL 用
   `START TRANSACTION` 开头、错误发生在 `COMMIT` 之前，mysql 客户端遇错即退出、会话关闭触发隐式回滚，
   因此**零写入**；重跑时 recon 的目标行数仍是 147,424，这就是"没写进去"的确证。

## 适用边界

MySQL 8 + 老库沿用 `utf8mb4_general_ci` 的场景最典型（升级上来的库都这样）。
MySQL 5.7 默认就是 `utf8mb4_general_ci`，同样的脚本在 5.7 上不会暴露这个问题。
