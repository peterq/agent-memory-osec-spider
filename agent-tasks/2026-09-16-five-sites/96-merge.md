# 合并预演简报（version 子 agent 专用）

目标：把 5 个站点分支合成一个集成分支 `integration/five-sites`，逐站合并、逐站编译，**不合 master、不 push**，留给用户确认。全部用中文。

## 前提

- 基线：SPIDER `integration/ten-proposals`（`7e79501`），其 worktree `/home/peterq/dev/projects/1s/spider-wt-ten-proposals` 里有一条**未提交**的 go.mod 改动（replace 指向 `../common-wt-ten-proposals`）；5 个站点分支各自带一条内容相同的 `temp(site): go.mod replace …` 提交。
- 站点分支（均已验收通过，见同目录 `9x-review-*.md`）：`feat/site-duanjuso`、`feat/site-xiaozi`、`feat/site-qileso`、`feat/site-jsnoteclub`、`feat/site-ddys`。
- 预期冲突面只有三处纯增量文件：`config/config.go`（各加一个 `<Site>Config`）、`config/crawler/crawler.go`（`Services.<Site>` 字段）、`commands_crawler.go`（一行注册）。解法统一：**全部保留、按字母序排列**。

## 步骤（每步命令写全，前台执行，禁止 Monitor/后台等待）

```bash
cd /home/peterq/dev/projects/1s/osec-spider-go
git worktree add -b integration/five-sites ../spider-wt-five-sites integration/ten-proposals
cp services/proxy-provider/change_proxy_config.go ../spider-wt-five-sites/services/proxy-provider/
cd ../spider-wt-five-sites
# 先把 go.mod replace 改成与站点分支一致并提交（这样后续 5 次合并 go.mod 不冲突）
sed -i 's#github.com/1s/enfi-resource-common => ../enfi-resource-common#github.com/1s/enfi-resource-common => ../common-wt-ten-proposals#' go.mod
git add go.mod && git commit -m "temp(integration): go.mod replace 指向 common-wt-ten-proposals, 合并 master 前撤销"
for b in feat/site-duanjuso feat/site-jsnoteclub feat/site-qileso feat/site-xiaozi feat/site-ddys; do
  git merge --no-ff "$b" -m "merge: $b 并入 integration/five-sites" || { echo "冲突: $b"; break; }
  go build ./... || { echo "编译失败: $b"; break; }
done
```
冲突时：`git status` 看文件，手工按「全部保留、字母序」编辑，`go build ./...` 通过后 `git add` + `git commit`（沿用上面的 merge 信息），再继续下一个分支。**每合一个必须 `go build ./...` 通过再合下一个**。

## 合完后的验证

```bash
go build ./... && go vet ./services/bbs/ && go vet -tags live ./services/bbs/
go test ./services/bbs/ -count=1            # 不带任何 *_IT 环境变量，联网用例应全部 Skip
grep -n 'bbs_duanjuso\|bbs_xiaozi\|bbs_qileso\|bbs_jsnoteclub\|bbs_ddys' commands_crawler.go
git log --oneline --first-parent -8
```
仓库有大量**存量** vet/test 问题（alipan/quark/gateway/devops…），只看 `services/bbs/` 与新增文件，存量问题如实列出不修。

## 产出

`agent-tasks/2026-09-16-five-sites/97-merge-result.md`：集成分支 HEAD、5 次合并各自的冲突文件与解法、build/vet/test 输出摘录、给用户的「合并到 master 的顺序」说明（先合十项提案 → 撤销 temp go.mod 提交 → 合 `integration/five-sites`）。不 push、不删任何 worktree/分支。
