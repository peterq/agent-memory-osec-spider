# 合并预演结果（five-sites → integration/five-sites）

执行时间：2026-09-16。执行人：version 子 agent，严格按 `96-merge.md` 步骤操作，全程前台命令，未 push、未合 master、未删除任何 worktree/分支。

## 集成分支

- Worktree：`/home/peterq/dev/projects/1s/spider-wt-five-sites`
- 分支：`integration/five-sites`，基线 `integration/ten-proposals`（`7e79501`）
- **HEAD：`94030a0`**（`merge: feat/site-ddys 并入 integration/five-sites`）

```
94030a0 merge: feat/site-ddys 并入 integration/five-sites
996b940 merge: feat/site-xiaozi 并入 integration/five-sites
685ba44 merge: feat/site-qileso 并入 integration/five-sites
7eddcd1 merge: feat/site-jsnoteclub 并入 integration/five-sites
5142735 merge: feat/site-duanjuso 并入 integration/five-sites
6d55b97 temp(integration): go.mod replace 指向 common-wt-ten-proposals, 合并 master 前撤销
7e79501 Merge branch 'feat/secrets' into integration/ten-proposals   # 基线
```

准备步骤：`git worktree add -b integration/five-sites ../spider-wt-five-sites integration/ten-proposals`；从主检出复制 `services/proxy-provider/change_proxy_config.go`（该文件是仓库唯一未入 git 的密钥文件，`.gitignore` 忽略，new worktree 天然没有，复制后不产生 git 改动）；`go.mod` 的 `enfi-resource-common` replace 从 `../enfi-resource-common` 改为 `../common-wt-ten-proposals` 并单独提交一次（`temp(integration): ...`），使后续 5 次合并都不再触碰 `go.mod`。

## 五次合并：冲突文件与解法

合并顺序：`feat/site-duanjuso(5ebd118)` → `feat/site-jsnoteclub(57ccff8)` → `feat/site-qileso(7bd9628)` → `feat/site-xiaozi(0d5176d)` → `feat/site-ddys(4617930)`。每次合并后立即 `go build ./...`，全部一次通过再进行下一次合并。

| 分支 | 冲突文件 | 解法 |
|---|---|---|
| feat/site-duanjuso | 无冲突 | 直接 `git merge --no-ff` 成功（新增文件 + 对 `config/config.go`/`config/crawler/crawler.go`/`commands_crawler.go` 的插入未与基线冲突） |
| feat/site-jsnoteclub | `config/crawler/crawler.go` | `Services` 结构体字段冲突：两边都在 `Misoso` 之后追加了自己的站点字段。解法：全部保留，按字母序排在末尾——`Duanjuso, Jsnoteclub`。`config/config.go`、`commands_crawler.go` 自动合并成功、无冲突 |
| feat/site-qileso | `config/crawler/crawler.go`、`config/config.go`、`commands_crawler.go` 三处均冲突 | `crawler.go`：`Services` 字段按字母序追加为 `...Duanjuso, Jsnoteclub, Qileso`。`config.go`：两边各自独立定义 `JsnoteclubConfig`/`QilesoConfig` 类型块，位置相邻、内容互不重叠，两个类型块原样保留（先 J 后 Q）。`commands_crawler.go`：`bbs_jsnoteclub`、`bbs_qileso` 两行都保留，顺序即字母序 |
| feat/site-xiaozi | `config/crawler/crawler.go`、`config/config.go`、`commands_crawler.go` 三处均冲突 | 同上模式：`crawler.go` 追加为 `...Duanjuso, Jsnoteclub, Qileso, Xiaozi`；`config.go` 里 `DuanjusoConfig`/`XiaoziConfig` 两个类型块相邻冲突，原样保留（先 D 后 X，位置在 `FuxipanConfig` 之后、`HaisouConfig` 之前）；`commands_crawler.go` 里 `bbs_qileso`、`bbs_xiaozi` 两行都保留 |
| feat/site-ddys | 仅 `config/crawler/crawler.go` 冲突；`config/config.go`、`commands_crawler.go` 自动合并成功 | `crawler.go`：`Services` 字段最终追加为字母序全集 `Ddys, Duanjuso, Jsnoteclub, Qileso, Xiaozi`（插在 `Misoso` 之后） |

**最终 `config/crawler/crawler.go` 的 `Services` 结构体字段顺序**（基线字段保持原序，5 个新站点字段按字母序追加在末尾）：
```go
Proxy, Share, Keyword, Kkpans, Dyyjmax, Feikuai, Fuxipan, Haisou, Kuakes, Misoso,
Ddys, Duanjuso, Jsnoteclub, Qileso, Xiaozi
```

