---
title: 会话：xlLoadShare 失败率排查
type: session
status: active
created_at: 2026-09-15T06:46:00+08:00
updated_at: 2026-09-15T06:46:00+08:00
priority: medium
keywords: [xlLoadShare, 迅雷, 失败率, 排查]
summary: xlLoadShare 失败率排查过程；结论在 knowledge/domain-迅雷分享爬取.md
load: rarely
related:
  - agent-memory/knowledge/domain-迅雷分享爬取.md
---

# 2026-09-15 xlLoadShare 失败率排查

## 完成事项
- 从 osec-jenkins/osec-resngix 的 docker 日志统计近 48h 成功/失败与 reason 分布（事件级 ≈50% 失败，任务级 39%）。
- 读 `xl-client.go`/`big-res.go`/消费者代码，对照夸克客户端，锁定顶层文件不入遍历队列的缺陷。
- 经 `:9527` 调试代理直连迅雷接口，对 186 个失败分享 + 40 个成功分享做顶层结构分类，对 45 个"只有文件夹"的失败分享逐个查详情（43 空）。
- 沉淀探针脚本 `scripts/xl_share_probe.sh`。

## 关键发现
见 `knowledge/domain-迅雷分享爬取.md` §3/§4。

## 遇到的问题
- 远端主机无 python3，解析全部放本地；调试代理共用 token 并发触发 captcha_invalid；pass_code_token 经代理需双重编码。
- osec-resngix ssh 偶发超时。

## 后续行动
- 待用户决定修复方案（见 `current/open-questions.md`），未改代码。
