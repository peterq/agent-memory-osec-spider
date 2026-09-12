---
title: 决策：下线 haisou.cc，代码保留但默认不启动
type: decision
status: active
created_at: 2026-09-03T21:20:00+08:00
updated_at: 2026-09-12T12:10:00+08:00
priority: high
keywords: [haisou, 下线, 13001, 端点级拦截, 站点放弃, keyword_haisou, 探路]
summary: haisou.cc 被站点端点级拦截且单 IP 产出上限极低，决定下线；代码保留、默认不启动、探路 cron 撤除
questions:
  - haisou 为什么下线
  - haisou 还能不能复活
load: on-demand
related:
  - agent-memory/lessons/failure-haisou搜索接口收紧.md
  - agent-memory/knowledge/domain-站点-2609接入批次.md
---

# 决策：下线 haisou.cc

## 背景

`haisou.cc` 是 2026-09-03 站点发现首轮筛出的 6 个达标站点之一，爬虫 `keyword_haisou`
当天完成开发并合并进 master，但**从未有过一条真实入库数据**：站点在同一天收紧了搜索端点。

同日经两轮归因确认（详见 [[failure-haisou搜索接口收紧]]）：

- `POST /api/v2/shares/search` 对代理池 IP 稳定返回 `13001`，**且不消耗积分**；
- 全新满额 IP 的首次请求也被拒 ⇒ 与配额无关；
- 逐一排除了请求头、HTTP/2、会话 cookie、匿名身份头；
- 用户在自己 IP 上花光 100 分（= 50 次成功搜索）后得到的是 `11003` ⇒
  **普通 IP 能搜，是代理网段被针对**；
- RDAP 查实代理是电信省级宽带秒拨段（不是机房 IP），通用 IP 纯净度库对此无效。

## 要解决的问题

继续投入 haisou，还是放弃？

## 备选方案

### 方案 A：换代理来源（住宅/未被秒拨池污染的出口）

优点：唯一可能解开 13001 的路子。

缺点：要采购成本；而且换来的产出上限被站点配额锁死——
单 IP 每日 100 积分 ÷ search 2 分 = **50 次搜索/天**，按 page_size=20 封顶 **1000 条/IP/天**。
和 misoso（626 万条 sitemap）这类站点差几个数量级，投入产出比最差。

### 方案 B：保留每日 cron 探路，等站点松绑

优点：几乎零成本（13001 不扣积分）。

缺点：需要本机常驻 `redis-topic-sync` 与 `dev_add_local_ip_to_qingting`，
两者不会开机自启，重启后探路会一直报 `unknown`，实际维护成本不为零；
且每天一封"仍被拦截"的邮件会很快被无视。

### 方案 C：下线，代码保留

优点：不再占用注意力与代理池额度；代码与逆向成果完整保留，站点若放行改个配置即可复活。

缺点：站点放行时不会自动发现，需要人工想起来。

## 最终决策

**采用方案 C。** 具体动作：

1. `services/haisou/haisou.cc.go`：把 `Enabled` 的语义**反过来**——
   与其他爬虫相反，**nil 视为关闭**，必须显式 `services.haisou.enabled: true` 才启动。
2. `config/config.go`：`HaisouConfig.Enabled` 注释标注该反向语义。
3. `spider.go`：命令描述前缀 `[已下线]`。
4. `deploy.sh`：原有注释从"暂不上线"改为"已下线"，并记下产出上限这个数字。
5. 移除本机 crontab 里的 `haisou_watch.py` 每日探路任务。

## 决策原因

拦截在积分层之前，**客户端侧任何改造都绕不开**——身份头、积分账本、节流、指纹轮换全部无效，
这一点是实测确认的，不是推测。而即使拿到解法，1000 条/IP/天的产出也排不进优先级。

## 影响

- 本批 6 站变为 **5 站可用**（dyyjmax / fuxipan / feikuai / kuakes / misoso 均已验收通过）。
- 已写的代码**不删**：`client_context.go` 里对站点匿名身份机制的逆向、`credits.go` 里
  「按积分而非按次数」的账本模式，对以后遇到同类风控设计的站点有复用价值。
- `scripts/haisou_watch.py` 保留在仓库里，只是不再定时跑；想复查时手动执行一次即可。

## 复盘条件

出现以下任一情况时重新评估：

- 有明确证据表明站点放行了代理段（例如手动跑一次 `haisou_watch.py` 得到 `released`）；
- 项目采购了新的代理来源，且顺手验证发现 haisou 可用；
- 站点提高游客额度，使单 IP 日产出量级发生变化。

## 当前状态

已执行。爬虫代码在 master 上、默认不启动、未接入 `deploy.sh`、无定时任务。
