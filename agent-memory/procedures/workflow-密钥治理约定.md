---
title: 密钥治理约定（测试凭据/配置敏感字段/gitleaks）
type: procedure
status: active
created_at: 2026-09-16T10:40:00+08:00
updated_at: 2026-09-16T18:50:00+08:00
priority: medium
keywords: [密钥治理, gitleaks, hide.json, 环境变量覆盖, secrets, AK/SK]
summary: 四仓库密钥约定：测试凭据 *.hide.json、配置 ${VAR} 环境变量覆盖、gitleaks 三件套；自定义规则与 [extend] 同用会静默失效
questions:
  - 测试文件需要真实账号凭据时该怎么写不进 git
  - 配置文件里的敏感字段怎么支持环境变量覆盖又不用改 yaml
load: on-demand
related:
  - agent-memory/current/risks.md
  - agent-memory/current/tasks-backlog.md
---

# 密钥治理约定

2026-09-16 密钥治理排查（agent-tasks/2026-09-16-ten-proposals/60-secrets.md）在 COMMON/SPIDER/
API/STORAGE 四仓库 `feat/secrets` 分支（未合并 master）落地，供后续新增代码复用，避免重蹈覆辙。

## 1. 测试代码需要真实账号/密码时

**不要**把真实值写进 `_test.go`（哪怕注释掉——commit 历史还在）。约定：

- 凭据放本地 `<name>.hide.json` 文件，文件名匹配仓库 `.gitignore` 的 `*.hide.*` 规则，永远不进 git。
- 仓库里只提交 `<name>.example.json`（占位值模板）。**注意文件名**：`.example.json` 不能再包含
  `.hide.` 子串（例如 `foo.hide.json.example` 会被 `*.hide.*` 连带忽略，导致 `.example` 模板也提交
  不上去；正确写法是 `foo.example.json`）。
- 路径默认写死在测试代码里（图省事，与原作者机器保持一致），但支持环境变量覆盖
  （如 `BND_ACCOUNTS_HIDE_JSON`/`ALIPAN_ACCOUNTS_HIDE_JSON`），方便其他机器/worktree 跑。
- 文件不存在时 `t.Skip`（带清晰提示，指向 `.example.json` 与环境变量名），**不 panic**、不影响
  `go test ./...` 整体通过。
- 参考实现：SPIDER `services/gateway/download_scheduler/pan_download/bnd_download/
  testutil_hide_account_test.go`、`alipan_download/testutil_hide_account_test.go`。

一次性调试脚本（`.sh`/`.js`/`package main` 的 `.go`）里需要真实 Cookie/Token 时，改从环境变量
读取，缺失时给清晰提示后退出（`: "${VAR:?提示}"` / `os.Getenv` + 判空 panic/exit），不要求
这类脚本也做 hide.json（没有复用价值，一个环境变量足够）。

## 2. 配置文件（config.yaml 等）里的敏感字段

**不改配置文件内容**（线上靠它跑，改了要重新分发+重启，属于独立排期的凭据轮换动作）。
新增的是可选迁移路径：把某个字段的值整段替换成 `"${VAR_NAME}"` 占位符，配置加载代码在
反序列化后用反射扫一遍，整段等于 `${VAR_NAME}` 的字符串字段替换成同名环境变量的值；
环境变量未设置时保留占位符原样（不报错）。

- SPIDER：`config/internal/loader/loader.go` 的 `expandEnvPlaceholders`，在
  `config_util.WithYamlMarshalOnChange` 的 `preChange` 回调里对 `newOne *T` 递归处理。
- API：`config/env_override.go`，在 `yaml.Unmarshal` 之后对 `&c` 处理。
- STORAGE：同 API，`config/env_override.go`。
- 三份实现**故意不共享代码**（各仓库配置加载路径不同：SPIDER 走 config-util 泛型
  manager，API/STORAGE 是直接 `yaml.Unmarshal` 原始字节），但语法与语义保持一致
  （整段 `${VAR_NAME}`，反射递归 struct/slice/map/string）。
