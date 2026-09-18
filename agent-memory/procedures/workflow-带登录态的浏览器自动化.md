---
title: 工作流：带登录态的浏览器自动化（agent-browser + cdp）
type: procedure
status: active
created_at: 2026-09-08T16:00:00+08:00
updated_at: 2026-09-18T10:50:00+08:00
priority: medium
keywords:
  - agent-browser
  - cdp.py
  - CDP
  - 调试浏览器
  - remote-debugging-port
  - user-data-dir
  - 浏览器自动化
  - 登录态复用
summary: 如何启动/复用一个带登录态的调试Chrome并用CDP脚本驱动它, 含"默认profile会被安全策略拦截"的前提坑
questions:
  - 我要测浏览器可见的交互，带登录态的浏览器怎么起
  - agent-browser.sh / cdp.py 怎么用
load: rarely
related:
  - agent-memory/lessons/success-桩网关加cdp浏览器做登录链路联调.md
  - agent-memory/lessons/failure-握手回包附加字段被传输层丢弃.md
---

# 带登录态的浏览器自动化

## 前提（踩过的坑）

Chrome 出于安全策略，在**默认 profile**（`~/.config/google-chrome`）上开
`--remote-debugging-port` 会被拦截并提示换 user-data-dir。因此必须用一个**独立的**
`--user-data-dir`；本仓库固定用 `MEMORY/.agent-browser/profile`（已在 `.gitignore` 中
排除，含 cookie 等敏感数据，**严禁提交**）。

人工在这个 profile 里登录一次（GitHub / 其他后台）之后，登录态会长期保留，
后续任意会话都能直接复用，不用重复走人工授权。

## 工具

| 脚本 | 作用 |
|---|---|
| `MEMERY/scripts/agent-browser.sh` | 启动/查看/关闭调试 Chrome，管理独立 profile |
| `MEMERY/scripts/cdp.py` | 通过 Chrome DevTools Protocol 驱动该浏览器：导航、求值、填表、截图 |

## 用法

```bash
# 启动（已在跑则不重复启动），默认端口 9222，可用 AGENT_BROWSER_PORT 覆盖
./scripts/agent-browser.sh start [url]
./scripts/agent-browser.sh status   # 查看调试端口是否可用
./scripts/agent-browser.sh tabs     # 列出当前标签页(id/title/url)
./scripts/agent-browser.sh stop     # 关闭

# 用 cdp.py 驱动
./scripts/cdp.py tabs                          # 列出页面标签(序号/标题/地址)
./scripts/cdp.py nav <url> [--tab N]           # 导航并等加载完成
./scripts/cdp.py new <url>                     # 新开标签
./scripts/cdp.py eval '<js 表达式>' [--tab N]   # 页面里求值(支持 await), 打印 JSON 结果
./scripts/cdp.py text [--tab N] [--max 4000]   # 打印 body.innerText
./scripts/cdp.py shot <文件路径> [--tab N]      # 截图存为 png
```

要点：
- `eval` 的表达式会被包进 async 函数，可以直接写 `await fetch(...)` 这类异步代码；
  返回值必须能 JSON 序列化。
- **表单输入的可靠做法**：用 `eval` 直接设 DOM 的 `value` 再派发 `input`/`change` 事件，
  不要指望能模拟真实按键。
- 无图形环境时给 `agent-browser.sh` 导出 `DISPLAY` 或改用 `--headless=new`
  （脚本里 `DISPLAY` 缺省取 `:1`）。

## 结合桩服务做端到端联调

配合"只保留被测链路的桩服务"（见 `lessons/success-桩网关加cdp浏览器做登录链路联调.md`）：
启动桩服务 → 启动/复用调试浏览器 → `cdp.py nav` 打开前端页面 → `cdp.py eval` 观察 DOM
状态或触发交互 → `cdp.py text`/`shot` 核对结果。这是目前验证"浏览器可见交互 + 多跳传输
链路"类改造最省事的手段。

## 注意事项

- profile 目录含真实登录态，任何截图/DOM dump 若可能带出敏感信息（token、邮箱等），
  分享前自行核对脱敏。
- 每次会话结束不必关闭调试浏览器，长期驻留、下次直接复用是设计初衷。

## 代码位置

- `osec-spider-go/tools/stubgw`（桩网关，只保留被测链路）
