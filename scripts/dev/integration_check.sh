#!/usr/bin/env bash
# 合并预演：在临时集成 worktree（分支 integration/<名>）上按顺序合并多个功能分支，
# 记录冲突文件后 abort 继续下一个，最后 go build。不碰 master、不 push。
#
# 用法: scripts/dev/integration_check.sh <repo> <集成名> <分支>...
#   repo ∈ common|spider|api|storage|ncjs
#   例: scripts/dev/integration_check.sh spider ten-proposals feat/delete-breaker feat/valid-unify
# 下游仓库 go.mod 的 replace 会临时指向 ../common-wt-<集成名>（不提交）。
# 重跑前先删旧集成 worktree: git -C <repo> worktree remove --force ../<repo>-wt-<集成名>; git branch -D integration/<集成名>
set -uo pipefail
ROOT=/home/peterq/dev/projects/1s
declare -A DIRS=([common]=enfi-resource-common [spider]=osec-spider-go [api]=osec-resource-api [storage]=enfi-resource-storage [ncjs]=nc-js)
r="$1"; name="$2"; shift 2
src="$ROOT/${DIRS[$r]}"; dest="$ROOT/$r-wt-$name"; br="integration/$name"
base=master; git -C "$src" show-ref --verify --quiet refs/heads/master || base=main
if [ -d "$dest" ]; then git -C "$src" worktree remove --force "$dest"; git -C "$src" branch -D "$br" >/dev/null 2>&1; fi
git -C "$src" worktree add -b "$br" "$dest" "$base" >/dev/null 2>&1 || { echo "建 worktree 失败"; exit 1; }
[ "$r" = spider ] && cp "$src/services/proxy-provider/change_proxy_config.go" "$dest/services/proxy-provider/" 2>/dev/null
if [ "$r" != common ] && [ "$r" != ncjs ] && [ -d "$ROOT/common-wt-$name" ]; then
  sed -i "s|=> ../enfi-resource-common|=> ../common-wt-$name|" "$dest/go.mod"
  git -C "$dest" commit -qm "temp(integration): replace 指向集成 COMMON, 合并 master 前必须撤销" -- go.mod
fi
echo "== $r 集成预演 ($br)"
conflicts=()
for b in "$@"; do
  if git -C "$dest" merge --no-ff --no-edit "$b" >/dev/null 2>&1; then
    echo "  ✅ $b"
  else
    files=$(git -C "$dest" diff --name-only --diff-filter=U | tr '\n' ' ')
    echo "  ❌ $b 冲突: $files"; conflicts+=("$b: $files")
    git -C "$dest" merge --abort
  fi
done
if [ "$r" = ncjs ]; then echo "  (ncjs 不编译)"; else
  if go build -C "$dest" ./... >/tmp/integ-$r.log 2>&1; then echo "  ✅ go build ./... 通过"; else echo "  ❌ go build 失败, 见 /tmp/integ-$r.log"; tail -20 /tmp/integ-$r.log; fi
fi
[ ${#conflicts[@]} -eq 0 ] && echo "  无冲突" || printf '  冲突汇总: %s\n' "${conflicts[@]}"
