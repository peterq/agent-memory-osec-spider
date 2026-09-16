# 角色 90：验收——腾讯文档表格解析

先读 `00-shared.md`。验收对象：`/home/peterq/dev/projects/peterq/userscripts-wt-qqdoc`（`feat/qqdoc-cloud`）与 `/home/peterq/dev/projects/1s/ncjs-wt-qqdoc`（`feat/qqdoc`）。只读代码 + 跑测试，**不改代码**（发现问题写清位置与复现，交给主控）。

## 清单
1. 金山无回归：`git diff master -- src/cloud/kdocCloud.ts` 逐行看，nonce/SSO/emit/emitTerminal/watchdog/心跳/copySheet/分批 result 是否语义等价；`DOC_HOSTS` 扩展后 `account.kdocs.cn` 仍只存 nonce 不解析。
2. 协议合规（05-doc-fc-contract.md §3）：腾讯路径 start→progress→result(seq/final)/error(permanent) 字段齐全；单条 ≤200KB 分批仍生效；任何异常路径都有终态且只发一次。
3. 分块循环：越界退回第一块时终止；`max_row` 为 0/缺失时不死循环；每次 fetch 有超时；总 watchdog 有效。
4. 解析正确性：独立用 `agent-tasks/2026-09-16-qqdoc-sheet/ref/qqextract.py fixtures/*.js` 的结果（968/64/21）对照单测断言；`pnpm test -- --run` 全绿；`pnpm build:cloud` 成功且产物无外链、含 docs.qq.com match。
5. 纯逻辑模块不引用 window/document；验证脚本 `scripts/qqdoc-verify.ts` 对两个示例链接能跑出与夹具一致的数量级。
6. 前端：type-check 通过；`parseDocLinkFromText` 对 `https://docs.qq.com/sheet/DR1paWVp2cWxmc3NW?tab=BB08J2` 产出 `https://docs.qq.com/sheet/DR1paWVp2cWxmc3NW`；金山识别不变。
7. 两个工作树 `git status` 干净、提交信息中文、无 Co-Authored-By、未 push。

## 交付
按清单逐条给「通过/不通过 + 证据（命令与关键输出）」；不通过项写明文件:行号与建议修法。
