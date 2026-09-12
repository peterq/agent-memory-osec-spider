---
title: 生产 ES 资源索引现状（2026-09-04 实测）
type: knowledge
status: active
created_at: 2026-09-05T00:30:00+08:00
updated_at: 2026-09-12T12:10:00+08:00
priority: high
keywords: [ES, Elasticsearch, 6.7, 无join, nested filelist, 百度存量, enfi_resource_v6, resource 别名, join 父子, 墓碑, docs.deleted, 分片, 容量, 入库速率, es_survey]
summary: 阿里云 ES 6.7 单索引的分片/容量/父子文档结构/入库增速与读写清理链路代码位置，是生命周期改造方案的事实基线
questions:
  - 生产 ES 有多大，怎么查生产 ES
  - 无 join 索引和 join 父子索引的区别
load: on-demand
related:
  - agent-memory/knowledge/architecture-storage.md
  - agent-memory/knowledge/architecture-api.md
  - agent-memory/decisions/decision-2026-09-04-资源索引生命周期改造方案.md
---

# 生产 ES 资源索引现状（2026-09-04 实测）

复跑体检：`osec-spider-go/scripts/es_survey.sh`（经 osec-res1 跳板，本机不能直连 ES；地址含凭据只在
`osec-spider-go/_note/config/spider.gateway.prod.yaml` 的 `es_addr`，**不要写进记忆**）。

## 集群
- [事实] 阿里云 ES **6.7.0**（lucene 7.7），5 个 data 节点（角色 mdi），每节点 heap 14.3GB / 磁盘 688GB，
  已用 31~33%，全集群可用约 2.3TB。集群 green。
- [事实] 无自定义 index template（只有阿里云默认模板）。

## 唯一业务索引 `enfi_resource_v6_250822`（别名 `resource`）
- [事实] 5 主分片 **0 副本**，store 1104GB（单分片 ~220GB）；`refresh_interval 60s`，`merge max_thread_count 1`。
- [事实] docs.count 15.76 亿，**docs.deleted 5.93 亿（≈27% 墓碑）**，468 个 segment，存在 57GB 巨段。
- [事实] **两种文档形态并存**：
  ① **join 父子结构** `resource → file`：资源父文档 1530 万（quark 95%：1454 万；aliyundrive 52 万；
  xunleipan 23 万；baidu 948），文件子文档 **12.2 亿**（平均每资源 ~80 个），子文档 `_routing=父 id`、
  `_id=md5(父id+path)`、`type=<父type>-file`（quark/aliyundrive/xunleipan 走此形态）。
  ② **无 join 字段的父文档 2966 万**（baidu 2905 万 + torrent 6 万），文件清单在 **nested `filelist`**（nested 内部文档 3.08 亿）。
  百度资源至今仍走 STORAGE `UpsertResource` 小资源路径写入（2025 年 164 万、2026 年 108 万），父文档不带 join；
  2013~2016 年的百度老数据约 2150 万，大概率大面积失效。
  → **真实资源总量 ≈ 4440 万**，文档对账：1530 万 + 12.22 亿子文档 + 2966 万 + 3.08 亿 nested ≈ 15.76 亿。
  ⚠️ 只按 `join=resource` 统计会漏掉三分之二的资源，v3 搜索/迁移必须同时处理两种形态。
- [事实] ES 里 `type` 值是 `baidu/aliyundrive/quark/xunleipan`，与 `spider_contract` 常量
  （`bnd/ali-share/quark/xunleipan`）**不同**。
- [事实] mapping 脏字段很多（`-`、`baiduUser`、`createTime` 等），`file_count/size/expires` 以字符串写入。
- [推算] 单资源平均占 ES ≈ 72KB（含子文档）；入库 2025-06 起每月 45~95 万资源 ≈ 60~70GB/月。
  utime 早于 90 天前的资源 ≈ 1266 万，近 90 天 ≈ 264 万。
- [事实] `terms` 查询父 join 字段 `join#resource` 可批量按父 id 命中子文档（已实测），`_reindex` 默认保留 routing。

## 读写清理链路代码位置
| 环节 | 位置 |
|---|---|
| 父文档写入 | STORAGE `services/save-worker/es.go`（Bulk，先按 version terms 判重） |
| 父+子文档流式写入 | STORAGE `services/gateway/gateway.go` `UpsertBigResource`（join、routing、`pending-<ts>` 中间 version） |
| 搜索 | API `services/search/search.go`（`SearchV2` 用 `has_child(file)`；`GetFileCtx` 用 routing） |
| 搜索时失效删除 | API `services/valid/valid.go` `deleteInvalid`（DeleteByQuery ids + parent_id） |
| 存量清理 | SPIDER 网关 `services/gateway/res_scheduler/clear_expire.go`（`clearExpire` 队列，写 MySQL `invalid_link_*`） |
| 存量检测生产者 | SPIDER `services/devops/clear_expire/`（dump ES → 文件 → `checkExpire:<type>` 队列 → 代理池探测），deploy 条目 `url_commit_check`/`url_check` |
| 索引名配置 | API `config.prod.yaml` `elastic.enfiresourceindex`；STORAGE `services.storage.es_resource_index`；网关 `gw_config.EsResourceIndex`，值都是别名 `resource` |

## 网关 MySQL（download_scheduler 在用）
- [事实] 阿里云 PolarDB MySQL 8.0.13，库 `prod-osec-spider`，44 张表共 132GB；最大表
  `download_share_file_ali_250111-all-pdf` 7100 万行 77GB。DSN 在 `gw_config.Mysql`（配置文件同上，不写值）。
- [事实] 分表惯例在 `services/gateway/spider_dao/spider_dao.go` `tableName`：按类型后缀
  （`resTableMap`: bnd/xunlei/quark/ali）+ 分组名动态拼表名，`AutoMigrate` 按表名建表，`sql_util.BatchUpsert` 批量写。
- [事实] 从 osec-res1 用 `mysql` 客户端可直连（DSN 口令含 `@`，shell 解析时要按 `@tcp(` 切分）。
