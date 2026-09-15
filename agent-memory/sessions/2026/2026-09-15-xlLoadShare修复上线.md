---
title: 会话：xlLoadShare 失败率修复上线与历史失败重投
type: session
status: active
created_at: 2026-09-15T09:25:00+08:00
updated_at: 2026-09-15T09:25:00+08:00
priority: medium
keywords: [xlLoadShare, 迅雷, 修复上线, xl-fail-export, 重投, dry run]
summary: 09-15 上午把迅雷分享爬取三处缺陷修复并上线两台机，从 SLS 导出 7 天内 288 条失败分享重投；失效上报按不可逆清单先 dry run
load: rarely
related:
  - agent-memory/knowledge/domain-迅雷分享爬取.md
  - agent-memory/procedures/checklist-不可逆操作上线.md
---

# 会话：xlLoadShare 失败率修复上线（2026-09-15）

## 完成事项
- SPIDER `3270e10` 修客户端/消费者/网关码表引用；`12e733b` 新增 `tools/xl-fail-export`。
- 本地代理池联网测试 5 例全过（顶层文件/文件夹回归/空文件夹/DELETED/PASS_CODE_ERROR）。
- `deploy.sh deploy xunlei` 在 osec-restest 上 ssh 超时卡死 → 改为逐机 `scp` + `call redeployHost xunlei <host>`，jenkins 08:51、resngix 08:58 上线；restest 后台脚本持续重试。
- 从 SLS 导出 288 条"无临时文件"失败分享（含 pwd），`lc-recrawl -rate 10` 全部投递；5 分钟内入库 173、空分享 78。

## 关键发现 / 经验
- 整体 `deploy.sh deploy <svc>` 遇到一台机 ssh 挂死会卡住全部；逐机 scp + `redeployHost` 可绕过，但注意 `deploy()` 先 `mv spider spider.old` 再 scp，scp 失败会留下**远端无 spider 二进制**的状态，须补 scp（本次 resngix 实测）。
- SLS `queueName`/`link_key` 不是索引键，`SearchLogs` 查询只能全文短语匹配（`"xunleipan:<id>"`）。
- `pkill -f <脚本名>` 在同一条 Bash 命令里会自匹配把自己杀掉（exit 144），要拆成两条命令或用 `pgrep -f 'nam[e]'` 且命令行里不再出现原名。
- 联网集成测试需要 `LOCAL_CONFIG_PATH` 指向含 `services.proxy`(redis 本地 db2, 频道 `proxy_subject`) 的最小 yaml，go test 空配置会 panic `services.proxy.redis 未配置`。

## 后续行动
- restest 部署完成确认；dry run 清单复核后由用户决定开启失效上报；6h 后补投一次。
