# 合并清单（待用户确认；未确认不合并、不 push）

## 集成分支（已按顺序合并全部功能分支、冲突已解决、断网 CI 全绿）

| 仓库 | 集成分支 / worktree | HEAD | 包含的功能分支 |
|---|---|---|---|
| COMMON | `integration/ten-proposals` / `common-wt-ten-proposals` | `c0dca69` | delete-breaker, valid-unify, health-observe, ci, secrets |
| SPIDER | 同上 / `spider-wt-ten-proposals` | `7e79501` | delete-breaker, valid-unify, startup-selfcheck, health-observe, ci, secrets, deploy-rollback, crawler-skeleton |
| API | 同上 / `api-wt-ten-proposals` | `6c413b6` | delete-breaker, valid-unify, startup-selfcheck, ci, secrets, deploy-rollback, search-config |
| STORAGE | 同上 / `storage-wt-ten-proposals` | `1a47033` | startup-selfcheck, ci, secrets, deploy-rollback |
| NC-JS | `feat/health-observe` / `ncjs-wt-health-observe` | `66ec854` | 健康监测两页 + 告警规则绝对阈值 |

各功能分支最终提交：10 delete-breaker COMMON `4a9f9e9`/SPIDER `75a44e4`/API `c6c1009`；20 valid-unify COMMON `6911095`/SPIDER `dfd6343`/API `23eba5d`；30 startup-selfcheck SPIDER `4ee99b1`/API `9d0f7da`/STORAGE `a153eef`；40 health-observe COMMON `69acf64`/SPIDER `161483b`；50 ci COMMON `4b522ba`/SPIDER `bdedb7e`/API `20b4055`/STORAGE `670f28a`；60 secrets COMMON `4585cc0`/SPIDER `bb9643c`/API `13ee22f`/STORAGE `10d5615`；70 deploy-rollback SPIDER `05191ec`/API `2fd598e`/STORAGE `ea772c8`；80 crawler-skeleton SPIDER `3805fb0`；85 search-config API `7677fcf`。

## 合并到 master 的步骤（主控执行，需用户一句确认）

1. COMMON：`master` ← `integration/ten-proposals`（`--no-ff`），`go build ./...`。
2. SPIDER/API/STORAGE：先在集成分支撤销 `temp(integration)` 那条 go.mod 提交（replace 改回 `../enfi-resource-common`），`go build`（此时吃到的是已合并的 COMMON master），再 `master` ← 集成分支。
3. NC-JS：`main` ← `feat/health-observe`。
4. 全部合并后各仓库跑一次 `scripts/ci.sh`，然后由用户决定 push 与上线顺序。
5. 清理 26 个 worktree 与 `integration/*`、`feat/*` 分支（`git merge-base --is-ancestor` 确认后）。

## 上线前置项（用户处理）

- GitHub 四仓库配 secret：`COMMON_REPO_TOKEN`、`PAN_REPO_TOKEN`、`PAN_CLIENT_CORE_REPO_TOKEN`、`SPIDER_REPO_TOKEN`（同一个有权限的 token 可复用）。
- FC 函数 `resource_download_fc/download2oss` 部署前在 FC 控制台配置 `OSS_ACCESS_KEY_ID`/`OSS_ACCESS_KEY_SECRET`，否则该函数上线即全部失败。
- 网关容器环境需已有上述 OSS 变量（`web_res`/`download_worker` 改读环境变量，缺失 panic）。
- `deploy.sh` 新机制（releases/current/rollback/健康检查）先在 `osec-restest` 演练；首次部署自动迁移目录布局，旧 `.old` 文件保留。
- 删除熔断器：三处 yaml 先开 `breaker.dry_run: true` 观察 ≥1 天，用 `tools/delbreaker-ctl -status` 校准阈值（缺省 600s/2000 条/50%/最少 200 样本）后关闭 dry_run 并 `-reset`。
- 凭据轮换清单在 secrets 角色汇报里（不落记忆）；下载链 AES 密钥与 CDN 边缘脚本共用，需协调发布窗口后再迁。
- `config-audit` 已复现 API 与 STORAGE 的 ES 主机不一致，需人工确认 API `config.yaml` 的 ES 集群是否过期。
- ListQueue 修复后从「恒空」变为真实返回，确认无下游依赖旧行为；账号探测首轮真实效果需观察。
- STORAGE 新增 `startup.metrics_addr`（缺省 `:9188`）确认端口不冲突。

## 已知残留（非阻塞）
- `01-index.md` 因多角色并行写入超 20000 字，收尾时由主控精简。
- gitleaks 对同时含 `[extend]` 与自定义 `[[rules]]` 的配置会静默忽略自定义规则（v8.30.1 实测），已改用 pre-commit 脚本 grep 兜底。
