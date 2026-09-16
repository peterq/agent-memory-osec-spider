# scripts/docspider —— 文档爬虫云端脚本的验证脚本

| 脚本 | 用途 |
|---|---|
| `e2e-local-fcchrome.sh <文档URL> [dist-cloud 目录] [超时秒]` | 本机 fc-chrome + 本机 Chrome 端到端跑云端脚本(inject 模式), 打印 `[[DOC_SPIDER]]` 终态摘要; 不碰线上 FC/OSS |

腾讯文档不起 Chrome 的批量验证用 userscripts 仓库的 `pnpm exec vite-node scripts/qqdoc-verify.ts <url...>`（见该仓库 README）。
线上 FC 验证：`procedures/workflow-fc-chrome上线.md`（wss://fc-resource-node-api.krzb.net/cdp3/chrome + 测试 OSS 路径，勿覆盖线上 `kdoc.user.js`）。
