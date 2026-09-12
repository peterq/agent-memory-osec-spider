---
title: 成功经验：给站点爬虫写可复跑的联网集成测试
type: lesson
status: active
created_at: 2026-09-02T15:25:00+08:00
updated_at: 2026-09-12T12:10:00+08:00
priority: high
keywords:
  - 集成测试
  - 爬虫
  - 联网测试
  - 去重键
  - 命名空间
  - 假 committer
summary: 用「假 committer + 独立 redis 键前缀 + 环境变量开关」让爬虫的联网测试可重复运行且不污染线上
questions:
  - 我要给爬虫写测试，联网测试怎么不污染线上
load: on-demand
related:
  - agent-memory/procedures/workflow-新站点调研.md
  - agent-memory/knowledge/architecture-spider.md
---

# 成功经验：给站点爬虫写可复跑的联网集成测试

## 问题

新写一个站点爬虫，怎么在**不连 storage gateway、不污染线上队列和去重键**的前提下，
真正验证"翻页会不会死循环、条数对不对、不支持的平台有没有被过滤、去重生不生效"？

单元测试 mock 掉 HTTP 就验证不了站点的真实行为（页码钳制、400、字段结构），
而直接跑爬虫又会把几千条链接推进入库链路。

## 适用条件

- SPIDER 仓库里任何"站点遍历型 / 关键词型"爬虫。
- 目标站点无反爬、请求成本低（本例全量 45 次请求 / 22 秒）。

## 推荐做法

三件事缺一不可：

1. **提交入口用接口，测试注入假实现。**
   `spider_common.ResLinkCommitter` 是接口，测试里定义一个只记录 URL 的
   `fakeCommitter` 塞进爬虫结构体，整条采集流程照跑，但不产生任何入库副作用。
   → 爬虫结构体的 `committer` 字段必须声明成**接口类型**而不是具体类型。

2. **redis 键前缀做成结构体字段，测试用独立命名空间。**
   生产用 `"<site>:"`，测试用 `"<site>-test:<pid>:"`。
   否则测试的去重键会和线上/上一次测试互相干扰——本例踩过：
   第一遍跑完键还在，第二遍"应该提交至少一条"的断言就挂了。

3. **用环境变量开关跳过，默认 `t.Skip`。**
   `KKPANS_IT=1` 才跑联网用例，`KKPANS_IT_ALL=1` 才跑全量（几千条）版本，
   这样 `go test ./...` 在 CI / 本地默认不会打站点。

## 示例

`osec-spider-go/services/bbs/kkpan.com_test.go`：

```bash
KKPANS_IT=1 go test ./services/bbs/ -v -run TestKkpans                 # 快，只跑最少条数的平台
KKPANS_IT=1 KKPANS_IT_ALL=1 go test ./services/bbs/ -v -run TestKkpans # 全量对账
```

覆盖的断言正好对应 PRD 的验收标准：
首页字段结构、**页码钳制**（请求 page=52 返回 page=43）、SSR 降级通道、
非法参数返回 400、`found == siteTotal`、不支持平台 `committed=0`、
第二轮去重后 `committed=0`、增量水位线首轮建立次轮追平。

## 注意事项

- 测试里的断言不要写死站点条数（本例 4295 会随站点更新变动），
  要断言 `found == siteTotal`（用站点自己返回的 `total` 对账）。
- 有水位线之类的无 TTL 键，测试结束要 `defer rds.Del(...)`。
- 测试的 `seenTTL` 要设得比整轮耗时长（本例 10 分钟），否则跑到一半键先过期。

## 可迁移范围

任何"外部数据源 → 内部队列"的采集类服务。
关键是把**副作用出口（committer）和状态命名空间（redis 前缀）都做成可注入的**。
