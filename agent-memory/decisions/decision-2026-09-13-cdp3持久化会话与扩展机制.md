---
title: 决策：cdp3 数据目录约定（NAS）、extensions= 走策略强装、profile= 用 NAS 单 tar + 连接内写回
type: decision
status: active
created_at: 2026-09-13T14:40:00+08:00
updated_at: 2026-09-13T14:40:00+08:00
priority: high
keywords: [cdp3, CDP3DATA, CDP3TEMP, NAS, extensions=, profile=, Browser.close, 定时清理, nc-app-prod-cdp3]
questions:
  - cdp3 的扩展和会话数据放在哪、目录怎么约定
  - 调用方用 profile= 时要注意什么
summary: 2026-09-13 用户要求 cdp3 挂 NAS：CDP3DATA=/mnt/nas/apps/cdp3（extensions/ profiles/），CDP3TEMP=/mnt/temp/cdp3 每天 04:30 定时清理；extensions= 只能策略强装；profile=ns/name 存单 tar、锁互斥、客户端须发 Browser.close 才可靠写回
load: on-demand
related:
  - agent-memory/lessons/failure-FC实例在WebSocket断开后立即冻结.md
  - agent-memory/lessons/success-cdp3策略强装扩展与NAS持久化profile.md
  - agent-memory/knowledge/architecture-fc-chrome文档爬虫上云.md
---

# cdp3 数据目录、扩展与持久化会话机制

## 背景与要解决的问题 [用户确认 2026-09-13]
用户要求 cdp3（`nc-app-prod-cdp3`）挂 NAS `00acc494e8-fnw4`：数据目录 `/mnt/nas/apps/cdp3`（环境变量 `CDP3DATA`，子目录 `extensions/` `profiles/`）；临时目录 `/mnt/temp/cdp3`（`CDP3TEMP`，跨实例/半永久才用，否则用实例 `/tmp`，定时每天清理）；`/chrome` 增加 `extensions=` 启用扩展、`profile=<namespace>/<name>` 持久化会话，profiles 要有锁防多实例同用。

## 备选与最终决策
1. **临时目录路径**：用户写 `/mnt/temp/cdp3` 而 NAS 根挂在 `/mnt/nas` → 采用第二个挂载点 NAS `/temp` → `/mnt/temp`（NAS 根已有 `temp/`），字面满足且跨实例。[推断，用户未反对]
2. **VPC**：FC 挂 NAS 必须进 VPC，用户片段无 vpcConfig → 照抄同账号唯一带 NAS 的 `nc-app-test$nc-image-render-api`（vpc-bp1wdtkktehlgutkby11k / vsw-bp1ago15c25gf58gl9fwg / sg-bp1d97t0sgaxdndifsmw）。[用户确认] 部署后挂载成功（/health cdp3Data/cdp3Temp writable=true）。
3. **扩展**：`--load-extension` 不可用（含 feature 开关）→ 策略 force_installed + 本机 update_url；解包目录用 Chrome 自身打 crx。`ext=<url>` 同路径修复。
4. **profile 存储**：目录树 cp → 单 tar（NFS 目录操作 31 s vs 1~2 s）；只含 `Default/`+`Local State`。
5. **写回时机**：FC 断开即冻结 → 拦截客户端 `Browser.close` 在连接内写回 + 20 s 周期快照兜底 + 写回前校验锁归属；锁过期 90 s。
6. **定时清理**：timer 触发器 `cleanTempTimer`（`CRON_TZ=Asia/Shanghai 0 30 4 * * *`）→ 事件调用 `Handle` → 删 CDP3TEMP 下最后修改 >24 h 的一级条目（payload `{"maxAgeHours":0}` 全清）。

## 影响
- 调用方（NC-JS task、doc_crawler 若用 `profile=`）**必须先发 CDP `Browser.close` 等响应再断开**，否则最多丢 20 s 且 profile 90 s 内不可复用（409）。
- 线上镜像 `app-20260913h`；NAS 上 `apps/cdp3/README.md` 有目录说明。

## 复盘条件
- Chrome 大版本升级后复测 `--pack-extension`、策略安装、`override_update_url`。
- 若 FC 3.0 提供 PreFreeze/后台任务能力，可去掉 Browser.close 依赖。
