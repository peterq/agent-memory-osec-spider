# 角色 70：部署回滚与灰度（提案 10）

短名 `deploy-rollback`。worktree：`spider-wt-deploy-rollback`、`api-wt-deploy-rollback`、`storage-wt-deploy-rollback`（分支 `feat/deploy-rollback`）。

## 目标

三仓库 `deploy.sh`：保留最近 N 版二进制、`rollback` 子命令、部署后健康检查、双机（gateway 在 osec-res1/res2）逐台部署并在第一台健康后才做第二台。
**绝不实际执行部署**：所有验证靠 `--dry-run`（只打印将执行的 ssh/scp/docker 命令）与 shellcheck；主控合并后由用户在测试机演练。

## 必读

`agent-memory/procedures/workflow-部署.md`、`workflow-部署-历史补充.md`；`agent-memory/current/risks.md` R5、R8；SPIDER `deploy.sh` 全文（584 行：`deploy`/`buildSpider`/`dockerRun`/`deployService`/`redeployHost`/`main`）；API、STORAGE `deploy.sh`（STORAGE 仍有 `mv storage storage.old` 的单版回滚）。

## 设计

1. 远端目录约定 `releases/<时间戳>-<gitsha>/<二进制>` + `current` 软链；`dockerRun` 挂载 `current`（或启动命令指向 `current/<bin>`）；保留 `KEEP=5` 版，旧的清理。
2. 子命令：`deploy <svc> [hosts]`（原行为 + 新目录约定）、`rollback <svc> [--to <版本>] [hosts]`（默认上一版；打印候选版本列表）、`releases <svc> <host>`、`health <svc> <host>`。
3. 健康检查：容器 running + 进程存活 + 可选 HTTP/gRPC 探针（网关有 gRPC 端口、API 有 HTTP；用 `deploy.sh` 里已有的端口/主机变量），失败自动 `rollback` 并非零退出。
4. 双机：主机列表按顺序逐台；第一台健康检查通过后（可配置等待秒数）再做下一台；任一台失败停止并回滚该台。
5. `--dry-run`：全局开关，所有 ssh/scp/docker 命令只 echo。
6. 每个仓库 `deploy.sh` 顶部注释 + `scripts/deploy.md`（用法、目录约定、回滚步骤、首次迁移到新目录约定的一次性步骤——现网是旧布局，必须写清「首次 deploy 会怎样、`spider.old` 还能不能用」）。
7. 三仓库风格尽量一致；SPIDER 是主脚本，API/STORAGE 照其抽公共函数（可放 `scripts/deploy_lib.sh` 三份同源拷贝，注明同源）。

## 文件所有权

三仓库：`deploy.sh`、`scripts/deploy_lib.sh`、`scripts/deploy.md`。不动其他文件；不动 `_note/`。

## 验证

`shellcheck deploy.sh scripts/deploy_lib.sh`（没装就 `bash -n`）；`./deploy.sh --dry-run deploy gateway`、`--dry-run rollback gateway`、`--dry-run rollback --to <假版本>` 输出贴进汇报；`bash` 单测可用 `bats`（有就用，没有就写 `scripts/deploy_test.sh` 用假 ssh 函数）。

## 交付

分支/提交、子命令说明、首次迁移步骤、dry-run 输出、需要用户在测试机演练的清单（`osec-restest`）。