`config/config.go` 里 5 个新站点的类型定义（`DdysConfig`/`DuanjusoConfig`/`JsnoteclubConfig`/`QilesoConfig`/`XiaoziConfig`）没有相互冲突（各自站点独立提交只在自己的插入点冲突过一次，且都是"新增类型块 vs 新增类型块"的相邻冲突，两块内容本身互不重叠），全部原样保留，未做整体重排；`commands_crawler.go` 里 5 行 `bbs_*` 注册全部保留，登记顺序为 `ddys, duanjuso, kkpans, dyyjmax, feikuai, fuxipan, kuakes, misoso, jsnoteclub, qileso, xiaozi`（ddys 因 diff 定位被自动合并插到了 `keyword_pansearch_me` 之后、`bbs_kkpans` 之前，其余四个集中在 `bbs_misoso` 之后——**未做人工重排**，均是 git 自动合并结果，不影响功能，仅供关注）。

## 合完后验证

```bash
cd /home/peterq/dev/projects/1s/spider-wt-five-sites
go build ./...                              # 通过，无输出
go vet ./services/bbs/                      # 通过，无输出
go vet -tags live ./services/bbs/           # 通过，无输出
go test ./services/bbs/ -count=1            # ok，0.011s
```

补充验证（不在 96-merge.md 硬性要求内，但用于确认"联网用例应全部 Skip"这一条真正生效）：5 个新站点的 `_test.go` 都带 `//go:build live` 构建标签，不加 `-tags live` 时这些测试文件根本不参与编译，`go test ./services/bbs/ -count=1` 只跑了 1 个通用测试（`TestEngineConfigMinRequestIntervalNotDropped`）。加上 `-tags live` 后（仍不带任何 `*_IT` 环境变量）重跑：

```bash
go test -tags live ./services/bbs/ -count=1 -v
```
结果 `PASS`，5 个新站点的联网集成测试（`TestDdysSitemapStructure`/`TestDdysHandleEntrySample`/`TestDdysIncrementalHeadWindow`/`TestDdysFullSweepSkipWait`、`TestDuanjusoSearchSample`/`TestDuanjusoDetailSample`/`TestDuanjusoIncrementalSample`/`TestDuanjusoFullSweepSkipWait`、`TestJsnoteclubSitemapPosts`/`TestJsnoteclubArticleSample`/`TestJsnoteclubYunpan`、`TestQilesoFetchSample`/`TestQilesoWatermarkProbeBeyondBoundary`/`TestQilesoFetchKnownContentAndDedup`、`TestXiaoziSitemapIndex`/`TestXiaoziSitemapSample`/`TestXiaoziIncrementalWatermarkProbe`/`TestXiaoziFullSweepStartupSkip`）全部 `SKIP`，纯本地解析/正则类单元测试全部 `PASS`，与其余 6 个既有站点（kkpans/dyyjmax/feikuai/fuxipan/kuakes/misoso）的既有行为一致。

```bash
grep -n 'bbs_duanjuso\|bbs_xiaozi\|bbs_qileso\|bbs_jsnoteclub\|bbs_ddys' commands_crawler.go
```
5 行全部命中，子命令注册齐全。

存量问题：本次未运行仓库级 `go vet ./...` / `go test ./...`（96-merge.md 明确只看 `services/bbs/` 与新增文件），已知仓库存量 vet/test 问题（`services/alipan`、`services/quark`、`gateway` 等）未涉及、未修改。

## 给用户的合并到 master 顺序说明

1. 先把 `integration/ten-proposals`（十项提案集成分支）合入 master。
2. 合并前撤销 `integration/ten-proposals` 及本分支各自的 `temp(*): go.mod replace 指向 common-wt-ten-proposals` 提交/改动，把 `go.mod` 的 `enfi-resource-common` replace 指回正式路径（或按上线时的真实依赖方式处理，不应把开发期 worktree 相对路径带上线）。
3. 再合并 `integration/five-sites` 到（已经合并了十项提案且撤销 temp go.mod 的）master。
4. 合并后建议按站点在 `config*.yaml` / `config.prod.yaml` 里各加一节 `<site>` 配置（本次任务规则禁止子 agent 改这些文件，需人工或后续任务补齐），否则 5 个新 `bbs_*` 子命令使用默认值启动。

## 结论

5 个站点分支已全部成功合并进 `integration/five-sites`，每步 `go build ./...` 均一次通过；合完后 `go build`、`go vet ./services/bbs/`（含 `-tags live`）、`go test ./services/bbs/`（含 `-tags live`）全部通过，5 个新子命令注册齐全。冲突只出现在 3 处预期的纯增量文件，且冲突模式与预期一致（各分支各自追加一个 `<Site>Config` / `Services.<Site>` 字段 / 一行子命令），已按"全部保留、`Services` 结构体字段按字母序排列"解决，无需回退重来。未 push、未合 master、未删除任何 worktree 或分支，留待用户确认。
