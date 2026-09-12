# 任务 10：检索方案对比（先读 00-shared.md）

## 目标
量化 `mem.py search` 不同配置的检索质量与耗时，给出最佳默认配置。

## 做法
1. 写 `ROOT/scripts/mem/bench/search_bench.py`：读取 gold.jsonl（和存在时的 gold_paraphrased.jsonl，字段同名 `queries`），对每个 query 调用检索逻辑（直接 import `mem.py` 里的 `load_all/lexical_scores/semantic_index/semantic_scores` 等函数，不要 subprocess 逐条跑），排除 `load: always` 文件，计算 **Hit@1 / Hit@3 / Hit@5 / MRR**（命中 = 结果在 expected 里任意一个），并记录每 query 平均耗时。
2. 对比至少这些配置：
   - lexical-bigram（临时禁用 jieba）、lexical-jieba
   - semantic-only：`BAAI/bge-small-zh-v1.5`、`BAAI/bge-m3`（大约 2GB，磁盘够，可装）、`jinaai/jina-embeddings-v2-base-zh`
   - hybrid（当前默认）以及 RRF 参数扫描：语义权重 {1.0,1.3,1.6,2.0}、K {10,30,60}、`min_sim` {0.3,0.35,0.45}
   - 切块大小 CHUNK_CHARS {300,600,1200}
   - 是否启用文档 boost（sessions 降权 / 巨型文件降权）
   需要的话给 `mem.py` 的相关函数加参数，默认值保持不变。
3. 分别在原始问法与改写问法上报告；如果改写文件此时还不存在，先跑原始问法，最后再检查一次目录，有就补跑。
4. 列出错得最多的 5 个 topic，分析是 gold 期望不合理、还是文件 Front Matter（keywords/summary）写得差，给出对文件元数据的改进建议（不要动文件）。

## 交付
`results-10.md`：配置对比表、最佳配置建议（含是否值得换大模型的耗时/收益权衡）、失败案例分析。
