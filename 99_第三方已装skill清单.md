# 第三方已装 Skill 清单（非本人生成，仅供对照）

> 这些是从 ClawHub / 开源社区**下载安装**的现成 Skill，不是本人自建，因此没有复制源文件到 `skills源文件/`。
> 本人自建的 14 个见 `00_我生成的skill汇总.md`。
> 统计时间：2026-09-06，共 37 个第三方 Skill。

## 1. 科研论文全栈（Scientific Agent Skills，2026-09-06 集中安装）

| Skill | 用途 |
|---|---|
| `scientific-brainstorming` | 科研选题发散、对抗式评审、方向优先级排序 |
| `hypothesis-generation` | 把观察转成可检验假设、对立解释、预注册分析计划 |
| `literature-review` | 多数据库系统文献综述，出 markdown/PDF |
| `paper-lookup` | 11 个学术库（PubMed/arXiv/OpenAlex/Crossref/S2 等）检索、DOI、找开放全文 |
| `citation-management` | 文献元数据提取、DOI 转 BibTeX、引用真实性校验 |
| `experimental-design` | 随机化、正交/因子/响应面实验设计（DOE） |
| `statistical-analysis` | 引导式统计检验、假设诊断、效应量、功效分析、APA 报告 |
| `statsmodels` | OLS/GLM/混合模型/时间序列等统计模型库 |
| `scikit-learn` | 机器学习：分类/回归/聚类/调参/流水线 |
| `pytorch-lightning` | PyTorch 深度学习框架（Lightning 封装） |
| `uncertainty-and-units` | 单位量纲、GUM 不确定度传播、结果合理性核查 |
| `matplotlib` | 底层绘图库精细控制 |
| `scientific-visualization` | 出版级科研图表、多面板、误差棒、配色审查 |
| `scientific-writing` | 论文起草/修订/审计、论断溯源、稿件 lint |
| `scientific-slides` | 科研汇报/答辩 PPT、Beamer |
| `what-if-oracle` | 4-6 分支情景推演、决策压力测试 |
| `academic-research-hub` | 另一套学术搜索/下载/引用工具（依赖 OpenClawCLI） |
| `mineru-pdf-extractor` | PDF→Markdown，支持公式/表格/OCR（自建库读中文文献也用它） |
| `exa-search` | Exa 科技/学术向网络搜索 |
| `docx` | Word 文档创建/编辑、目录页码、套模板 |

## 2. 深度研究 / 信息检索

| Skill | 用途 |
|---|---|
| `deep-research` | 通用深度研究流程 |
| `storm-research` | STORM 式预研究（主题/趋势/文章拆解） |
| `jina-reader` | Jina Reader：URL 转 markdown、搜索、精读 |
| `volcengine-web-search` | 火山引擎联网搜索脚本 |

## 3. 学习方法 / 思维 / 编程辅导

| Skill | 用途 |
|---|---|
| `anki-connect` | 通过 AnkiConnect API 制作/更新 Anki 记忆卡片 |
| `first-principles` | 第一性原理拆解、质疑"惯例做法" |
| `code-mentor` | 编程教学、代码 review、debug、算法练习、项目辅导 |
| `goal-clarification` | 执行前的结构化目标澄清讨论 |

## 4. OpenClaw 系统运维 / 会话与提效

| Skill | 用途 |
|---|---|
| `reprompter` | 手动打磨提示词，模糊请求反问澄清 |
| `archify` | 生成架构图/流程图/时序图/数据流图 |
| `context-slimmer` | 精简常驻上下文文件（AGENTS/TOOLS/USER/MEMORY 等） |
| `openclaw-session-guard` | 长会话防爆：80% 自动归档、轮换新会话、低 token 交接 |
| `session-health-monitor` | 上下文窗口健康监控、阈值告警、压缩前快照 |
| `smart-cron` | 自然语言创建定时任务 |
| `token-manager` | 多厂商 token 用量监控与省钱建议 |
| `verification-before-completion` | 宣称"完成"前强制可运行验证 |
| `openmaic` | OpenMAIC 多智能体互动课堂（Live Demo/本地部署/二开） |

## 说明
- 科研全栈这套偏**英文学术体系**，不覆盖知网/万方/维普，中文文献需自己从校园网下载后用 `mineru-pdf-extractor` 解析。
- 这些第三方 Skill 与本人自建 Skill 的配合方法，见 `00_我生成的skill汇总.md` 第五节及"论文全流程"相关说明。
