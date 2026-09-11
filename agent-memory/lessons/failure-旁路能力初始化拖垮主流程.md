---
title: 失败经验：旁路能力(监控/埋点)的初始化把所有子命令拖垮
type: lesson
status: active
created_at: 2026-09-09T00:25:00+08:00
updated_at: 2026-09-09T00:25:00+08:00
priority: high
keywords: [db.Redis, log.Fatal, panic, 监控初始化, 旁路能力, 降级, proxy_monitor, spider.go, 配置按服务拆分, 埋点覆盖]
summary: 用会 log.Fatal/panic 的基础设施函数去初始化"可有可无"的监控, 会让每个子命令随配置缺失或 redis 抖动一起死; 以及埋点只覆盖成功路径会让最严重的故障隐形
load: on-demand
related:
  - agent-memory/lessons/failure-配置v2二进制无本地回落导致老容器重启即挂.md
  - agent-memory/lessons/failure-resdb的ES端点指向已下线集群.md
  - agent-memory/sessions/2026/2026-09-08-并行四任务监控与文档爬虫上云.md
---

# 失败经验：旁路能力的初始化拖垮主流程

## 问题背景

2026-09-08 给代理池加监控上报（`illuminate/proxy-monitor`）。设计上它是纯旁路：
业务不依赖它，它挂了不该影响任何爬虫。子 Agent 在 `spider.go` 的命令分发前加了一行
进程级初始化。

## 失败方法

```go
if err := proxy_monitor.Init(db.Redis(config.Config.Services.Proxy.Redis), config.Hostname); err != nil {
    log.Println("proxy_monitor init error:", err)   // 这行永远等不到执行
}
```

看起来"失败只打日志不阻断"，实际上：

- `db.Redis(name)` 对 **`redises` 配置里没有这个名字**是 `log.Fatal`（整个进程退出）；
- 对 **连不上 redis** 是 `panic`（`_, e := rds.Get("test")` 之后直接 panic）；
- 两种情况都在 `Init` 被调用**之前**发生，`err` 分支形同虚设。

## 失败表现（未上线，代码审查阶段拦下）

2026-09-08 刚做完「配置按服务拆分为网关/爬虫两份」，**网关那份配置没有 `services.proxy` 节**
→ `Services.Proxy.Redis == ""` → `log.Fatal("redises 配置里没有这一项: ")`
→ **网关一启动就退出**。爬虫侧则会在 redis 抖动时集体 panic。

讽刺的是，同一个功能的**读取侧** `services/gateway/proxy_admin/redis_resolve.go` 把这道防线
写得很完整，注释里还专门写了"不直接调用 db.Redis(名字不存在会 log.Fatal 整个进程)"——
**知道危险不等于每一处都防住了**。

## 根本原因

1. 把"可有可无的旁路能力"接到了一个**为主流程设计的、失败即致命**的基础设施函数上。
   `db.Redis` 的 Fatal/panic 语义对"没这个 redis 就跑不了"的主流程是合理的，
   对监控是灾难。
2. 初始化被放在**所有子命令共用**的路径上，把爆炸半径从"用代理的爬虫"扩大到"每一个进程"。
3. 配置形态刚发生变化（按服务拆分），新代码假设了一个并非所有进程都有的配置节。

## 规避方法

旁路能力的初始化模板：

```go
func initXxx() {
    defer func() {                       // 兜住基础设施函数的 panic
        if r := recover(); r != nil {
            log.Println("xxx init skipped:", r)
        }
    }()
    name := conf.SomeRedisName
    if name == "" { return }             // 本进程配置里就没有这一节 —— 正常情况, 直接跳过
    if _, ok := config.Config.Redises[name]; !ok {   // 先查表, 绕开 log.Fatal
        log.Println("xxx init skipped: redises 里没有", name)
        return
    }
    if err := Xxx(db.Redis(name)); err != nil {
        log.Println("xxx init error:", err)
    }
}
```

三条硬要求：
1. **`log.Fatal` 无法 recover** —— 凡是可能 Fatal 的分支，必须靠前置条件判断绕开，不能靠 recover。
2. **`panic` 要用 recover 兜住** —— 连接自检类失败属于运行时环境问题，不该杀进程。
3. **"配置里没有这一节"是正常情况，不是错误** —— 尤其在配置按服务拆分之后。

## 同一批修复里的第二个教训：埋点只覆盖成功路径

`ProxyClient.Do()` 原本只在 `case res = <-req.resCh:`（拿到响应）这一支上报观测，
另外三个提前 return 的分支（没有消费者接单 / 代理 leader 已结束 / 客户端侧收包超时）
什么都不记。结果是**代理池枯竭、全员超时这类最严重的故障在成功率里完全隐形**——
既不进分母也不进分子，面板上一片绿。

> 设计观测点时先问一句：**"失败得最彻底的那条路径，会被记录吗？"**

顺带：分类器 `classify(pc, res)` 在 `res == nil` 时仍会调业务提供的 `ClassifyResult`，
而业务分类器普遍直接读 `res.StatusCode` / `res.Body` —— 等于给每个接入方埋一个空指针。
**只要一个回调可能收到 nil，就要么在框架层挡掉，要么在契约里写死"一定非 nil"。**

## 下次行动建议

- 新增任何"进程级初始化"，先问：它会不会在**没有用到该能力的进程**里也执行？失败会怎样？
- 主控必须逐行审 hub 代码（`spider.go` 的命令分发、`gateway.go` 的注册、热路径的埋点）。
  本次两个验收 Agent 都没抓到这个缺陷，是主控自己审 hub 时发现的。

## 适用边界

适用于所有"旁路/可观测/上报"类能力接入既有进程的场景；不适用于业务确实强依赖的组件
（那种情况 fail-fast 才是对的，见 `lessons/failure-resdb的ES端点指向已下线集群.md`）。
