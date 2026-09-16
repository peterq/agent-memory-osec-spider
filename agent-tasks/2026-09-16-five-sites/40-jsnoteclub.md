# 站点：jsnoteclub.com（灵犀笔记）—— 短名 `jsnoteclub`，子命令 `bbs_jsnoteclub`

worktree：`/home/peterq/dev/projects/1s/spider-wt-site-jsnoteclub`（分支 `feat/site-jsnoteclub`）。样板：`services/bbs/kuakes.com.go`（文章型站）+ `fuxipan.com.go`（sitemap 枚举）。

## 报告已知（不要重测）

- Ghost CMS 博客；sitemap 结构 `sitemap.xml → sitemap-{pages,posts,authors,tags}.xml`；`sitemap-posts.xml` 1448 篇，按分类目录（`/dongman/`、`/meihanju/`、`/aaa/` …）。
- **每篇文章正文平均直出约 5 条明文链接（含提取码）**，推算 7000+ 条；quark 68%；59 条抽样有效率 96.15%；纯 HTML、免登录、无 JS 依赖。
- 另有一篇**持续追加的汇总页** `/yunpan/`（271 条，"本页会持续分享资源"），是增量的重要来源。
- 近 7 天 15 篇新文章；`sitemap-posts.xml` 的 `lastmod` 可用作增量水位线（报告未验证逐条可信度，**实测并写进 PRD**）。

## 策略要求

- 全量：`sitemap-posts.xml` 全部文章 + `/yunpan/`，每篇解析正文全部链接 + 提取码（提取码解析规则写进 PRD，按样板的 `pwd` 字段提交），`FullSweepGate=true`。
- 增量：`sitemap-posts.xml` 按 `lastmod` 水位线取新/改文章；`/yunpan/` 每轮重抓，用 `Engine.SeenChanged` 按内容变化判断。
- 联网测试：抽 10 篇文章 + `/yunpan/`，断言每篇 ≥1 条链接、提取码解析、去重、二轮 0 提交。
