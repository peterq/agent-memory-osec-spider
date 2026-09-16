# 角色 20：前端——文档提交弹窗识别腾讯文档链接

工作树：`/home/peterq/dev/projects/1s/ncjs-wt-qqdoc`（分支 `feat/qqdoc`）。先读 `00-shared.md`（尤其 §5 第 2 条：**绝不 `pnpm build`**）。

## 改动范围（只这两个文件，别扩散）
1. `admin/spiderAdmin/src/scheduler/spiderUtil.ts`
   - `DocType` 联合类型增加 `'qqSheet'`；`docTypeNames` 增加 `qqSheet: '腾讯文档'`。
   - 新增正则 `/docs\.qq\.com\/sheet\/([a-zA-Z\d]{10,40})/g`，加入 `parseDocLinkFromText` 的映射表。产出 url 形如 `https://docs.qq.com/sheet/<id>`（不带 `?tab=`，同一文档不同 tab 只算一个任务；云端脚本会遍历全部 sheet）。
   - 看一眼 `docTypeCount` 等依赖 `DocType` 的地方是否需要同步（例如用 `Record<DocType, number>` 初始化的对象）。
2. `admin/spiderAdmin/src/pages/doc/comps/sumbitModal.vue`
   - 缺省示例文本改为两行：金山示例 + `https://docs.qq.com/sheet/DR1paWVp2cWxmc3NW`。
   - 如有 placeholder/提示文案提到"金山文档"，改成"金山文档 / 腾讯文档（表格）"。

## 验证（前台执行，都要贴输出）
```bash
cd /home/peterq/dev/projects/1s/ncjs-wt-qqdoc/admin/spiderAdmin
pnpm type-check          # 或 package.json 里 type-check 对应脚本名
pnpm test:unit -- --run  # 若 spiderUtil 有测试, 顺手加一条: 一段混合文本能同时识别 kdocs 与 docs.qq.com(带 ?tab=) 且 url 不含 query
```
不要 `pnpm build`、不要 `pnpm dev` 长驻。

## 交付
`git commit -- admin/spiderAdmin/src/scheduler/spiderUtil.ts admin/spiderAdmin/src/pages/doc/comps/sumbitModal.vue <测试文件>`（不 push）。汇报文件清单、commit 哈希、命令输出摘要。
