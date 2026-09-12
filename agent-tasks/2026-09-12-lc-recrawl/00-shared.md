# 误删资源重爬工具 —— 共享上下文（2026-09-12）

## 背景
`lifecycle_checker` 09-05~09-12 把资源 md5 当分享 id 探测，1,156,201 条有效资源（quark 1,115,264 / ali-share 40,007 / bnd 930）被判失效并从新旧 ES 索引删除（正本 SPIDER `PRD/res-lifecycle/rollout-2026-09-05.md` §15）。
**ES 是唯一数据源（Mongo 无数据，用户 09-12 确认）**，恢复只能重新解析入库：
把这些分享链接按限速重新投递到网关 `resourcePreCheck` 队列 → `*LoadShare` 消费者解析 → `resource.SaveResource` 写新旧索引，
lc 分表里 status=2 的行由入库上报自动复活（`services/gateway/lifecycle/rpc_service.go` L703 附近）；真失效的由解析器 `SubmitValid(valid=0)`。
`invalid_link_*` 表在代码里只写不读，不拦截。

## 仓库
| 简称 | 路径 | module |
|---|---|---|
| SPIDER | `/home/peterq/dev/projects/1s/osec-spider-go` | `github.com/1s/enfi-spider-go` |
| COMMON | `/home/peterq/dev/projects/1s/enfi-resource-common` | 只读参考（`rpc/spider/res_scheduler_rpc/res_rpc.go` 队列名） |

## 硬性约束
- 只做**投递工具 + dry-run 验证 + 文档**，**不投递生产**（主控拿到用户对节奏的确认后执行）。
- 投递必须走网关（`spider_common.NewResLinkCommitter().CommitResLink()`），禁止直连 redis 队列（`decisions/decision-2026-09-04-队列v2统一走网关.md`）。
- 生产凭据在 `_note/config/*.yaml`，禁止明文进代码/文档/汇报。
- 中文注释；错误用 `github.com/pkg/errors`；沿用 `services/devops/clear_expire/` 与 `tools/lc-check/main.go` 的风格。
- git：不加 `Co-Authored-By`；commit 前缀 `feat(devops)`/`tools(...)`；完成后 commit + push master。
- 禁止 Monitor / 后台任务；单测不联网。

## 验证
```bash
cd /home/peterq/dev/projects/1s/osec-spider-go && go build ./... && go vet ./tools/... ./services/devops/...
```

## 交付格式
≤400 字中文：改了哪些文件（路径:行）、测试/dry-run 输出原文、commit hash、push 状态、未做/无法验证项。