- 用法示例见 SPIDER `PRD/config-v2/README.md` §5、API/STORAGE 各自 `README.md`。

## 3. gitleaks 密钥扫描三件套

四仓库根目录都已加：

- `.gitleaks.toml`：`useDefault = true` + `[allowlist]` 白名单（`.example.*` 模板文件、
  已知安全的测试占位字符串、reCAPTCHA 公开 sitekey、逆向所得的第三方客户端签名算法常量等）。
  新增误报按同样方式加 `paths`（按文件路径）或 `regexes`（按提取出的 Secret 值，**不是**按整行
  Match——gitleaks allowlist 的 `regexes` 匹配的是 `Secret` 字段, 不含前后的 key 名/引号）。
- `.github/workflows/secrets.yml`：只扫 PR 的 diff（`base...head`），不扫全仓库历史（历史里的
  已知凭据是独立的轮换+清理排期，不适合每次 PR 反复报警）。
- `scripts/pre-commit-secrets.sh`：本机可选的 `pre-commit` 钩子（`git config core.hooksPath
  scripts/githooks` + 软链接），跑 `gitleaks protect --staged`；本机没装 gitleaks 时打印安装提示
  后 `exit 0`（不阻塞提交，CI 侧兜底）。

本机安装 gitleaks：`go install github.com/zricethezav/gitleaks/v8@latest`（注意 module path 是
`zricethezav/gitleaks`，`go install github.com/gitleaks/gitleaks/v8@latest` 会报 module path 冲突）。

**现状扫描方法**（排除 gitignore/未跟踪文件，只扫"如果现在提交会是什么样"）：
```bash
# 对每个仓库: 用 git ls-files + 未提交的新增文件构建一份快照目录, 再对快照跑 gitleaks --no-git
# (--no-git 直接跑 git status/HEAD 会连 gitignore 掉的本地文件一起扫, 需要自己拼快照排除)
```
2026-09-16 现状扫描结果（`feat/secrets` 分支，值不贴，仅计数）：SPIDER 19→2（剩 2 处是
CDN 边缘脚本与后端共享的 AES 签名密钥, 见 risks.md R7, 未处理）、API 11→6（剩 6 处都在
`config.yaml`, 按约定不改）、STORAGE 3→3（`config_dev.yaml`, 同上）、COMMON 2→0。
**同日验收返工后二次扫描**（按字段名 grep 之外，改成对每个已确认真实值做 `git grep -F`
逐一反查，四仓库排除 `config*.yaml`/`deploy.sh` 后合计 0 命中；`deploy.sh`/`config.yaml`/
`config_dev.yaml` 里的已知值不算新发现，按约定不动）。

### gitleaks 自定义规则失效（`[extend]` + `[[rules]]` 组合坑）

**现象**：`.gitleaks.toml` 里只要同时有 `[extend]`（`useDefault = true` 或 `path = "..."`
两种都一样）和自己写的 `[[rules]]`，那条自定义规则会被**静默吃掉**——不报错、`gitleaks
detect` 正常跑完、就是永远匹配不到，哪怕拿掉 `[extend]` 单独跑这条规则完全正常。
本机版本：`go install github.com/zricethezav/gitleaks/v8@latest` 装到的 v8.30.1。

**复现**：建一个只有一行 `ak=xxx&sk=yyy` 的 `.go` 文件 + 一份 `[[rules]] regex =
'''ak=...&sk=...'''` 的 `.gitleaks.toml`：不加 `[extend]` 能扫到，加了
`[extend]\nuseDefault = true`（或换成 `path` 指向手动导出的默认配置副本）就扫不到。看过
`config/config.go` 的 `Translate()`/`extend()` 源码，逻辑上不应该丢规则（`extend()` 只应该
**追加**默认规则集里我没有的 ID），没查出根因，怀疑是 viper 处理 `[[rules]]`（数组表）与
其他顶层 key 混排时的已知类问题，没有继续深挖（性价比不高）。

