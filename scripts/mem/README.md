# scripts/mem —— agent-memory 加载 / 检索 / 体检工具

Python 3.10+；核心功能零依赖，装上 `requirements.txt`（jieba + fastembed）后检索变成「jieba 分词 BM25 + bge-small-zh 语义」融合。
所有子命令只读，不会修改任何记忆文件（只写自己的缓存 `scripts/mem/.cache/`，已 gitignore）。
目的：把「通读 01-index.md / 00-overview.md 再翻正文」改成「启动包 → 检索 → 看结构 → 只读需要的章节」，
把新会话恢复上下文的 token 从 4 万量级压到 1 万以内。

```bash
scripts/mem/mem.py boot                  # 启动包: 路径|优先级|更新|summary|前 3 个关键词 + questions 行(仅 critical/high 文件, 最多 3 条; sessions 只列最近 3 个)
scripts/mem/mem.py index --write         # 把启动包写成 agent-memory/01-index.md (索引是生成物, 禁止手改)
scripts/mem/mem.py search 网关重启前要检查什么 -q   # 混合检索, 支持自然语言问句; 默认排除常驻文件
scripts/mem/mem.py search xx --dir lessons,decisions -k 5 --no-snippets --mode lexical   # 纯词法, 不加载模型更快
scripts/mem/mem.py embed                 # 预热/刷新 embedding 缓存(search 也会按文件哈希自动增量刷新)
scripts/mem/mem.py outline <file>...     # 章节结构: 起止行/字数, 决定读哪一段
scripts/mem/mem.py body <file>           # 只输出正文(剥离 Front Matter)
scripts/mem/mem.py body <file> --section 实测数据   # 只输出某章节(标题子串匹配)
scripts/mem/mem.py body <file> --lines 120:160     # 按行区间
scripts/mem/mem.py lint                  # 体检: 元数据缺失/超长/常驻超长/悬空引用/updated_at 落后于 git/valid_until 过期/索引过期
scripts/mem/mem.py lint --max-chars 12000 --target-chars 6000 --warn-chars 9000 --index-warn 17000 --index-max 20000   # 长度双阈值的缺省值, 见下文
scripts/mem/mem.py stat                  # 各目录字数、load=always 体积、最大文件
scripts/mem/mem.py dup                   # 跨文件逐行重复检测(只能抓原样复制, 抓不到改写复述)
scripts/mem/mem.py recent --days 7       # 用 git 历史代替手工"最近更新"
```

文件参数可以写 `agent-memory/xxx.md`、`xxx.md`（相对 agent-memory）或绝对路径。

## 与 AGENTS.md 协议的关系

- Claude Code 的 `SessionStart` hook（`.claude/settings.json`）在每个新会话自动注入 `boot` 输出；其他 Agent 读 `01-index.md`（同一内容的快照）。
- 会话结束固定动作：改 Front Matter → `index --write` → `lint` 清零。

## 设计要点

- **Front Matter 就是索引**：`boot` 完全由各文件的 `summary/keywords/priority/updated_at` 生成，
  维护好 Front Matter 就不用再手工维护索引表。
- **检索 = 词法 + 语义 RRF 融合**：词法是 jieba 搜索模式分词（未装则字二元切分）+ BM25 变体，字段加权
  `title=keywords=questions(6) > summary(4) > headings(3) > body(1)`；语义用 `jinaai/jina-embeddings-v2-base-zh`（09-12 基准评测优于 bge-small-zh 与 bge-m3，见 `bench/`）
  （fastembed/ONNX，CPU 即可，模型约 640MB 存 `~/.cache/fastembed`），按「摘要块 + 章节块（≤600 字）」
  切块后取每文件最高相似块，结果里 `语义0.71@章节名` 直接告诉你该读哪一节。
  文档 boost：sessions ×0.7、archived/deprecated ×0.5、>2 万字巨型文件 ×0.8（避免 tasks.md 什么都沾边）。
- **回归基线（2026-09-12）**：7 组自然语言问句 Top1 全部命中预期文件，见决策文件。
- **性能**：全量建缓存 101 文件 / 1881 块约 40 秒（一次性），之后每次查询约 1 秒；缓存按文件内容哈希增量刷新。
- **lint 长度检查是双阈值**（2026-09-13 起）：>12,000 字才报「超长」并计入问题，触发后必须一次压到 <6,000；9,000~12,000 只打「提示」不计入问题。
  原因：单阈值 8,000 时每次只压到 7,9xx，下一次改动又超，lint 反复报警；把触发线和目标线拉开 6k 才有喘息空间。
  总览 5,500 硬上限不变；`01-index.md` 随文件数线性增长，同样双阈值：17,000 提示、20,000 硬上限（`--index-warn/--index-max`）。
- **lint 的 git 对比只看修改型提交**（`--diff-filter=M`），避免整目录迁移把所有文件判成落后。
- 悬空引用只检查记忆目录内路径；指向其他仓库（`PRD/…`、`site-discovery/…`）的不管。

## 可选后续

- 文件数破千或中文长句召回不佳时，可把 `EMBED_MODEL` 换成 `BAAI/bge-m3`（更大更准，fastembed 已支持）。
- Claude Code `SessionStart` hook 自动把 `boot` 输出注入上下文（`.claude/settings.json`），
  非 Claude Code 的 Agent 仍按 AGENTS.md 手动执行。

## bench/ —— 评测基准与脚本

- `gold.jsonl`：41 主题的「问法 → 期望文件」，抽自 01-index.md 关键词路由；`gold_paraphrased.jsonl`：每主题 3 条无泄露改写问法；`*_questions.jsonl` 为去答案版本，给被评测 Agent 用。
- `search_bench.py`：对比检索配置（模型/切块/RRF 参数/boost），输出 Hit@k 与 MRR。
- `score_routing.py`：给「Agent 只看某份启动上下文选文件」实验打分。
- 结果与结论：`agent-tasks/2026-09-12-memory-optimization-bench/results-*.md`（`results-summary.md` 为汇总）。

## load: rarely 的文件不进启动包（2026-09-18）

`boot`/`index` 对 `load: rarely` 的文件只计数不列条目（sessions 之外的目录同样适用），`search` 仍能检索到。用途：窄主题、一次性的 lessons/decisions 标成 rarely，把启动包压回 17,000 提示线以下，而不用归档。
