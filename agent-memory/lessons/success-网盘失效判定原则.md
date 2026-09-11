---
title: 成功经验：网盘失效判定要「业务码优先 + 不确定就报错」
type: lesson
status: active
created_at: 2026-09-02T16:35:00+08:00
updated_at: 2026-09-02T16:35:00+08:00
priority: high
keywords:
  - 失效判定
  - 业务码
  - 限流
  - 误删
  - 文案匹配
summary: 靠 message 文案匹配判定网盘失效必然随站点文案漂移而失灵，应改用业务码并把未知响应升级为 error
load: on-demand
related:
  - agent-memory/knowledge/domain-网盘有效性检测.md
  - agent-memory/lessons/success-爬虫联网集成测试.md
---

# 成功经验：网盘失效判定要「业务码优先 + 不确定就报错」

## 问题

夸克/阿里的有效性检测长期是「用中文 `message` 做 `strings.Contains` / 正则匹配」，
网盘一改文案或新增一种失效原因，检测就落到 `unknown status` 分支返回 error，
对外接口直接变成 `status = -1`。2026-09-02 抽样 15+15 条，10 条报错。

## 适用条件

任何「调第三方接口判断资源生死」的场景，尤其是**判定结果会触发删除**的。

## 推荐做法

1. **用业务码而不是文案分类。**
   夸克的 `code`（41004/41006/41010/41011/41012）、阿里的 `code`（`ShareLink.*` / `NotFound.*`）
   都是稳定枚举；`message` 只留作兜底正则。
   排查时不要只试一条链接——**一次跑一批（15 条起）才能把冷门业务码抖出来**，
   本次 4 条 `41004`、1 条 `ShareLink.ContentInvalid` 都是这么发现的。

2. **限流必须和失效严格区分。**
   HTTP 429 / `code=TooManyRequests` / **空 body**，都属于"没问出结果"，
   要 `BlockProxy` + 退避重试，用尽后返回 **error**。
   把限流当失效，等于按接口的抖动去删 ES 数据。

3. **未知响应返回 error，而不是 false。**
   判定函数返回 `(valid, known bool)`：`known == false` 时调用方报错。
   宁可对外 -1 让人来看，也不能悄悄把有效资源判死——
   `deleteInvalid` / `DeleteResourceTask` 是不可逆的。

4. **"入口还在" ≠ "内容还在"。**
   阿里有一类分享 `share_title` 正常、`file_count > 0`，但 `file_infos` 为空数组，
   实际内容已被删除/屏蔽。只查分享元信息会漏判，要顺带看文件列表是否为空。

## 原因

第三方网盘不承诺 message 文案稳定，但业务码是它自己的接口契约，改动频率低得多。
而"未知即报错"把不确定性留在了可观测的地方（-1 + 日志），
"未知即失效"则把不确定性直接写成了数据删除。

## 注意事项

- 只登记**真实观测到**的业务码，不要凭印象猜码值。
- 两套实现（API `services/valid/` 与 SPIDER `services/gateway/valid/`）是独立代码，
  改判定逻辑要同时改，否则 `/v2/validShareLink` 和 `clear_expire` 会给出不一致的结论。

## 可迁移范围

百度网盘、迅雷的 checker 同样是文案匹配，有同类风险；下次动到它们时按本文改造。
