# 05-doc-fc-contract —— 文档爬虫上云的接口契约（40 与 41 两个角色都必读）

主控在派单前先把两边的接口定死，避免并行开发对不上。**不要单方面改这份契约**；
确有必要改，在汇报里写明并同步告知另一角色（通过主控）。

## 1. 总体拓扑

```
网关 spider_gateway (标准 gRPC :8082)
   ↑ PopTask / TaskKeepalive / TaskDone / CommitResource2
   │
doc-crawler (SPIDER 新进程, 角色 41)
   │  控制并发, 一个任务一条 WS
   ↓ ws://<fc-host>/chrome?...
新 FC Chrome 实例 (COMMON/fc-chrome, 角色 40)
   │  Tampermonkey 内置 + 按 url 装扩展/油猴脚本
   ↓ 打开 <docUrl>#taskNonce=<nonce>
云端版金山文档爬虫脚本 (userscripts 仓库新 target, 角色 40)
   │  解析表格 → 提取网盘链接
   ↓ console.log 约定协议
doc-crawler 收集结果 → CommitResource2 提交链接 → TaskDone 上报
```

**关键简化**：云端脚本**不再自己连 gRPC / WebRTC，也不用 GM 跨标签页总线**。
它只做"解析 + 通过 console 回传"，链接提交与任务上报统一由 doc-crawler 用标准 gRPC 完成。
这样脚本体积、依赖和失败面都大幅收敛。

## 2. FC Chrome HTTP/WS 接口（角色 40 实现，角色 41 调用）

### `GET /chrome`（WebSocket Upgrade）

一次 WS 连接 = 一个全新的 Chrome 实例；连接断开即 kill Chrome 并清 profile。
连上后是**裸 CDP 协议透传**（与现有 `nerve-center/fc-entry/cmd/app_cdp/app_cdp.go:300-374` 行为一致，
调用方可直接用 puppeteer/chromedp 的 `connect(browserWSEndpoint)`）。

query 参数：

| 参数 | 含义 | 缺省 |
|---|---|---|
| `display` | `1` = 非 headless（本地带界面调试用） | `0`（`--headless=new`） |
| `ext` | 要加载的扩展，逗号分隔的 URL 列表（zip 或 crx）。下载后解包并 `--load-extension` | 空 |
| `noTm` | `1` = 不加载内置 Tampermonkey | `0`（默认加载） |
| `script` | 油猴脚本 URL（`*.user.js`），Chrome 起来后自动装进 Tampermonkey | 空 |
| `inject` | `1` = 除了装进油猴，另外用 CDP `Page.addScriptToEvaluateOnNewDocument` 直接注入 `script`（兜底通道，见 §5） | `0` |
| `timeoutSec` | 单实例最长存活秒数 | `300` |

- 参数非法或下载失败：**在 WS 握手前**返回 HTTP 4xx/5xx，body 是 JSON `{"error":"..."}`，
  这样调用方能拿到明确原因（现有实现是握手后才报错，很难排查——要改掉）。
- `ext` / `script` 的 URL **必须在白名单域内**（缺省只允许 `osec-deploy-pub` 那个 OSS 桶的公网/内网域名，
  域名列表用环境变量 `ALLOWED_ASSET_HOSTS` 覆盖），防止被当成任意 URL 下载器。

### `GET /health`

返回 `{"ok":true,"chromeVersion":"...","tampermonkey":"<version|null>","cacheEntries":N}`。
角色 41 用它做启动自检。

### `GET /test`

保留现有语义（拉起一次 Chrome 返回 ws endpoint 字符串），用于人工验证。

## 3. 页面 → doc-crawler 的 console 协议（角色 40 的脚本产出，角色 41 消费）

脚本在**目标文档页**里执行。所有回传都通过 `console.log(单行字符串)`，前缀固定：

```
[[DOC_SPIDER]]<json>
```

`<json>` 是一个对象，字段：

```jsonc
{
  "nonce": "<从 location.hash 的 #taskNonce= 取到的值>",
  "event": "start" | "progress" | "result" | "error",
  // event=progress
  "scanned": 1234,          // 已扫描行数
  // event=result
  "ok": true,
  "docType": "kdocSheet",
  "docMtime": "2026-09-08T12:00:00.000Z",  // ISO8601, 来自 window.__WPSENV__.file_info.file.modify_time
  "version": "<sha1>",       // 全部链接 url 去重排序后 join("\n") 的 SHA-1, 与现有 PC 版算法保持一致
  "linkCount": 42,
  "links": [ { "url": "...", "pwd": "...", "type": "quark" } ],
  // event=error
  "message": "暂仅支持表格文档",
  "permanent": true          // true = 这个文档以后也不用再试(类型不支持/文档已失效)
}
```

