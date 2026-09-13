---
title: 失败经验：品牌版 Chrome 137+ 忽略 --load-extension、138+ 用户脚本需 "Allow User Scripts" 二次授权
type: lesson
status: active
created_at: 2026-09-13T11:00:00+08:00
updated_at: 2026-09-13T14:45:00+08:00
priority: high
keywords: [Chrome, load-extension, ExtensionSettings, Tampermonkey, @match, 302 重定向, Allow User Scripts, headless, 企业策略]
questions:
  - 为什么 headless Chrome 加了 --load-extension 却看不到扩展
  - 怎么让容器里的 Chrome 自动装上 Tampermonkey
  - 油猴脚本装上了但页面不执行是怎么回事
  - Tampermonkey 就绪要等多久, 怎么把等待挪到构建期
summary: 2026-09-13 fc-chrome 上线实测：品牌版 Chrome 137+ 忽略 --load-extension，改企业策略 force_installed 装 Tampermonkey；138+ 还要打开 Allow User Scripts（预热 profile 种子解决）；CDP 不能 attach chrome-extension:// target；油猴路径"装上不执行"最终是 @match 没覆盖 SSO 302 首跳页
load: on-demand
related:
  - agent-memory/knowledge/architecture-fc-chrome文档爬虫上云.md
  - agent-memory/procedures/workflow-fc-chrome上线.md
---

# 品牌版 Chrome 装扩展的三道墙

## 问题背景
fc-chrome 的"内置 Tampermonkey + 自动装脚本"路径按 `--load-extension` 设计（09-08），09-13 上线才发现在真实 Chrome 149/153 上根本进不了浏览器。

## 失败方法与表现
1. `--load-extension=/opt/extensions/tampermonkey`：stderr `WARNING: --load-extension is not allowed in Google Chrome, ignoring.`，`Target.getTargets` 只有 4 个内置组件扩展。headless 与 `display=1` 一样。[14:00 补] 加 `--disable-features=DisableLoadExtensionCommandLineSwitch` 在 153 上同样被忽略；自定义扩展的可行链路见 `success-cdp3策略强装扩展与NAS持久化profile.md`。
2. 装上后（策略路径）脚本在 dashboard 可见却永不执行：Chrome 138+ 的 `chrome.userScripts` 需要用户在 `chrome://extensions/?id=<id>` 打开 "Allow User Scripts"，官方明确没有等价企业策略。
3. 用 CDP `Target.attachToTarget` 到任意 `chrome-extension://` target 一律 `-32000 Not allowed`。
4. 拿 `Target.getTargets` 里"第一个 chrome-extension://"当 Tampermonkey → 选中了内置 Hangouts，打开它的 options.html 报 `ERR_FILE_NOT_FOUND`。

## 有效做法
- 企业策略：镜像里 `/etc/opt/chrome/policies/managed/tampermonkey.json` = `{"ExtensionSettings":{"<id>":{"installation_mode":"force_installed","update_url":"<OSS update.xml>"}}}`；update.xml 是 gupdate 清单，`codebase` 指 OSS 上的原始 crx（Chrome 应用店 crx 下载端点可直接取）。容器内 `/json/list` **≤5 s** 就出现 `service_worker chrome-extension://<id>/background.js`。
- "Allow User Scripts"：只能用 CDP 在 `chrome://extensions` 特权页点开，且状态随 profile 持久化 → **预热一份 profile 种子打进镜像，运行时 `cp -a` 复制**（`scripts/seedprep-oob.sh` + `cmd/seedprep`），运行时就绪 2~3 s。
- 操作扩展页面：先 `Target.createTarget about:blank` 再 `Page.navigate` 到 `chrome-extension://…`。识别 Tampermonkey：按 `-ext-id` 精确匹配 target URL 前缀，不要取第一个。
- Tampermonkey 5.5 真实 DOM：Utils 面板输入框 `.updateurl_input`、按钮文案 "Install"；确认页 `ask.html?aid=…` 上 `input[name=Install].install`。

## 第四道墙：`@match` 与重定向链 [事实 2026-09-13]
- 线上"脚本装上了但页面不执行"折腾 4 轮，最后是 **`@match`**：未登录访问 `www.kdocs.cn/l/*` 首个响应 302 到 `account.kdocs.cn/passport/singlesign?…`，浏览器把 `#taskNonce=` 带到这一跳；脚本只匹配文档域名，在 TM 下从未在该跳运行、拿不到 nonce，落地后按"无 nonce 不做事"退出。`inject=1`（`addScriptToEvaluateOnNewDocument`）对每个文档注入所以没这个问题——**两条路径行为差异优先查 `@match` 覆盖不到的中间跳转页**。
- 验证手法：写一个 `@match https://<站点>/*` 的桩脚本打印每一跳 `location.href`，比读日志快得多。OSS 默认域名下的 html 会被 `Content-Disposition: attachment` 强制下载，不能拿来当桩页。

## 边界
- 镜像若**没带策略文件**，种子 profile 里的强装扩展启动即被清理（Chrome 日志 `Skipping mandatory platform policies`）——叠层镜像必须同时 COPY 策略与 seed（09-13 线上踩过）。
- 以上为 Chrome 153 + Tampermonkey 5.5.0 的结论，Chrome 每个大版本都可能变。
