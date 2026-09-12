---
title: 成功经验：打通本地开发的 IP 代理池
type: lesson
status: active
created_at: 2026-09-03T17:30:00+08:00
updated_at: 2026-09-12T12:10:00+08:00
priority: high
keywords: [代理池, 蜻蜓代理, 白名单, redis-topic-sync, 出口IP, localIp, 重复推送, 秒拨, 住宅宽带, RDAP, 蜻蜓]
summary: 本地怎么用上代理池、三个会让人查错方向的坑，以及验证方法
questions:
  - 代理池连不上怎么办，本地怎么用上代理池
  - 蜻蜓白名单/出口IP不对怎么查
load: on-demand
related:
  - agent-memory/procedures/workflow-站点发现.md
---

# 打通本地开发的 IP 代理池

## 问题

项目硬规则要求分享链接爬虫一律走代理池。但本地开发默认拿不到代理，
表现是「代理全部连不上（`ProxyError`）」或「频道里一个代理都收不到」。

## 正确做法（两件事都要做，缺一不可）

```bash
# ① 把本机公网 IP 加进蜻蜓白名单（常驻，每分钟同步一次）
cd osec-spider-go && go run . dev_add_local_ip_to_qingting &

# ② 把生产 redis 的代理频道同步到本地（= GoLand 运行配置 sync-redis）
python3 enfi-resource-common/site-discovery/tools/proxypool.py start
```

链路：生产 `proxy-provider` 校验后发布到生产 redis 频道 `proxy_subject`
→ `tools/redis-topic-sync` 经 ssh 隧道订阅并转发
→ 本地 redis `127.0.0.1:6379/2` 同一频道 → 本地爬虫/工具订阅。

## 三个会让人查错方向的坑

### 1. 取公网 IP 必须用境内接口

蜻蜓代理按 **IP 白名单**鉴权。开发机装了 TUN 透明代理时会同时存在**多个出口 IP**：
境外目标走代理出口、境内目标走直连出口。实测同一台机器上
`api.ipify.org` / `v4.ident.me` 给出的是代理出口，与境内接口的结果**不是同一个 IP**。

蜻蜓节点都在境内，白名单要的是境内出口那个。用错了**日志里看不出任何异常**，
只表现为「代理全部连不上」——极易误判成「代理池坏了」。

`localIp()` 已改为只用 `ddns.oray.com`、`members.3322.org`、`test.ustc.edu.cn`
三个境内接口并取多数派（原来那个 `112.124.34.135:8103` 已不可用，且单点挂掉
就让整个白名单同步失效）。

### 2. 蜻蜓凭据的正本在 init() 里，不在那两处显眼的常量

`services/proxy-provider/change_proxy_config.go` 的 `init()` 会**覆盖**
`proxy-provider.go` 里硬编码的 `qtWhitelistLink` 和 config yaml 里的
`providers[].conf`。

只看那两处旧常量去测，会得到 `code 20014 代理订单异常` / `code 422 token 不存在`，
从而误判成「仓库里的凭据全过期了、生产用的是另一套」——**这个结论是错的**，
我第一次排查就栽在这里。排查凭据问题先看 `init()`。

### 3. 数同步进程要按实例数，不是进程数

一个同步实例会派生 **4 个**能匹配到 `redis-topic-sync` 的进程：
`go run` 包装进程、编译出的二进制、`sh -c ssh`、`ssh` 本身。

按进程数去数会把 1 个实例误报成 2 个，进而假报「重复推送」。
只认 argv[0] 的 basename 恰好是 `redis-topic-sync` 的那一个
（`proxypool.parse_sync_pgrep()`，有单测锁住）。

**为什么要数**：每多跑一个同步进程，同一个代理 IP 就会被重复推送一次，
代理池规模虚高，且对同一 IP 的实际请求频率成倍上升，更容易被目标站封。
所以启动前必须先检测已有实例。

## 验证方法

```bash
python3 site-discovery/tools/proxypool.py status          # 同步进程 + 频道实时收包
python3 site-discovery/tools/pancheck.py --file links.txt --require-proxy
```

[实测 2026-09-03] 白名单生效后频道推来的代理 **6/6 全部可用**，
`pancheck --require-proxy` 三条样本 0 unknown，结论与直连基线一致。

## 注意事项

- 代理池是 pub/sub 持续喂的，**刚启动时天然是空的**，判就绪必须带等待
  （`ProxyPool.wait_ready()`），用瞬时 `size()==0` 去守卫会误杀。
- 现行凭据在 `change_proxy_config.go`，该文件**是 gitignore 的**（没进 git，处理得当）。
  仓库里留着的是**过期**凭据（`proxy-provider.go` 的常量、config yaml 的 conf URL），
  正是它们把排查带偏的。
- SPIDER 有 6 处源码故意 gitignore（`captcha/`、`services/keyword/fuck0fy/`、
  `tools/sync-sak/`、`tools/sync-old-index/`、`devops_online_env.go`、
  `change_proxy_config.go`），**全新 clone/worktree 编译不过**。
  开 worktree 用 `osec-spider-go/scripts/new_worktree.sh`，它会一并补齐。

## 代理池的真实形态：住宅宽带秒拨池，不是机房 IP（2026-09-03 RDAP 实测）

此前多处记着「蜻蜓＝机房 IP，可能整段被标记」，**这是错的**。对池子里的 IP 做 RDAP 查询：

| IP | 注册网段 | 归属 |
|---|---|---|
| 119.101.54.192 | 119.96.0.0/13 | CHINANET-HB 湖北电信 |
| 218.86.67.52 | 218.85.0.0/15 | CHINANET-FJ 福建电信 |
| 140.250.147.83 | 140.250.0.0/16 | CHINANET-SD 山东电信 |
| 49.87.0.119 | 49.64.0.0/11 | CHINANET-JS 江苏电信 |
| 27.152.127.141 | 27.152.0.0/17 | Quanzhou Broadband MAN 泉州宽带城域网 |

全是**电信省级宽带/城域网**，也就是家宽 PPPoE 拨号池（"秒拨"），不是 IDC 机房段。

**这条更正会改变结论的走向**：

- 通用的「代理/VPN/机房检测」类数据库对这些 IP 大概率判**低风险、住宅**——
  因为按 ASN 和网段性质它们确实就是住宅。指望这类库预筛出"哪个 IP 会被 haisou 拒"是不现实的。
- 只有专门追踪**住宅代理网络**的厂商（Spur.us 一类）才有可能识别，且都是商业付费。
- 站点更可能是**按行为**把这些秒拨段拉黑的（这些池子被爬虫反复复用），
  这种黑名单没有公开数据库能镜像。

**最便宜也最准的判据其实是站点自己**：13001 不消耗积分，所以对每个新 IP 发一次搜索探路是**零成本**的，
结果比任何第三方分数都准。要做 IP 预筛就用观测结果建黑名单（redis 记 IP → 拒绝时间），
不要引入第三方纯净度库。

**可迁移教训**：判断代理是不是"机房 IP"要查 RDAP 的网段归属，不要凭代理商的品类名脑补。
判错了会把排查方向整个带偏（"换住宅代理"这个建议其实是原地打转，因为用的就已经是住宅 IP）。

（本节由 `lessons/failure-haisou搜索接口收紧.md` 迁入，2026-09-12）
