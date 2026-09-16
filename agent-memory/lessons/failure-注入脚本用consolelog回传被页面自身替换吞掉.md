---
title: 失败经验：CDP 主世界注入脚本用 console.log 回传，被页面自身的 console.log 替换悄悄吞掉
type: lesson
status: active
created_at: 2026-09-13T15:50:00+08:00
updated_at: 2026-09-16T09:30:00+08:00
priority: high
keywords: [console.log, CDP, addScriptToEvaluateOnNewDocument, 主世界注入, fc-chrome, kdocCloud, DOC_SPIDER, 油猴, Tampermonkey, monkey-patch]
summary: 页面自身代码会整体替换 window.console.log；注入脚本必须在最开头抓原生引用回传，否则只见一条 start 后沉默
questions:
  - CDP 注入脚本为什么只打出第一条日志就沉默
  - 用 console.log 回传协议什么情况会全部收不到
load: on-demand
related:
  - agent-memory/agent-tasks/2026-09-13-fc-chrome-online/99-notes.md
  - agent-memory/agent-tasks/2026-09-08-monitoring-and-doc-fc/05-doc-fc-contract.md
---

## 问题背景

`fc-chrome`（COMMON 仓库，阿里云 FC 自定义 Chrome 运行环境）支持用 CDP
`Page.addScriptToEvaluateOnNewDocument` 在 `document-start` 阶段把一段脚本注入到主世界
（`inject=1`，是"油猴自动装脚本"三条路径里唯一验证稳定的兜底通道）。脚本
（`userscripts` 仓库 `src/cloud/kdocCloud.ts`）解析完金山文档表格后，通过约定的
`console.log('[[DOC_SPIDER]]' + JSON.stringify(payload))` 单行协议回传给上层
（doc-crawler / 人工调试工具 `localverify`），上层用 CDP `Runtime.consoleAPICalled`
事件订阅这条通道。

用**真实、公开可访问**的金山文档表格分享链接（`www.kdocs.cn/l/xxx`）联调时，无论本地
`fc-chrome` 还是线上已部署的 FC 实例，现象完全一致：只收到一条 `{"event":"start"}`，
之后无论等多久（试过 40s~300s+）都再也没有任何 `progress`/`result`/`error`，直到
FC 实例的 `timeoutSec` 到期、Chrome 被杀、连接异常关闭。

## 排查过程中试过的错误方向（均已证伪，记录下来避免下次重复踩）

1. **怀疑 SSO 重定向丢了 nonce**：确实存在真实问题（`www.kdocs.cn` 匿名访问会经过
   `account.kdocs.cn`/`account.wps.cn` 的一串重定向，最终落地页 `location.hash`
   被冲掉），修复后（用 `Domain=.kdocs.cn` 跨子域 cookie 带 nonce + 只在真正的文档域名
   消费）确认 `start` 能在正确的、`window.__WPSENV__`/`window.APP.getActiveSheet()`
   都已就绪的落地页上正确触发——但后续依然只有 `start`，说明还有别的问题。
2. **怀疑页面又发生了一次没观察到的内部重导航/重置，销毁了执行上下文**：用 CDP
   `Target.setDiscoverTargets`+`Page.frameNavigated`+`Runtime.executionContextsCleared`
   +`Inspector.targetCrashed` 全程监听，确认落地后**没有**发生任何新的导航/上下文清空/
   崩溃事件。证伪。
3. **怀疑同一个 nonce 被过早消费**：改成"真正拿到终态才消费"（sticky nonce）后现象不变。
4. **怀疑是本机资源紧张/网络抖动**：换到线上真实已部署的 FC 实例（干净环境、非本机）
   复测，现象完全一致，排除本机环境因素。
5. **怀疑 JS 执行环境本身被挂起/卡死（长同步循环占满主线程，watchdog 的 setTimeout
   都没机会跑）**：加了一个独立的 `setInterval` 心跳，并在回调里同时写一个
   `window.__debug_ticks__` 全局计数器。用 CDP `Runtime.evaluate` **直接轮询**这个
   全局变量（不经过 console 通道），发现计数器在稳定增长（比如 15 秒内到了 5）——
   **证明 JS 定时器和主线程完全正常，问题只出在"回传"这一步，不是"执行"这一步**。
   这一步是定位到真正根因的关键分岔点：执行正常但回传收不到，说明是
   `console.log` → CDP 这条链路本身出了问题。
