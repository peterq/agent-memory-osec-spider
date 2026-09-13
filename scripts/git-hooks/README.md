# scripts/git-hooks —— 提交信息违禁词钩子

`commit-msg` 钩子在每次 `git commit` 时用正则表检查提交信息，命中即拒绝并打印命中的行、正则和片段。
背景：远端仓库会拒绝含邮箱（如 `Co-Authored-By: xx <a@b.c>`）的提交，靠人记不住，改为本地钩子兜底。

```bash
scripts/git-hooks/install.sh                 # 安装到本仓库 + 1S 五个仓库(符号链接到本目录)
scripts/git-hooks/install.sh /path/to/repo   # 只装指定仓库
scripts/git-hooks/commit-msg /tmp/msg.txt    # 手动检查一个文件(退出码 1 = 命中)
```

- 违禁词表 `banned-patterns.txt`：一行一个 Python 正则，`#` 注释；改完立即生效，无需重装。初始：邮箱地址、`卧槽`。
- 钩子只检查会入库的内容：跳过注释行与 `git commit -v` 的 scissors 之后的 diff。
- 找表顺序：钩子同目录 → 环境变量 `GIT_BANNED_PATTERNS` → 仓库根 `.git-banned-patterns.txt` → 安装时记录的源目录（`.git/hooks/commit-msg.src`）。符号链接安装时同目录就是本目录。
- 跳过一次：`git commit --no-verify`（含邮箱时远端仍会拒绝，慎用）。
- 依赖：python3；`.git/hooks` 不入库，换机器需重跑 `install.sh`。
