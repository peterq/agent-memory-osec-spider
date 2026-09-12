---
title: 任务后备清单（低优先级 / 等人工事项）
type: task
status: active
created_at: 2026-09-12T23:00:00+08:00
updated_at: 2026-09-12T23:00:00+08:00
priority: low
keywords: [backlog, P3, 文档爬虫, FC, 人工事项]
questions:
  - 文档爬虫 FC 自动化还差哪些人工步骤
  - 有哪些 P3 低优先级待办
summary: 从 tasks.md 拆出的低优先级/等人工事项：文档爬虫 FC 自动化 6 项人工步骤、P3 代码小修
load: rarely
related:
  - agent-memory/current/tasks.md
---

# 任务后备清单

## 2026-09-08 并行四任务（监控增强 + 文档爬虫上云）—— 部分已上线，文档爬虫 FC 自动化待人工

①告警后台/队列告警可配 ②代理池后台 ③链接路径追踪 **已随 09-09 网关重启上线**（五仓库均已 push，详情见 session）。
- **④文档爬虫 FC 自动化仍未落地**，卡在以下人工事项：
  - [ ] SLS 给 `link_key` 建索引后打开 `services.queue_admin.sls.link_key_indexed`（缺省 false）
  - [ ] Tampermonkey 扩展包上传 OSS（`fc-chrome/extensions/tampermonkey.zip`），拿到实物后复核 `fc-chrome/tampermonkey.go` DOM 选择器（未验证）
  - [ ] FC 镜像构建与部署（阿里云 ACR + serverless-devs，函数名 `nc-app-prod-cdp3`），步骤见 COMMON `fc-chrome/README.md`
  - [ ] 新 FC 域名回填三处：NC-JS `CDP_ENDPOINT`、`task.ts` 的 `eps['prod-v3']`（TODO 占位）、SPIDER `services.doc_crawler.fc_endpoint`
  - [ ] 云端油猴脚本上传：userscripts `pnpm build:cloud && pnpm upload:cloud`
  - [ ] doc-crawler 部署主机待确认（`deploy.sh` 暂填 `osec-jenkins` 占位）
  - [ ] PC 端油猴调度器是否下线，由用户决定（可与 doc-crawler 并存）
- 详情：`sessions/2026/2026-09-08-并行四任务监控与文档爬虫上云.md`；`agent-tasks/2026-09-08-monitoring-and-doc-fc/`；`lessons/failure-旁路能力初始化拖垮主流程.md`。


## P3 低优先级待办

- [ ] **P3** `illuminate/queue-task/queue_test.go` 的 `TestGetTimeoutKeys`/`TestRePush` 既有失败（时间戳断言误差 ~10s）。
- [ ] **P3** `services/aliyun-drive` 的 `checkRecentUpdate` 用分享 id 而非 `md5(shareLink)` 查 STORAGE，疑似历史 bug，待确认。
- [ ] **P3 清理** 蜻蜓代理的**现行**凭据在 `services/proxy-provider/change_proxy_config.go`，
      该文件是 gitignore 的（未提交，处理得当）。但仓库里仍留着**过期**凭据：
      `proxy-provider.go` 硬编码的 `qtWhitelistLink` 与两份 `config*.yaml` 的
      `providers[].conf`。这些死值会误导排查（我就据此误判过"凭据全过期"），
      建议清掉或改成从环境变量读。
- [ ] **P3** `bnd_resolver_check.go:160` 的 `go vet` 告警（`storage.Resource` 按值传递，含 `sync.Mutex`）。
      根因是 `resource.SaveBaiduResource` 的全局签名，要改得整体改。
- [ ] **P3** `devops_res_reindex` 若要在非本地环境跑，需先约定导出目录挂载点（当前直接 panic 退出）。
