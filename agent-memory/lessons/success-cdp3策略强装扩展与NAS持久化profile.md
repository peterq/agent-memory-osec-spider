---
title: 成功经验：品牌版 Chrome 用企业策略 + 本机 update_url 装 NAS 上的扩展；profile 用 NAS 单 tar 持久化
type: lesson
status: active
created_at: 2026-09-13T14:40:00+08:00
updated_at: 2026-09-16T09:00:00+08:00
priority: medium
keywords: [扩展安装, ExtensionSettings, override_update_url, pack-extension, disable-background-networking, developerPrivate.autoUpdate, NAS, tar, profile 持久化, NFS 性能]
questions:
  - 怎么让 headless Chrome 装 NAS 上的自定义扩展
  - 策略强装的扩展改了版本为什么不更新
summary: 品牌版 Chrome 用企业策略 force_installed 装扩展 + 预热 profile 存 NAS 复用登录态
load: on-demand
related:
  - agent-memory/lessons/failure-品牌版Chrome禁用load-extension与userScripts二次授权.md
  - agent-memory/lessons/failure-FC实例在WebSocket断开后立即冻结.md
  - agent-memory/decisions/decision-2026-09-13-cdp3持久化会话与扩展机制.md
---

# cdp3 扩展启用与 profile 持久化的可行做法（Chrome 153）

## 扩展：唯一可行路径是企业策略 force_installed
- `--load-extension` 在品牌版 153 上即使加 `--disable-features=DisableLoadExtensionCommandLineSwitch` 也被忽略（实测）。
- 链路：`CDP3DATA/extensions/<name>/`（解包）→ 容器内 `google-chrome --headless=new --no-sandbox --pack-extension=<本地副本> [--pack-extension-key=<name>.pem]` 打 crx（无需显示，~1 s；pem 落 NAS 保证 id 稳定，crx 用临时文件+rename 落 NAS 共享）→ bootstrap 自己在 `127.0.0.1:9000/cdp3-ext/<name>/{update.xml,ext.crx}` 提供 gupdate 清单 → 起 Chrome 前写 `zz-cdp3-extensions.json`。
- 扩展 id 直接从 crx3 头解析：protobuf field 10000 `signed_header_data` → field 1 `crx_id`（16 字节，每 4 bit 映射 a~p），不用算公钥哈希。
- **三个坑**：① `--disable-background-networking` 会让扩展更新器不拉 update_url（20 s 装不上，去掉后 1~3 s）；② 策略条目必须 `"override_update_url": true`，否则 update_url 只管首装，之后按 manifest（没有）检查 → 改了扩展永远升不上去（现象：autoUpdate 跑了但 downloader 一个 URL 都不拉）；③ 已装旧版本时只在周期检查升级，握手前在 `chrome://extensions` 页 `Runtime.evaluate` `chrome.developerPrivate.autoUpdate()`（awaitPromise）主动触发，1~2 s 完成。
- 同一策略键（ExtensionSettings）多个文件时 Chrome 取字母序最后一个而不是合并，所以要把镜像里的 Tampermonkey 条目合并进自己的 `zz-` 文件。
- 就绪判据：`Default/Extensions/<id>/<version>_0/` 落盘（无后台页的扩展在 Target.getTargets 里看不到）。
- 组件更新器会往 profile 塞几十 MB（optimization_guide_model_store 36 MB）：加 `--disable-component-update`。

## profile 持久化
- NAS 上存单个 `<name>.tar`（只含 `Default/` + `Local State`，排除 Cache/Code Cache/GPUCache/Service Worker 缓存），~10 MB；目录树 `cp -a` 到 NFS 要 31 s，tar 1~2 s。
- Chrome 关闭必须走 CDP `Browser.close`：SIGTERM 是快速关闭，localStorage 写完立刻断开会丢（等 6 s 才不丢）。发 Browser.close 只保证写出，不等响应（Chrome 可能先关连接），看进程退出。
- 复制来的 profile 先删 `Singleton*`/`DevToolsActivePort`。
- 锁：`<name>.lock` O_EXCL 创建；抢过期锁用 rename（只有一个能成功）再 O_EXCL 重建，不能 remove+create；心跳原地覆盖不 rename。
- 验证工具 `fc-chrome/cmd/cdp3verify`（`-query`/`-page`/`-eval`/`-hold`/`-close`）；本地联调用 `fc-chrome:base-seed` 容器挂 bootstrap + 本地目录当 NAS。
