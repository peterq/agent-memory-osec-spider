# 角色 90：验收（每条分支一个验收 Agent，只报告不改代码）

先读 `00-shared.md`，再读被验收角色的简报，按其「目标/设计/文件所有权/验证/交付」逐项核对，每项给「通过 / 不通过 + 证据（文件:行 或命令输出）」。

## 一票否决项
- 提交里出现任何明文凭据（AK/SK/口令/token/BDUSS）或 `Co-Authored-By`/邮箱。
- 改了「文件所有权」之外的文件（列出来）。
- 主检出（非 worktree）被改动；有 push；改了 `config*.yaml`/`.vscode`。
- 触碰生产（ssh/deploy/线上写操作）。
- 删除/判失效路径：未知响应被判成失效；熔断 redis 故障时非 fail-open（`delete-breaker`/`valid-unify` 专项）。
- 旁路初始化失败会 panic/Fatal。

## 通用核对
- 在该 worktree 实跑：`go build ./...`；对角色声明的包 `go vet` + `go test`；结果原样贴。
- `git diff master --stat` 与汇报的文件清单一致；`git log master..HEAD` 提交信息合规。
- 依赖 COMMON 分支的角色：SPIDER/API worktree 的 `go.mod` replace 改动**未被提交**（`git diff master -- go.mod` 应为空）。
- README/文档中文、无值泄露。

## 汇总
通过项数 / 不通过项（按严重度）/ 建议返工内容 / 主控合并时需注意的冲突点（与其他角色重叠的文件）。