约束：
- **单条 console.log 不得超过 200KB**。链接多时分批发多条 `event:"result"`，
  用 `"seq": n, "final": true|false` 标记；`final:true` 那条才带 `version`/`linkCount`。
- 脚本必须在 **60 秒内**发出第一条 `start`，否则 doc-crawler 判失败。
- 脚本**不负责关闭页面**，由 doc-crawler 关。
- 脚本必须在解析异常时也发 `event:"error"`，不要静默。

## 4. doc-crawler 的行为约定（角色 41 实现）

- 从网关 `DocSchedulerRpc.PopTask` 拉任务（标准 gRPC，网关已在 `gateway.go:376` 注册）
- 每个任务生成 `nonce`（uuid），打开 `task.model.url + "#taskNonce=" + nonce`
- **保活**：网关侧超时判定是 **61 秒无保活**（`res_scheduler.go` 与
  `doc_scheduler.go:672` 的 10 秒扫描），doc-crawler 每 **5 秒** 调一次 `TaskKeepalive`
- 收到 `final:true` 的 result → 用 `SpiderRpc.CommitResource2` 批量提交链接（分批，每批 ≤200）
  → 再调 `TaskDone`
- `TaskDoneParams` 字段与现有 PC 版对齐：`{seqId, url, success, failMsg, invalid, type, docMtime, version, linkCount, meta}`
- **版本未变则跳过提交**：`task.model.version == 新算出的 version` 时不提交链接，
  但仍要 `TaskDone`（把 version/linkCount 原样回填），与 PC 版行为一致

## 5. Tampermonkey 自动装脚本（角色 40 的难点，必须如实汇报做法与把握度）

Chrome 无法用命令行直接给 Tampermonkey 预装脚本。可选路径，**按顺序尝试**：

1. **Tampermonkey 的 managed storage / 配置导入**：下载到扩展后先读它的 `manifest.json` 与
   options 页，确认当前版本支持哪种"从 URL 导入"的入口。
2. **驱动它的 options 页**：用 CDP 打开 `chrome-extension://<id>/options.html#nav=utils`，
   在"Import from URL"里填 `script` 并提交，等待安装完成的 DOM 变化。
3. **兜底通道（必须实现）**：`inject=1` 时用 CDP `Page.addScriptToEvaluateOnNewDocument`
   把脚本源码直接注入主世界。注入前把油猴头（`// ==UserScript== ... ==/UserScript==`）剥掉，
   并注入一层极小的 GM shim（只需 `GM_setValue/GM_getValue/GM_log` 的空实现即可，
   云端脚本按 §3 设计本就不依赖真正的 GM 能力）。
   **主世界注入时 `window` 就是页面 window，`unsafeWindow` 直接等于 `window`**，
   金山文档需要的 `window.APP` / `window.__WPSENV__` 可以直接访问 —— 这条路径反而最可靠。

**本轮无 FC 环境、无阿里云凭据，Tampermonkey 那条路无法实跑验证。**
要求：路径 1/2 按最好理解实现并写清"未验证"，路径 3 必须本地用真实 Chrome 跑通并给出证据。
doc-crawler 侧缺省用 `inject=1`（可配），保证功能开箱能用。

## 6. 本轮无法完成的部分（两个角色都不要卡在这里）

- 新 FC 实例的**镜像构建与部署**需要阿里云 ACR / serverless-devs 凭据 → 只写脚本与文档，不执行
- Tampermonkey 扩展包本体需要人工放到 `oss://osec-deploy-pub/fc-chrome/extensions/tampermonkey.zip`
  → 构建脚本里做成"URL 可配 + 缺失时警告并跳过"，不要让构建失败
- `cdp-driver` 切到新实例需要新实例的真实域名 → **把 endpoint 改成环境变量可配
  （`CDP_ENDPOINT` / `CDP_ENDPOINT_VPC`），缺省值先保留旧域名并加 TODO 注释**，
  等新实例上线后改环境变量即可，不要写死一个还不存在的域名
