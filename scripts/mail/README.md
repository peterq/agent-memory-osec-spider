# scripts/mail — Markdown 邮件汇报

给不在电脑旁的用户发任务进度 / 异常 / 完成汇报。正文写 Markdown，`notify.py` 渲染成内联样式 HTML 卡片（顶部色条 + 级别徽标 + 标题 + 元信息 + 正文 + 页脚），POST 到 cf-worker 的 `notify_admin` 接口（JSON `{subject, htmlContent, source}`，同 `scripts/notify-admin.sh`）。

## 用法

```bash
scripts/mail/notify.py -s "主题" -f body.md -l progress --kv 阶段=D --kv 进度=31%
echo "- 一行进度" | scripts/mail/notify.py -s "主题"                 # stdin
scripts/mail/notify.py -s "主题" -m "**异常**：ssh 三次失败" -l error  # 字符串正文
scripts/mail/notify.py -s "主题" -f body.md --preview /tmp/x.html    # 只渲染不发
scripts/mail/notify.py -s "主题" -f body.md --dry-run                # 不发, 打印摘要
```

| 参数 | 说明 |
|---|---|
| `-s` | 主题，脚本自动加 `【进度】/【完成】/【注意】/【异常】/【通知】` 前缀；`--no-prefix` 关闭 |
| `-f` / `-m` | 正文来源：文件（`-` 为 stdin）或字符串；都不给则读 stdin |
| `-l` | `progress`(蓝, 默认) `done`(绿) `warn`(黄) `error`(红) `info`(灰) |
| `--kv 键=值` | 顶部元信息行追加字段（时间/来源/主机为默认项），可重复 |
| `--source` | 接口的 source 字段，缺省 `agent-task`，建议按任务命名便于过滤 |
| `--url` | 接口地址，缺省 `https://cf-worker.peterq.cn/notify_admin` |

退出码：0 成功 / 2 参数错误 / 3 发送失败（网络或非 2xx）。

## 写正文的约定

- 只用标题、列表、表格、粗体、行内代码、引用、代码块（都已配内联样式，Gmail/Outlook/手机端可正常显示）。
- 第一段一句话说结论，异常邮件把「影响 + 已做处理 + 需要用户做什么」放最前。
- 长日志放代码块并截断到 ≤30 行；再长的放文件路径让用户回来看。
- 不写明文密钥/口令（参见 `02-user-preferences.md` 第 10 条）。

## 何时发（用户要求 2026-09-15，见 `procedures/workflow-任务进度邮件汇报.md`）

长任务开始 / 关键里程碑 / 异常与阻塞（立即）/ 完成；巡检类按固定间隔（如 `search_canary_report.sh` 每 30 min）。

## 实现说明

- 渲染用 `python3-markdown`（3.5.2，扩展 tables/fenced_code/sane_lists/nl2br）；未安装时退化为 `<pre>`。
- 邮件客户端普遍忽略 `<style>`，故用正则给常见标签补 `style=`（`TAG_STYLE` 表），要改样式改这张表。
- 接口前有 Cloudflare，python-urllib 默认 UA 会被拒（403 `error code: 1010`），脚本已固定自定义 UA；换 HTTP 客户端时同样要带 UA。
- 预览可用 `google-chrome --headless=new --screenshot=/tmp/x.png file:///tmp/x.html` 截图检查。
