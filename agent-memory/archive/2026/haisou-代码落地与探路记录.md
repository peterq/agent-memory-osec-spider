---
title: haisou.cc 已落地代码与常态化探路记录（已下线，归档）
type: archive
status: archived
created_at: 2026-09-12T11:35:00+08:00
updated_at: 2026-09-16T10:40:00+08:00
priority: low
keywords: [haisou, keyword_haisou, haisou_watch.py, 积分账本, 探路, 归档]
summary: haisou 下线前已写的爬虫代码（积分账本、未联网验收）与每日探路脚本的实现记录；站点已于 2026-09-03 下线，只在考虑复活 haisou 时读
questions:
  - 管理员邮件通知/cron 任务怎么发通知
  - haisou 已落地但未验收的代码在哪
load: rarely
related:
  - agent-memory/archive/2026/failure-haisou搜索接口收紧.md
  - agent-memory/decisions/decision-2026-09-03-下线haisou.md
---

# haisou.cc 已落地代码与常态化探路记录

由 `archive/2026/failure-haisou搜索接口收紧.md` 于 2026-09-12 拆出，原文保留。

### 已落地的代码（2026-09-03 傍晚，SPIDER 未提交）

用户确认「连积分账本一起写」，已实现并编译/单测通过（**联网仍无法验收**，因为 13001 未解除）：

| 文件 | 内容 |
|---|---|
| `services/haisou/client_context.go` | Go 版身份头：还原混淆公钥 + RSA-OAEP 加密 payload |
| `services/haisou/credits.go` | 积分账本 + 代理准入闸门 + status 拉取 + `BeforeSend` 头装配 |
| `services/haisou/credits_test.go` | 离线单测：公钥还原、头不可重复、IP 提取、次日零点 TTL（含 UTC 输入与 23:59:59 边界） |
| `config/config.go` | `minCredits` / `creditsRefreshInterval` / `visitorIdTTL` 三个新字段，全部有内置缺省 |
| `scripts/haisou_client_context.py`、`scripts/haisou_probe.py` | Python 版身份头 + `credits` / `curl` 两个新子命令 |

设计要点（与用户原方案的差异都在这）：

- **账本按 IP 记，不按 `ip:port`**：代理商给同一出口 IP 分不同端口，按 ip:port 会把同一份额度重复算。
- **TTL 到次日零点（东八区）**，且 `DECRBY` 后要补一次 `Expire`——跨零点时键已过期，
  DECRBY 会建出一个**没有 TTL 的负数键**，会把该 IP 永久拉黑。
- **status 刷新做了节流**（默认 30 分钟一个 IP，靠一个短 TTL 标记键）。
  用户原方案是"每次 OnProxy 都刷新"，但代理池会持续复推同一批 IP、代理 leader 只活 5 分钟，
  不节流会变成每 IP 每几秒一次真实请求。账本在两次刷新之间靠本地扣减维持。
- **扣多少以站点回传的 `meta.credits_consumed` 为准**，缺失才按常量 2 兜底，站点调价能自动跟上。
- **visitorId 按代理 IP 绑定并存 redis**（`haisou:vid:<ip>`）：额度是 ip 桶与 fingerprint 桶取小，
  换指纹拿不到更多额度，反而让同一 IP 上出现大量一次性指纹，特征更明显。
- 身份头挂在 `proxy_client.Request.BeforeSend` 上，因为它必须和**实际派发到的那个代理**绑定，
  而代理是调度时才确定的。
- `fetchCredits` 顺带校验 `anonymous_identity_type`，不是 `client_context` 就告警——
  站点换公钥时服务端不报错、只是把身份退回按 IP 识别，这是唯一能及时发现的判据。


### 常态化探路（2026-09-03 晚已上线）

`osec-spider-go/scripts/haisou_watch.py` + 本机 crontab，每天 09:30 跑一次，结果邮件通知。

    30 9 * * * \
      /home/peterq/dev/env/miniforge3/bin/python3 scripts/haisou_watch.py --proxies 3 \
      >> /tmp/haisou_watch.log 2>&1

判定口径（**`unknown` 与 `blocked` 必须分开**，这是设计上最关键的一点）：

| 结论 | 条件 | 含义 |
|---|---|---|
| `released` ✅ | 任一代理搜索成功 | 站点放行，要立刻补联网验收 |
| `blocked` ⛔ | 全部 13001 | 维持现状 |
| `quota` ⚠️ | 命中 11003 | 不该出现，说明账本或探路逻辑有问题 |
| `unknown` ❓ | 没代理 / 全网络错误 | **我们这边坏了**，不是站点的结论 |

把 `unknown` 混进 `blocked` 会让「探路早就没在跑了」这件事被无声吞掉——
同步进程一停、白名单一过期就会这样，而那恰恰是最容易发生又最难察觉的失效。

邮件通道：`POST http://cf-worker.peterq.cn/notify_admin`，
body `{"subject","htmlContent","source"}`，实测返回 `email_send_ok`。
这是本项目通用的管理员通知入口，其他 cron 任务也可复用。

⚠️ 探路依赖本机常驻的 `redis-topic-sync` 与 `dev_add_local_ip_to_qingting`，
两者**不会开机自启**，重启后探路会一直报 `unknown`。
默认每次都发邮件；嫌吵可以加 `--only-on-change`（代价是失去心跳，死掉和无变化看起来一样）。

