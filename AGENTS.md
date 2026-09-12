# 关于

风控技术部项目: 爬取网络上网盘资源, 为后续版权侵犯追责提供证据
必须**严格按照**下文 agent-memory「§9 自主进化循环」工作。

## repos
> 1S_ROOT: `/home/peterq/dev/projects/1s`

- MEMORY: `/home/peterq/dev/projects/peterq/agent-memory-osec-spider` 用于管理 Agent 记忆和工作流的目录, 由 Agent 自主维护
  - `ls .` => `agent-memory  AGENTS.md  agent-tasks  CLAUDE.md  scripts`
- COMMON: `1S_ROOT/enfi-resource-common` 跨仓库共用工具类, rpc定义等.
- STORAGE:  `1S_ROOT/enfi-resource-storage` 存储服务, 主要负责爬取的资源的入库
- API: `1S_ROOT/osec-resource-api` 给前端和其他部门提供资源查询接口服务
- SPIDER: `1S_ROOT/osec-spider-go` 爬虫服务, 主要负责爬取网络资源, 调用 STORAGE 入库, 并将爬取的资源信息写入 ES, 供 API 查询
- NC-JS: `1S_ROOT/nc-js` 前端mono repo
  - NC-JS/admin/* : 系统后台 由qiankun微前端框架管理的多子应用, 主要用于管理爬虫和资源


## Rules
禁止在 git message 中添加类似 Co-Authored-By 的信息, 会被远程仓库拒绝.
禁止使用 harness memory, 仅使用 agent-memory 进行跨会话记忆和复用
向用户展示的信息使用 **中文**
Agent Memory使用 **中文**
代码注释使用 **中文**
为完成任务所用的脚本, 有价值的写入到项目中, 并记录文档, 以便开发者或其他 Agent 复用. 调用时通过项目中的路径调用以节省输出 token

## 下面是一份技能定义，适用于 AI Agent. 务必 **严格按照** `## 15. 自主进化循环` 工作流进行工作

# 技能:agent-memory(可持续进化记忆系统)

通过 `agent-memory/` 目录用 Markdown 管理项目知识、会话经验、决策和可复用流程。Agent 对该目录有完整的创建/读取/更新/整理/归档/重构权限。
思考模式下 thinking 只写主要思路和核心要点,不与正文重复,避免浪费 token。

## 1. 目标
跨会话积累并复用:项目基础信息、当前目标与进展、用户偏好、已确认事实、决策及原因、可复用流程、有效经验、失败方法及原因、待办/风险/未解决问题。

要求:新会话能快速恢复上下文;总览精炼省 token;详细知识按需加载;全部为 Markdown 且带创建/更新时间;目录由 Agent 自主维护;区分事实/推断/偏好/决策/临时信息;过时内容必须更新、标记或归档;持续提炼高价值经验并更新总览和索引。

## 2. 目录约定
```text
agent-memory/
├── 00-overview.md          # 必加载:总览与当前状态
├── 01-index.md             # 必加载:启动包快照, 由 scripts/mem/mem.py index --write 生成, 禁止手改
├── 02-user-preferences.md  # 用户偏好
├── 03-project-context.md   # 项目背景、目标、边界、基础事实
├── current/    goals.md tasks.md risks.md open-questions.md
├── knowledge/  domain-*.md architecture-*.md api-*.md concept-*.md
├── decisions/  decision-*.md rejected-*.md
├── procedures/ workflow-*.md troubleshooting-*.md checklist-*.md
├── lessons/    success-*.md failure-*.md patterns-*.md
├── sessions/YYYY/YYYY-MM-DD-*.md   # 会话摘要
└── archive/YYYY/*.md               # 已归档
```
原则:结构可按项目规模调整;不为形式建空目录;文件少可合并,文件过大按主题拆分;文件名用中文/小写英文/数字/连字符;一文一主题;只用 Markdown;无长期价值的草稿不入库。

## 3. 文件元数据
每个 `.md` 开头必须有 Front Matter:
```yaml
---
title:
type: overview | index | context | preference | task | risk | question | knowledge | decision | procedure | lesson | session | archive
status: active | draft | deprecated | archived
created_at: 2026-08-24T10:30:00+08:00   # 创建后不得修改
updated_at: 2026-08-24T10:30:00+08:00   # 每次改动必须更新
priority: critical | high | medium | low
keywords: [关键词]                       # 用于检索与按需加载, 含英文标识符; 启动包只展示前 3 个, 最重要的放前面
questions: [这个文件能回答的问题]         # 可选, 3~6 条自然语言问句, 进入启动包与检索; 替代旧索引里的"问题→文件"路由
summary: 一句话概括,不读正文即可判断是否加载
load: always | on-demand | rarely        # always 仅限启动必读文件; sessions 一律 rarely
valid_until: 2026-10-01                  # 可选, 限流/配额/第三方接口类结论的保质期, lint 到期提醒
related:
  - agent-memory/xxx.md  # 文件名不足以说明关联时加注释
---
```
时间用 ISO 8601 含时区,默认 Asia/Shanghai。

## 4. 必须维护的核心文件

### 4.1 `00-overview.md`(priority critical, load always)
每次新会话首先加载。**硬上限 5,500 字符**(`python3 -c "print(len(open(p).read()))"` 口径, `mem.py lint` 判据);只放后续工作最需要的信息,不复制详细知识。
§2 当前状态只留最近 7 天 ≤5 条、每条 ≤2 行并指向精确文件;历史进 `current/changelog.md`。§5/§6 只写「一句话 → 文件路径」各 ≤10 条。
章节:
1. 项目身份:名称/类型/目标/当前阶段/边界/主要交付物
2. 当前状态:正在处理/已完成/进行中/下一步/阻塞/最近重要变化
3. 核心事实(仅已确认且直接影响后续工作的)
4. 用户与协作偏好:输出语言/风格/技术偏好/禁止做法/验收标准 → 详见 `02-user-preferences.md`
5. 当前关键决策:决策/原因/影响 → 详见 `decisions/`
6. 高价值经验 → 详见 `lessons/` `procedures/`
7. 待解决问题 → 详见 `current/open-questions.md`
8. 找文件方法(≤6 行):`scripts/mem/mem.py boot` → `search <问题>` → `outline <file>` → `body <file> --section <标题>`;不再维护手工导航表

### 4.2 `01-index.md`(priority critical, load always, **脚本生成物**)
= `scripts/mem/mem.py index --write` 的输出:每个文件一行「路径 | 优先级 | 更新 | summary | 前 3 个关键词」+ 可选的 `questions` 行, sessions 只列最近 3 个。
**禁止手工编辑**。索引的唯一维护方式是改目标文件的 Front Matter(summary / keywords / questions),再运行 `scripts/mem/mem.py index --write`。
「最近更新」不再维护, 需要时 `mem.py recent --days 7` 看 git 历史。工具说明见 `scripts/mem/README.md`。

## 5. 新会话启动协议
1. 检查 `agent-memory/`:不存在则创建最小文件集(`00-overview.md` `01-index.md` `02-user-preferences.md` `03-project-context.md`);存在则补齐缺失核心文件。
2. 读取 `00-overview.md`。
3. 读取启动包:Claude Code 下 SessionStart hook 已自动注入 `mem.py boot` 输出(看到「agent-memory 启动包」即不必再读);否则读 `01-index.md`(等价快照)。
4. 从用户请求提取关键词:项目/功能/技术栈/任务类型/领域术语/实体/约束/错误信息/用户提及的历史事项。
5. 先在启动包里按 summary/关键词/questions 选文件(评测:LLM 读紧凑目录 Hit@1 90%, 强于算法检索);拿不准或要找 sessions 时 `scripts/mem/mem.py search <自然语言问题>`。
   定位到文件后**先 `mem.py outline <file>` 看章节, 再 `mem.py body <file> --section <标题>` 只读需要的一段**;整文件读取仅限 ≤3,000 字符的文件。
   优先级:当前任务目标 > 项目背景 > 用户偏好 > 决策 > 流程 > 成功/失败经验 > 领域知识。不因文件存在就全读。
6. 内部整理工作上下文:已知事实/当前目标/适用约束/相关决策/可复用流程/潜在风险/需确认问题。

记忆与用户当前指令冲突时,以当前指令为准并记录该变化。

## 6. 会话结束与持续学习
**应写入**(满足任一):用户明确偏好;新的基础事实;重要技术/产品决策;可复用方案;明确的失败原因;任务/目标/风险变化;可复用流程;用户纠正了 Agent;某方法被验证有效或无效;后续很可能再用;多轮交互才确定的有复用价值信息。

**不写入**:无长期价值闲聊;可从代码/现有文件直接推导的临时信息;未标记的猜测;重复内容;一次性中间过程;敏感信息(除非用户明确要求且环境允许)。

**会话摘要**:有长期价值的会话创建 `sessions/YYYY/YYYY-MM-DD-主题.md`(type session, priority medium, load on-demand),章节:完成事项/关键发现/新增或改变的事实/做出的决策/遇到的问题/后续行动/值得沉淀的经验。
摘要不是最终知识库,长期有效内容须进一步提炼到项目上下文、决策、流程、成功/失败经验、当前任务或风险文件。
sessions 一律 `load: rarely`, 启动包不列、检索降权;只在用户点名某次会话或提炼后的文件确实没有时才读。会话中沉淀的长期知识**必须**在会话结束时提炼进 knowledge/procedures/lessons/decisions, 不能只留在 session 里(评测发现索引指向 session 的主题是找不准的主因之一)。

## 7. 经验、决策与可信度

### 经验提炼
不只记录"发生了什么",要回答:要解决什么问题?试了哪些方法?哪种有效、为何?哪种无效、为何?下次优先做什么?适用前提与边界?
- `lessons/success-*.md`(priority medium)章节:问题/适用条件/推荐做法/原因/示例/注意事项/可迁移范围
- `lessons/failure-*.md`(priority high)章节:问题背景/失败方法/失败表现/根本原因/规避方法/下次行动建议/适用边界

### 决策记录
重要决策必须单独记录于 `decisions/decision-YYYY-MM-DD-名称.md`(priority high),章节:背景/要解决的问题/备选方案(各列优缺点)/最终决策/决策原因/影响/复盘条件/当前状态。
决策被推翻时:保留原文件,`status: deprecated`,记录替代决策路径,更新总览和索引中的有效决策。

### 可信度标签
`[事实]` 已确认 · `[用户确认]` 用户明确说明 · `[推断]` 推导结论 · `[待确认]` 未验证 · `[临时]` 仅当前任务有效 · `[已废弃]` 不再适用。
不要把推测写成事实。

## 8. 更新、Token 控制与整理

### 修改文件时
保留 `created_at`;更新 `updated_at`;核对 `summary`/`keywords`/`related`;过时则标记状态;影响总览或索引时同步更新。

### 总览只放
当前阶段/目标/任务、关键事实、重要约束、有效决策、最近重要变化、最值得复用的经验、关键文件导航。不放完整文档、长会话记录、历史细节、失效方案、无关知识。

### 索引更新时机
任何 Front Matter 变化或文件增删改名后运行 `scripts/mem/mem.py index --write`;`mem.py lint` 会报「索引过期」。

### 加载层级
- 第一层始终:`00-overview.md`(≤5,500) + 启动包(hook 注入或 `01-index.md`, 提示线 17,000、硬上限 20,000;超提示线时精简 summary/questions 或归档低价值文件), 合计目标 ≤ 22,500 字符
- 第二层按任务:`03-project-context.md` `02-user-preferences.md` `current/` 相关决策与流程 —— 用 `outline` + `body --section` 按章节读
- 第三层仅确需时:历史会话、详细领域知识、失败经验、归档内容、弱相关资料

### 长度(均为字符数, `mem.py lint` 判据)
总览 ≤5,500;`03-project-context.md` ≤4,000;会话摘要 ≤4,000;`archive/` 与 `status: archived` 的文件不限长度(永不整读, 只按章节取)。
其余文件(含 `current/tasks.md`)采用**双阈值**:硬上限 12,000, 超过即 lint「超长」, **必须一次压缩/拆分/归档到 <6,000**(留足增长空间, 禁止只压到刚好低于上限, 否则下次改动又超);9,000~12,000 之间 lint 只打「提示」不阻塞, 顺手压缩即可。压缩手段:任务「完成且已部署」即整块移入 `archive/YYYY/tasks-YYYY-MM-已完成.md`;已上线/已验证的过程细节移到 rollout/决策/lessons 只留一句话指针;多主题文件按主题拆分。
避免重复:总览写摘要,索引写关键词与概要,会话只写过程摘要,决策只写决策与依据;详细内容放唯一文件,其他文件链接引用。

### 整理与归档(定期主动执行)
- 合并:内容高度重复 → 合为一个主题文件,保留更完整准确的内容,旧文件记录替代文件,更新索引与引用。
- 拆分:多主题或过长 → 按主题拆分,补齐元数据,更新总览索引,删除或归档原文件。
- 归档到 `archive/YYYY/`:已完成不再用的任务、被替代的决策、过时会话摘要、失效临时信息、与当前阶段无关的历史资料。归档前:`status: archived`,保留 `created_at`,更新 `updated_at`,原位或索引留替代路径,确认不破坏引用。
- 删除仅限:完全重复、明显错误且无历史价值、误操作产生、用户明确要求。过时但有复盘价值的应归档而非删除。

### 冲突处理
优先级:用户当前指令 > 最近用户确认 > 有效决策文件 > 更新较新的项目上下文 > 历史会话摘要 > 未确认推断/临时记录。
发现冲突:不静默覆盖;记录冲突及来源;以高优先级为准;更新相关状态;必要时新建决策;总览保留当前有效结论。

### 敏感信息
不保存密码、API Key、私钥、令牌、身份证/银行卡、未授权隐私、不必要的敏感业务数据。必须记录时只存脱敏信息、变量名、配置位置、使用方式和安全注意事项,例如:"API Key 存于环境变量 `PROJECT_API_KEY`,不写入仓库或记忆文件"。

## 9. 自主进化循环(必须严格执行)
```text
读取总览 → 读启动包 → 识别任务关键词 → 选文件, 按章节加载 → 执行任务
→ 识别新事实/决策/经验 → 更新详细记忆文件(含 Front Matter 的 summary/keywords/questions)
→ 提炼高价值内容到总览(≤5,500 字符) → 归档过时内容
→ scripts/mem/mem.py index --write → scripts/mem/mem.py lint 通过
```
每次任务完成后至少检查:新项目事实?新用户偏好?重要决策?可复用方法?验证了某方法无效?任务或风险变化?需更新 `00-overview.md`?Front Matter 是否反映新内容?然后 `index --write` + `lint`, lint 有「超长/常驻超长/索引过期/悬空引用」未清零视为任务未完成(「提示」不阻塞)。

## 10. 最低执行要求
- 新会话:读 `00-overview.md`;看启动包(hook 注入或 `01-index.md`);至少按章节加载一个最相关详细文件(若存在)。
- 任务后:判断是否产生长期信息;有则更新/创建 `.md`;更新 `updated_at` 与 Front Matter;`scripts/mem/mem.py index --write`;`scripts/mem/mem.py lint`。
- 禁止:忽略总览从零开始;一次性加载全部历史;整文件读取 >3,000 字符的文件而不先 `outline`;手工编辑 `01-index.md`;创建无元数据文件;修改 `created_at`;把推测记为事实;索引指向不存在的文件;只记过程不提炼经验;总览无限膨胀;把长期知识只留在 sessions。