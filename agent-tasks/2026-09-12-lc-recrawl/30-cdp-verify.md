# 角色 30：SPIDER —— `tools/quark-cdp-verify` 用云端 Chrome（CDP）实测解析器判失效的夸克分享

先读 00-shared.md（背景与硬性约束）。本角色**允许联网做只读浏览**（打开公开分享页），但不写任何生产数据。

## 目标
重爬过程中夸克解析器把约 45% 的分享判为失效（业务码 41031 封禁 / 41012 取消 / 41004 不存在 / 41011 过期 / 41010 违规 / 41019）。
为避免再出现"判定链路本身错了"的事故（见 rollout §15），用户要求：**抽 1,000 条，用真实浏览器（阿里云 FC 云端 Chrome）打开分享页实测**，
统计解析器判定与浏览器所见的一致率，列出所有不一致的样本。

## 输入
`/home/peterq/dev/projects/1s/osec-spider-go/_note/lc-recrawl/cdp-sample-1000.tsv`：每行 `share_id<TAB>resolver_code`（主控已生成，不要改）。分享页 URL = `https://pan.quark.cn/s/<share_id>`。

## 云端 Chrome（CDP）
- 端点 `wss://fc-resource-node-api.krzb.net/cdp3/chrome`（**不要带 `inject`/`script` 参数**）。每个 websocket 连接 = 一个独立的 Chrome 实例；**最大并发 30 个连接**（硬上限，工具缺省 20，flag 可调但 ≤30）。健康：`https://fc-resource-node-api.krzb.net/cdp3/health`。
- 连接后是浏览器级 CDP：`Target.createTarget` → `Target.attachToTarget(flatten=true)` 得 sessionId → 之后带 sessionId 发 `Page.enable`/`Network.enable`/`Page.navigate`/`Runtime.evaluate`。
- **复用** `services/doc_crawler/cdp/cdp.go`（gorilla websocket 的最小 CDP 客户端：`Dial`/`CreateTarget`/`AttachToTarget`/`RuntimeEnable`/`CloseTarget`，内部 `call(ctx, method, params, sessionId)`）。它没有通用事件订阅与通用调用导出——在该包里**最小化**加：`Call(ctx, method, params, sessionId) (json.RawMessage, error)` 与 `OnEvent(method string, fn func(sessionId string, params json.RawMessage))`（`dispatchEvent` 里分发），保持现有 `SetConsoleHandler` 行为不变，`go test ./services/doc_crawler/...` 必须仍过。知识：`agent-memory/knowledge/architecture-fc-chrome文档爬虫上云.md`、`lessons/failure-fc-chrome上线踩坑合集.md`（读一遍，别踩同样的坑）。
- FC 实例 600 s 超时、握手约 5 s：每个 worker 持一条连接顺序跑多页（每页新开 target、跑完 `Target.closeTarget`），连接断了就重连；不要每页重连（握手成本高）。

## 每条样本怎么判（写成纯函数 `classify(obs) verdict`，便于单测）
1. `Network.enable` 后 `Page.navigate`，等 `Page.loadEventFired` 或 20 s 超时；
2. 抓 `Network.responseReceived` 里 URL 含 `/share/sharepage/token` 的响应 → `Network.getResponseBody` → JSON `status/code/message`（这就是解析器与 checker 用的同一个接口，但由真实浏览器带完整上下文发出）；
3. 页面加载后 `Runtime.evaluate` 取 `document.title` 与 `document.body.innerText.slice(0,400)`；
4. 判定：
   - `code==0`（或页面出现文件列表/「保存到网盘」等有效标志且无失效文案）→ **CDP=有效** → 与解析器 **不一致（重点）**；
   - `code` ∈ {41031,41012,41004,41011,41010,41019} 或页面文案含「分享不存在/已失效/已取消/被封禁/违规/已过期」→ **CDP=失效**，且记录 CDP 业务码是否与解析器一致；
   - 抓不到 token 响应、超时、验证码/滑块页 → **未知**，重试 1 次仍未知则记 unknown（不算一致也不算不一致）。
5. 对每个「不一致」样本额外 `Page.captureScreenshot`（jpeg quality 40）存 `<outdir>/shots/<share_id>.jpg`，最多存 50 张。

## 交付
- `tools/quark-cdp-verify/main.go`（+ `classify.go`、`classify_test.go`）：flags `-file`、`-out <dir>`（缺省 `_note/lc-recrawl/cdp-verify`）、`-endpoint`、`-concurrency`（缺省 20，上限 30）、`-limit`、`-timeout`（每页缺省 20s）。逐条结果追加写 `<out>/results.tsv`：`share_id resolver_code cdp_code cdp_message title text_snippet verdict elapsed_ms`；支持断点（已在 results.tsv 的 id 跳过）。结束打印汇总：总数 / 一致 / 不一致 / 未知，按 resolver_code 分组的一致率，不一致样本列表。
- `<out>/report.md`：汇总表 + 不一致样本明细（share_id、解析器码、CDP 码/文案、截图路径）+ 未知样本原因分布。
- 顶部用法注释（中文）。
- **验证**：`go build ./... && go vet ./tools/quark-cdp-verify/ ./services/doc_crawler/... && go test ./tools/quark-cdp-verify/ ./services/doc_crawler/...`；然后 **真实跑 `-limit 5 -concurrency 2`** 贴输出（允许，这是只读浏览）。全量 1,000 由主控跑。
- commit 前缀 `tools(quark-cdp-verify)` / `doc_crawler(cdp)`，push master。汇报按 00-shared.md 格式，另附 5 条实测的逐条结果。