**结论**：**不要**在同时用 `[extend]` 的 `.gitleaks.toml` 里加 `[[rules]]` 期望它生效——
会造成"看起来配置了防护、实际没有"的假安全感，比不配置更危险。默认规则集认不出的模式
（比如 SPIDER 这次的 `ak=xxx&sk=yyy` 自定义 DSL），改成在 `scripts/pre-commit-secrets.sh`
里加一段独立于 gitleaks 的结构化 `grep -P`（对 `git diff --cached -U0` 的新增行做检查），
连带在 `.gitleaks.toml` 顶部写清楚"为什么这里没有对应的 `[[rules]]`"，避免后人重复踩坑。
升级 gitleaks 大版本后可以重新验证这个坑是否修复，修复了再把 grep 兜底换回 `[[rules]]`。

## 4. 一次性排查到的、有代表性的坑

- **文件名里带 `.hide.` 但其实想让它"能提交"** 会被 `*.hide.*` 一并忽略，见上面「文件名」提示。
- **注释里写"该文件已 gitignore"不代表现在还是**：`services/devops/devops_utils/
  devops_online_env.go` 的注释就是这样, 但 `chore: 历史遗留的被忽略源码纳入 git` 那次提交
  已经把它连同硬编码的真实 AK/SK/ES 密码一起提交进了 git 历史。改动前先
  `git log --oneline -- <file>` 确认真实状态, 不要信注释。
- **同一份真实凭据可能重复出现在多处**：本次发现同一对 OSS AK/SK 在 SPIDER 三个文件里
  重复硬编码（`devops_online_env.go`/`update_fc_loop.go`/`download2oss.go`）、同一个生产
  Redis 密码在 SPIDER 和 STORAGE 两个仓库里都有。grep 到一处后要在**全部四仓库**里搜同一
  个值/同一模式,不要以为改了一处就完了。
- **死代码里的硬编码也算数**：`storage-wt-secrets/services/save-worker/save-torrent.go` 的
  `onRedis` 函数开头就是 `return`（原作者自己注释"谁把redis hard code在这了"），但 return 之后
  的死代码仍把生产 Redis 密码明文提交进了 git——`go vet`/编译器都不会提示这种"死代码里的
  凭据"，只能靠 gitleaks 或人工通读发现。
- **按字段名/关键词 grep 会漏掉不常见的写法**：第一轮只 grep
  `AccessKeySecret|access_key_secret|BDUSS|refresh_token|password:|passwd|secret` 一类
  字段名，漏掉了 `fc_config_util.InvokerByConf("...&ak=<AK>&sk=<SK>")` 这种 query-string DSL
  （`ak=`/`sk=` 不匹配任何字段名模式）和 `esRun.mjs` 里 `const password = 'xxx'`（JS 变量声明,
  之前的 grep 命令行只覆盖了 `.go`/`.yaml`/`.sh`/`.json`, 没覆盖 `.mjs`）。验收返工时改成按
  **已确认的敏感值**（不是字段名）逐个 `git grep -F` 反查全仓库才补全；同一份 AK/SK 最终
  在 SPIDER 一共重复硬编码了 **6 处**（`devops_online_env.go`/`update_fc_loop.go`/
  `download2oss.go`/`web_res/download_url.go`/`download_worker/download_mgr.go` 生产代码
  各一处 + `download_fc_test.go`/`bing_pdf_test.go` 测试各一处，`deploy.sh` 里还有第 7 处但
  那是它的合法来源、不算硬编码问题）。教训：**排查完字段名之后一定要再按"已确认的具体
  值"补一轮 `git grep -F`**，两种搜法覆盖的是不同的写法习惯，互相不能替代。
