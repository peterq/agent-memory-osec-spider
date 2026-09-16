# 角色 60：密钥治理（提案 9）

短名 `secrets`。worktree：`common-wt-secrets`、`spider-wt-secrets`、`api-wt-secrets`、`storage-wt-secrets`（分支 `feat/secrets`）。

## 目标

仓库里的明文凭据（AK/SK、ES/MySQL/Redis 口令、OSS、S3、RefreshToken、BDUSS、Cookie）迁出源码与提交范围；加密钥扫描防再犯。
**不轮换凭据、不改写 git 历史**（都是用户的事，汇报里列清单建议）。

## 必读

`agent-memory/current/risks.md` R2、R7；`agent-memory/current/tasks-backlog.md` 「P2 安全（凭据轮换）」「P3 清理 蜻蜓代理」；SPIDER `.gitignore`（`*.hide.*` 约定）、`scripts/new_worktree.sh` 注释（`change_proxy_config.go` 的处理方式）；配置加载代码（SPIDER `config/`、API `config/config.go`、STORAGE `config/config.go`）看有没有环境变量/`OSS_CONFIG_URL` 覆盖机制。

## 要做的事

1. 盘点：四仓库 `grep` 明文凭据（`AccessKeySecret|access_key_secret|BDUSS|refresh_token|password:|passwd|secret` 等，含 `*.go`、`*.yaml`、`*.sh`、`*.json`、`_note/`），列成表：文件、字段、类型、是否已进 git 历史、处置方式。**表里不写值。**
2. 源码内硬编码（如 `services/devops/.../devops_online_env.go`、两份下载测试 `alipan_dl_test.go`/`bnd_dl_test.go`、`proxy-provider.go` 的 `qtWhitelistLink` 死值、STORAGE `services/save-worker/save-torrent.go`、API `resource-admin/`、`services/forbidden/content.go` 等 grep 命中的）：改为从 `*.hide.json`（gitignore）或环境变量读取，缺失时测试 `t.Skip`、运行时报明确错误；给每处留 `*.hide.json.example`（占位值）。
3. 配置 yaml 里的口令：保持文件不动（线上靠它跑，改了要重部署），但在 `config/` 加载代码里支持环境变量覆盖（`ENV:` 前缀或 `${VAR}` 展开，选一种，四仓库一致），README 写用法；`_note/config/*` 若含凭据，评估能否 gitignore（已在历史里的说明即可）。
4. 扫描：四仓库加 `.gitleaks.toml`（allowlist 历史误报路径）+ `.github/workflows/secrets.yml`（gitleaks，只扫 PR diff）+ `scripts/pre-commit-secrets.sh`（gitleaks protect --staged，没装就提示安装并退出 0）+ `git config core.hooksPath` 说明。本机若有 gitleaks 就跑一遍现状扫描，结果计数写进汇报（不贴内容）。
5. 汇报里单列「建议轮换清单」（凭据类型、所在系统、影响面）。

## 文件所有权

四仓库：上述 grep 命中的源码文件（`alipan_dl_test.go`/`bnd_dl_test.go` 只改内容不加 build 标签，`ci` 角色加标签）、`config/` 加载代码（只加环境变量覆盖）、`.gitleaks.toml`、`.github/workflows/secrets.yml`、`scripts/pre-commit-secrets.sh`、`*.hide.json.example`、README 一节。**不动** `config*.yaml` 内容、`deploy.sh`。

## 验证

四仓库 `go build ./...`；改过的包 `go vet`/`go test`（凭据缺失时应 Skip 而非失败）；`grep` 复扫确认源码里无明文值残留；确认你的提交里没有把 `*.hide.json` 或任何值提交进去（`git show --stat` + `git diff master --  | grep -i` 抽查）。

## 交付

盘点表（无值）、改动清单、环境变量约定、扫描结果计数、轮换建议清单。
