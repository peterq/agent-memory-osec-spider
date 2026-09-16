# 角色 20 追加任务：与 main 上新合入的飞书识别合并

背景：你开发期间 nc-js `main` 合入 `39c145a`（提交文档链接支持飞书），与你的 `cc0bed1` 在 `spiderUtil.ts` / `spiderUtil.test.ts` / `sumbitModal.vue` 三处冲突。

工作树仍是 `/home/peterq/dev/projects/1s/ncjs-wt-qqdoc`（分支 `feat/qqdoc`）。禁忌不变：不 push、**不 `pnpm build`**、不碰主工作树。

## 要做的事
1. `git merge main`，三个文件都按"两边都保留"解决：
   - `DocType = 'kingSoft' | 'feishu' | 'qqSheet'`；`kingSoftReg`、`feishuReg`、`qqSheetReg` 三个正则都在；`docTypeNames` 三项（金山文档 / 飞书文档 / 腾讯文档）；`parseDocLinkFromText` 映射表三项。注释保留两边。
   - `sumbitModal.vue` 缺省示例：金山 + 飞书（main 上的示例）+ 腾讯三行。
   - `spiderUtil.test.ts`：两边新增的用例都保留；若飞书用例与腾讯用例断言的是同一段混合文本，合成一个用例同时断言三类。
2. `pnpm type-check` 与 `npx vitest run`（不要用 `pnpm test:unit -- --run`，会进 watch）全过，贴输出。
3. 提交 merge（中文信息），不 push。汇报 commit 哈希与冲突处理方式。
