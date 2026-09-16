#!/usr/bin/env bash
# 为跨仓库并行开发一次性创建多个仓库的 git worktree（与 enfi-resource-common 同级，
# 保证 go.mod 的相对 replace 生效）。
#
# 用法: scripts/dev/new_worktree_all.sh <分支名> <短名> <repo>...
#   repo ∈ common | spider | api | storage | ncjs
#   例: scripts/dev/new_worktree_all.sh feat/valid-unify valid-unify common spider api
#
# 生成目录: /home/peterq/dev/projects/1s/<repo前缀>-wt-<短名>
#   common → common-wt-<短名>    spider → spider-wt-<短名>（复用 SPIDER 自带脚本, 会补齐 gitignore 源码）
#   api    → api-wt-<短名>       storage → storage-wt-<短名>     ncjs → ncjs-wt-<短名>
# 分支已存在则直接检出到 worktree；目录已存在则跳过。
set -euo pipefail
ROOT=/home/peterq/dev/projects/1s
BRANCH="${1:?用法: $0 <分支名> <短名> <repo>...}"; SHORT="${2:?缺短名}"; shift 2
declare -A DIRS=([common]=enfi-resource-common [spider]=osec-spider-go [api]=osec-resource-api [storage]=enfi-resource-storage [ncjs]=nc-js)
for r in "$@"; do
  src="$ROOT/${DIRS[$r]:?未知 repo $r}"; dest="$ROOT/$r-wt-$SHORT"
  if [ -d "$dest" ]; then echo "跳过(已存在): $dest"; continue; fi
  if [ "$r" = spider ]; then
    "$src/scripts/new_worktree.sh" "$BRANCH" "spider-wt-$SHORT" >/dev/null
  elif git -C "$src" show-ref --verify --quiet "refs/heads/$BRANCH"; then
    git -C "$src" worktree add "$dest" "$BRANCH" >/dev/null
  else
    git -C "$src" worktree add -b "$BRANCH" "$dest" master >/dev/null
  fi
  echo "worktree: $dest  分支: $BRANCH"
done
