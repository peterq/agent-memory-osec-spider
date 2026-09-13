#!/usr/bin/env bash
# 把 commit-msg 违禁词钩子安装到一个或多个 git 仓库的 .git/hooks/ 下.
# 用法: scripts/git-hooks/install.sh [仓库路径...]   (不传参数 = 本仓库 + 1S 五个仓库)
# 钩子以符号链接方式安装, 指向本目录, 违禁词表改一处全仓库生效; 已有非本钩子的 commit-msg 会先备份为 commit-msg.bak
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ONE_S="${ONE_S_ROOT:-/home/peterq/dev/projects/1s}"
if [ $# -eq 0 ]; then
  set -- "$SRC/../.." "$ONE_S"/enfi-resource-common "$ONE_S"/osec-spider-go "$ONE_S"/osec-resource-api "$ONE_S"/enfi-resource-storage "$ONE_S"/nc-js
fi
for repo in "$@"; do
  if ! hooks="$(git -C "$repo" rev-parse --git-path hooks 2>/dev/null)"; then
    echo "跳过(不是 git 仓库): $repo"; continue
  fi
  hooks="$(cd "$repo" && cd "$(dirname "$hooks")" && pwd -P)/$(basename "$hooks")"
  mkdir -p "$hooks"
  dst="$hooks/commit-msg"
  if [ -e "$dst" ] && [ ! -L "$dst" ]; then
    mv "$dst" "$dst.bak"; echo "已备份原有钩子: $dst.bak"
  fi
  ln -sfn "$SRC/commit-msg" "$dst"
  printf '%s\n' "$SRC" > "$hooks/commit-msg.src"   # 记录源目录, 钩子据此找违禁词表
  echo "已安装: $(cd "$repo" && pwd -P) -> $dst"
done