6. **怀疑 Chromium DevTools 对完全相同的重复 console.log 做协议级去重**（只报第一条,
   后续相同内容不再触发 `Runtime.consoleAPICalled`，只在 UI 上折叠成 "xN"）：给每条
   心跳消息带上递增 tick/时间戳让内容各不相同，现象依旧不变。证伪。

## 根本原因

**金山文档自己的前端代码加载完成后，会整体替换 `window.console.log`**（推测是收敛生产
环境日志噪音、或接自己的日志上报系统，是很多成熟 web 应用的常见做法），大约发生在
页面落地后 1~2 秒内。

`fc-chrome` 的 `inject=1` 是在 `document-start` 阶段注入，比页面自己的任何脚本都早，
所以脚本一开始的 `emit({event:'start'})` 调 `console.log` 时命中的还是**原生实现**，
CDP 能看到。但 `emit()` 内部每次都是"重新读取 `console.log` 属性再调用"——一旦页面
自己的代码执行完毕、把 `window.console.log` 整体换成了它自己的函数，后续所有
`console.log(...)` 调用实际上调的是**替换后的函数**，这个函数可能只是把日志推进一个
数组或发去自己的上报接口，根本不会走到浏览器原生的 console 实现，因此**完全不会**
触发 CDP 的 `Runtime.consoleAPICalled` 事件——表现得像"整个执行环境失去响应"，
实际上 JS 一直在正常执行（心跳计数器持续增长可以证明），只是回传通道本身被换掉了。

## 规避方法

在注入脚本的**最开头**（比任何其它逻辑都早，因为是 document-start 主世界注入，
本身就比页面其它脚本先执行）抓一份原生 `console.log` 的引用存好：

```js
const nativeConsoleLog = console.log.bind(console);
```

后续所有回传**只用这个抓到的引用**调用，不再经过随时可能被页面自身代码重新赋值的
`window.console.log` 属性。因为 JS 函数是对象，`bind()` 生成的新函数内部持有的是
"绑定时那一刻"的原始函数引用，之后 `window.console.log` 被重新赋值也不影响它。

同理，任何用 `console.error`/`console.warn` 兜底的地方也要用同一份抓到的原生引用，
不要再调 `console.error(...)`（同样可能被替换、或替换成的函数语义不同）。

## 适用范围与推广价值

- 不止金山文档：**任何依赖 CDP 主世界注入 + console.log 回传协议、目标页面是成熟商业
  web 应用（尤其是大厂自己的办公套件/SaaS）** 的场景都可能踩到同样的坑，因为这类应用
  普遍会在生产环境接管/收敛 `console.*`。
- 排查思路可复用：怀疑"脚本卡死"但又不确定是执行卡死还是回传卡死时，**先用一个独立的
  全局变量 + `Runtime.evaluate` 轮询**去验证 JS 是否还在正常执行，能快速把"执行环境
  问题"和"回传通道问题"这两大类原因分开，避免在错误的方向（重导航/内存泄漏/事件循环
  饥饿）里反复兜圈子。
- 抓原生引用这个技巧对 `setTimeout`/`fetch`/`XMLHttpRequest` 等也同样可能需要，
  只是本次只在 `console.log` 上实测踩到。

## 相关的另外两个真实 bug（同一轮排查一并发现修复，价值较小但记录避免遗忘）

- `taskNonce` 的正则字符集漏了 `-`，doc-crawler 用 uuid 做 nonce，被截断
  （如 `online-inject-1` 截成 `online`）——**用正则做"提取到下一个已知分隔符/字符串
  结尾为止"时，字符集一定要按实际取值范围来定，不要凭直觉列举**，uuid/token 类值几乎
  都会带 `-`。
- 分享链接的匿名访问 SSO 重定向链会经过多个跳转，`location.hash` 在跨域重定向时可能
  被冲掉——如果需要在这类重定向后还能拿到原始 hash 里的信息，可以用
  `Domain=.<父域>` 的跨子域 cookie 在"最后一次看到 hash"时存一份，落地后再读出来
  （前提是重定向链最终落回同一个注册域下）。
