---
name: "resume-builder"
description: >-
  一站式求职自动化工具集：多渠道职位搜索（BOSS直聘/中南大学就业网/实习僧）+ AI匹配打分 +
  基于Obsidian知识库的定制简历生成（Drafter-Reviewer双Agent循环 + JD预分析8维度报告）+
  技能差距学习路径（解析JD缺失技能→生成学习计划→调用topic-knowledge-base建库→学完更新简历）+
  PDF/Word/Markdown多格式导出。支持一键流程：搜索→匹配→选岗→生成简历→技能差距分析。
  典型触发语：'生成简历 方向=xxx'、'找工作 关键词=xxx'、'一键求职 xxx'、'更新简历'、
  '帮我做一份xxx岗位的简历'、'搜索xxx岗位'、'匹配度分析'、'帮我分析缺什么技能'、
  '技能差距学习'、'学完更新简历'。输出到 E:\obsidian\rein\简历库\。
---

# 简历生成器 (resume-builder)

一站式求职自动化工具集：多渠道职位搜索 + AI匹配打分 + 定制简历生成 + 多格式导出。

## 自适应接入（personal-twin，P2）

生成简历/选岗/技能差距分析前，先读取用户画像参数（见
`personal-twin/references/adaptation-guide.md` 的读取命令）：
- **素材详略**：按 `adaptation.<领域>.depth` 决定某技能在简历里的篇幅——level≥3 的领域（如机器视觉）
  可写"独立完成/能应用"级别的量化描述；level≤2 的领域只能写"学习中/了解"，严禁夸大。
- **硬约束**：`hard_facts.constraints` 含"不走施工现场/不读博"时，投递建议必须过滤施工/外业岗，
  优先 AI 视觉、仿真等非现场方向；`weak_top3` 可补充"建议投递的成长岗"。
- **坑点**：`hotspots` 命中技能时，面试准备部分提示"你曾在这踩过坑，建议补强"。
- 读不到画像按默认执行，不阻塞。

## 核心能力

### 1. 多渠道职位搜索
- **BOSS直聘**：关键词+城市+分页+薪资/经验/学历筛选，明文薪资（绕过字体反爬），需要Cookie
- **中南大学就业网**：宣讲会+招聘公告，含职位列表表格，校招核心渠道，不需要Cookie
- **实习僧**：实习岗位，按城市抓取，不需要Cookie

### 2. AI匹配打分
- 5维度评分：技能40% + 经验25% + 项目20% + 学历15%
- 已匹配/缺失技能分析
- 优势/差距分析
- 投递建议（强烈推荐/可以尝试/不建议）
- 面试准备建议

### 3. 定制简历生成
- **双Agent Drafter-Reviewer循环**：Drafter起草 → Reviewer独立评审（7维度）→ 循环修订2轮
- **JD预分析报告**（8维度）：岗位角色摘要/核心要求拆解/匹配度分析/技能差距/薪资参考/简历定制建议/面试准备/投递建议
- 基于Obsidian知识库真实项目经历，严禁编造
- ATS友好，量化成果，去AI味

### 4. 多格式导出
- Markdown源文件（可编辑）
- PDF（Chrome headless，带头像，ATS友好，可选中文字）
- Word（python-docx，可编辑，带头像）

### 5. 一键求职流程（v2）
- **多渠道合并搜索**：BOSS直聘 + 中南大学就业网 + 实习僧，统一格式，自动去重
- **BOSS岗位详情抓取**：自动获取完整JD（非列表页简短描述），简历生成更精准
- **交互式选岗**：搜索匹配后暂停，展示Top 20岗位清单，让用户勾选要生成的岗位
- 搜索 → AI匹配 → 选岗（自动/交互/指定）→ 逐个生成定制简历
- 全程自动化，约17-35分钟完成Top 3
- 输出汇总报告 + 文件清单

### 6. 技能差距学习路径
- **解析缺失技能**：从JD分析报告中自动提取"缺失技能"列表，按权重排序
- **生成学习路径计划**：用LLM为每个缺失技能生成完整学习路径（知识树+学习阶段+资源推荐+成果检验标准）
- **半自动触发**：简历生成后自动展示缺失技能，询问用户要学哪个，确认后调用 topic-knowledge-base 建完整知识库
- **视频教程联动**：可选调用 video-to-knowledge 抓B站/YouTube教程
- **学习闭环**：学完后说"更新简历"，重新扫描知识库并生成更强的简历
- 形成"找工作→发现差距→学习→更新简历→再找工作"的完整闭环

## 脚本位置

所有脚本在 `skills/resume-builder/scripts/`：

| 脚本 | 用途 |
|---|---|
| `job_pipeline.py` | **一键流程 v2**：多渠道搜索→匹配→交互式选岗→生成简历（推荐首选） |
| `skill_gap_learning.py` | **技能差距学习路径**：解析JD缺失技能→生成学习计划→建库（新增） |
| `boss_client.py` | BOSS直聘搜索（需要Cookie） |
| `job_matcher.py` | AI匹配打分（5维度） |
| `csu_career.py` | 中南大学就业网爬虫（宣讲会+招聘公告） |
| `shixiseng_client.py` | 实习僧爬虫（实习岗位） |
| `scan_knowledge.py` | 知识库扫描器（提取项目/技能/成果） |
| `generate_resume.py` | 双Agent简历生成 + JD预分析（核心生成器） |
| `export_pdf.py` | Markdown → PDF（Chrome headless，带头像） |
| `export_docx.py` | Markdown → Word（python-docx，带头像） |
| `pipeline.py` | 旧版主流程（扫描→生成→导出，单岗位） |

## 配置文件

| 文件 | 用途 |
|---|---|
| `config/personal_info.json` | 个人基础信息（姓名/电话/邮箱/教育/校园经历/实习经历），已填写完整 |
| `config/scan_config.json` | 扫描配置（扫描02-学习库/03-项目库/04-简历成长库） |
| `data/boss_cookies.json` | BOSS直聘Cookie（从浏览器导出后导入） |
| `assets/avatar.jpg` | 简历头像（标准JPEG，2:3比例证件照） |
| `scan_result.json` | 知识库扫描结果缓存 |

## 触发指令

### 一键求职流程（推荐，全自动）
```
一键求职 关键词=机器视觉工程师 城市=长沙
找工作 智慧工地工程软件开发工程师
帮我搜xxx岗位并生成简历
```

### 交互式选岗（推荐，你掌控生成哪些）
```
一键求职 关键词=机器视觉 交互模式
找工作 算法工程师 我自己选岗位
```
流程：搜索+匹配完成后，展示Top 20岗位清单，你输入编号（如"1,3,5"或"1-5"或"top5"），确认后生成。

### 只搜索+匹配（不生成简历，先看岗位）
```
搜索岗位 机器视觉工程师 长沙 只看岗位
找工作 xxx 先不生成简历
```
完成后展示岗位清单，你可以选择后续生成。

### 指定搜索渠道
```
一键求职 关键词=xxx 只用BOSS直聘
一键求职 关键词=xxx 渠道=BOSS,中南就业网
找实习 关键词=算法 只用实习僧
```
默认三个渠道都搜（BOSS+中南就业网+实习僧）。

### 仅搜索职位
```
搜索 BOSS直聘 机器视觉工程师 长沙
搜索 中南大学就业网 宣讲会
搜索 实习僧 长沙 算法
```

### 仅匹配打分
```
匹配度分析 岗位文件=jobs.json
给这些岗位打分
```

### 仅生成简历（单岗位）
```
生成简历 方向=机器视觉工程师
更新简历 方向=控制工程
帮我做一份 AI算法工程师 的简历
```

### 只生成 Markdown（不导出 PDF/Word）
```
生成简历 方向=xxx 只导出md
```

### 技能差距学习路径
```
帮我分析缺什么技能
技能差距学习
JD分析后帮我建学习路径
我缺什么技能
学完更新简历
帮我学XX技能
```

## 工作流（Agent 必须严格遵循）

### 方式A：一键求职流程（推荐，全自动）

#### 步骤1：确认参数
- 从用户指令中提取：关键词（必填）、城市（默认长沙）、生成数量（默认Top 3）、搜索渠道（默认全部三个）
- 如果用户没说关键词，询问：`请问想搜索什么岗位关键词？（如：机器视觉工程师、软件开发、算法工程师等）`

#### 步骤2：运行一键流程（多渠道+BOSS详情）
```bash
python "<skill目录>\scripts\job_pipeline.py" \
  --keyword "<关键词>" --city "<城市>" --top 3 --pages 2 --max-match 15 \
  --channels boss,csu,shixiseng
```
- 自动完成：多渠道搜索（BOSS+中南就业网+实习僧，合并去重）→ AI匹配打分（15岗位）→ 自动选Top 3 → 逐个生成简历（**自动抓取BOSS岗位完整JD** + JD分析 + 双Agent循环 + PDF/Word导出）
- 预计17-35分钟
- 输出到 `E:\obsidian\rein\简历库\<关键词>_<时间戳>\`

#### 步骤3：汇报结果
- 列出各渠道搜索到的岗位数、合并去重后总数、匹配度排名、生成的简历清单
- 展示输出目录和文件结构
- 询问：`需要调整关键词、生成更多岗位，或修改简历内容吗？`

### 方式A+：交互式选岗（推荐，你掌控生成哪些）

#### 阶段1：只搜索+匹配（不生成简历）
```bash
python job_pipeline.py --keyword "<关键词>" --city "<城市>" --skip-generate \
  --channels boss,csu,shixiseng
```
- 完成多渠道搜索 + AI匹配打分
- 自动展示 Top 20 岗位清单（含匹配度、岗位、公司、薪资、来源）

#### 阶段2：展示清单，等用户选择
向用户展示岗位清单，说明选择方式：
```
💡 选择方式：
  - 输入编号（多个用逗号分隔）: 1,3,5
  - 输入范围: 1-5
  - 输入 all: 全部生成
  - 输入 top3 / top5 / top10: 自动选前N个
  - 输入 exit: 退出不生成
```

#### 阶段3：根据用户选择生成简历
```bash
python job_pipeline.py --keyword "<关键词>" --skip-search --skip-match \
  --select "1,3,5" --output "<上一阶段的输出目录>"
```
- `--skip-search --skip-match` 复用阶段1的结果，不重复搜索
- `--select` 指定用户选择的岗位编号
- 生成简历时自动抓取BOSS岗位完整JD

### 方式B：分步操作（灵活控制）

#### 步骤1：搜索职位
**BOSS直聘**（需要Cookie）：
```bash
python scripts/boss_client.py "<关键词>" --city <城市> --pages <页数> --output jobs.json
```
**中南大学就业网**（不需要Cookie）：
```bash
python scripts/csu_career.py --type all --pages 3 --detail --output csu.json
```
**实习僧**（不需要Cookie）：
```bash
python scripts/shixiseng_client.py --city <城市> --pages 10 --keyword <关键词> --output interns.json
```

#### 步骤2：AI匹配打分
```bash
python scripts/job_matcher.py --jobs jobs.json --output match.json --top 10 --max-jobs 15
```

#### 步骤3：用户选择岗位
- 向用户展示匹配度排名（Top 10）
- 询问：`请选择要生成简历的岗位编号（可多选，如1,3,5）`

#### 步骤4：生成简历（对每个选中的岗位）
```bash
python scripts/generate_resume.py \
  --scan scan_result.json \
  --personal config/personal_info.json \
  --role "<岗位名称>" \
  --jd "<JD文件路径>" \
  --output "<输出路径>/简历.md" \
  --analyze-output "<输出路径>/JD分析报告.md" \
  --review-output "<输出路径>/评审历史.json"
```

#### 步骤5：导出PDF+Word
```bash
python scripts/export_pdf.py <简历.md> --output <简历.pdf>
python scripts/export_docx.py <简历.md> --output <简历.docx>
```

### 方式C：技能差距学习闭环（找工作→发现差距→学习→更新简历）

#### 触发时机
- 简历生成完成后，Agent 自动检查 JD 分析报告中的缺失技能
- 或用户主动说：`帮我分析缺什么技能`、`技能差距学习`、`我缺什么技能`

#### 步骤1：解析缺失技能
```bash
python scripts/skill_gap_learning.py \
  --jd-report "<JD分析报告路径>" \
  --output "<简历生成目录>/技能差距" \
  --list
```
- 从 JD 分析报告中解析"缺失技能"列表
- 按权重排序（越靠前越重要）
- 展示 Top 5 缺失技能

#### 步骤2：生成学习路径计划
```bash
python scripts/skill_gap_learning.py \
  --jd-report "<JD分析报告路径>" \
  --output "<简历生成目录>/技能差距" \
  --top 3
```
- 为 Top N 缺失技能生成完整学习路径计划
- 每个技能的学习路径包含：技能概述、知识树（先总后细）、学习阶段（入门→基础→进阶→实战）、推荐学习资源（web+视频）、成果检验标准、跟目标岗位的关联
- 输出 `缺失技能汇总.md` + `学习路径_<技能名>.md`

#### 步骤3：展示并询问用户
向用户展示：
- 缺失技能列表（按权重排序，Top 5）
- 最关键技能的学习路径计划摘要
- 询问：`要为哪个技能建知识库？（默认推荐最关键的1个，输入编号或"跳过"）`

#### 步骤4：调用 topic-knowledge-base 建库
用户确认后，调用 topic-knowledge-base skill：
- 关键词 = 技能名称（如"PyTorch深度学习框架"）
- 建库路径 = `E:\obsidian\rein\<技能名>\`
- 建库结构：_知识谱系.md + 分层目录 + 各 _总览.md + 知识点笔记 + _log.md

#### 步骤5：（可选）视频教程联动
如果用户说"还要视频"，调用 video-to-knowledge skill：
- 搜索 B站/YouTube 相关教程
- 下载→转写→总结→写入 Obsidian

#### 步骤6：学习完成后更新简历
用户学完后，说：`更新简历`
- 重新扫描知识库（`scan_knowledge.py`）
- 重新生成简历（匹配度会提升）
- 形成完整闭环：找工作→发现差距→学习→更新简历→再找工作

## BOSS直聘Cookie配置

首次使用BOSS直聘搜索需要配置Cookie：

1. 在浏览器中打开 https://www.zhipin.com，扫码登录
2. 用Cookie-Editor插件导出为Netscape格式，或从开发者工具复制Cookie字符串
3. 导入Cookie：
```bash
# 从文件导入（Netscape格式）
python scripts/parse_cookie.py  # 修改脚本中的文件路径

# 或从字符串导入
python scripts/boss_client.py --from-string "cookie字符串"
```
4. 验证：`python scripts/boss_client.py`（无关键词时只验证Cookie有效性）

Cookie失效时（code=37风控），重新登录并导入即可。

## 个人信息配置

个人信息已填写完整，如需修改编辑：
`skills/resume-builder/config/personal_info.json`

包含：姓名、电话、邮箱、性别、年龄、城市、教育背景、GPA、英语证书、校园经历（学委/就业指导中心助理/奖学金）、实习经历、求职意向。

## 知识库扫描配置

扫描三个库：`02-学习库`、`03-项目库`、`04-简历成长库`，排除`简历素材库.md`。

项目笔记需要包含：项目名称、状态、技术栈、简介、成果/产出。

重新扫描：
```bash
python scripts/scan_knowledge.py --output scan_result.json
```

## 红线（必须遵守）

1. **只读取** Obsidian 知识库，不修改、不删除原笔记
2. **所有项目经历必须来自知识库**，严禁编造不存在的项目、成果、技能
3. **个人信息从配置文件读取**，不编造姓名、电话等隐私信息
4. **输出只写入** `E:\obsidian\rein\简历库\`，不触碰其他目录
5. **每次生成保留历史版本**，不覆盖之前的简历
6. **JD搜索结果仅供参考**，简历内容以知识库真实经历为准
7. **不自动覆盖用户手动修改的简历**，生成新版本而非覆盖
8. **BOSS直聘Cookie是用户隐私**，不输出、不分享、不上传到外部
9. **职位搜索遵守目标网站robots协议和使用条款**，控制请求频率

## 常见问题

### 一键流程太慢怎么办？
- 用 `--top 1` 只生成1份简历（约10分钟）
- 用 `--skip-search --jobs-file jobs.json` 跳过搜索，用已有岗位文件
- 用 `--skip-match --match-file match.json` 跳过匹配，用已有匹配结果

### BOSS直聘搜索报错（code=37风控）
- Cookie失效，重新登录 zhipin.com 并导入新Cookie
- 检查 `data/boss_cookies.json` 是否包含 `__zp_stoken__`
- 降低搜索频率，避免短时间内大量请求

### PDF导出失败
- 检查Chrome路径：`C:\Program Files\Google\Chrome\Application\chrome.exe`
- 已改用Chrome headless（非weasyprint），不需要GTK运行时
- 如果Chrome不存在，会自动尝试Edge

### 知识库扫描不到项目
- 检查 `config/scan_config.json` 中的 `scan_vaults` 配置
- 项目笔记需要在 `03-项目库` 目录下，或有 `project_name` frontmatter
- 可用 `scan_knowledge.py` 单独运行查看扫描结果

### 简历内容太简单/评分低
- 知识库中的项目笔记需要包含：项目简介、技术栈、成果/产出、技术要点
- 参考 `03-项目库` 下的项目笔记格式，补充更多细节
- 可以在 `04-简历成长库/简历素材库.md` 中追加可直接使用的简历片段
- 岗位越具体（如"机器视觉算法工程师" vs "软件开发"），简历生成质量越高

### 想调整简历风格
- 编辑 `generate_resume.py` 中的 `DRAFTER_SYSTEM`/`REVIEWER_SYSTEM`，调整输出格式要求
- 编辑 `export_pdf.py` 中的 `RESUME_CSS`，调整PDF样式
- 编辑 `export_docx.py`，调整Word样式

### 头像显示异常
- 头像必须是标准JPEG格式（不能是WEBP），路径：`assets/avatar.jpg`
- 建议2:3比例证件照，用Pillow转换格式

### 中南大学就业网/实习僧搜不到相关岗位
- 这两个渠道岗位数量有限，长沙的技术岗位可能较少
- 建议用 `--city 全国` 扩大范围
- 或用BOSS直聘作为主渠道，中南大学就业网作为校招补充

### 多渠道搜索怎么配置？
- 默认三个渠道都搜：`--channels boss,csu,shixiseng`
- 只用BOSS：`--channels boss`
- BOSS+中南就业网：`--channels boss,csu`
- 只搜实习：`--channels shixiseng`
- 三个渠道的结果会自动合并去重，统一格式

### BOSS岗位详情抓取是什么？
- 默认开启：生成简历前自动抓取 BOSS 岗位详情页的完整 JD
- 列表页的岗位描述通常只有1-2句话，详情页有完整的岗位职责和任职要求
- 用完整 JD 生成的简历，匹配度和质量会显著提升
- 关闭详情抓取（更快）：加 `--no-detail` 参数
- 中南就业网和实习僧的岗位不支持详情抓取，用列表页数据

### 交互式选岗怎么用？
- 方式1（两阶段，推荐）：
  - 阶段1：`python job_pipeline.py -k "关键词" --skip-generate`（只搜索+匹配，展示岗位清单）
  - 阶段2：`python job_pipeline.py -k "关键词" --skip-search --skip-match --select "1,3,5"`（根据选择生成简历）
- 方式2（直接交互）：`python job_pipeline.py -k "关键词" --interactive`（搜索匹配后自动暂停，等待输入）
- 选择方式：输入编号（`1,3,5`）、范围（`1-5`）、`all`、`top3`/`top5`/`top10`、`exit`

### --skip-generate 是什么？
- 只执行搜索+匹配，不生成简历
- 用于交互式选岗的第一阶段：先看有哪些岗位，再决定生成哪些
- 完成后会展示 Top 20 岗位清单，并提示下一步命令
- 配合 `--skip-search --skip-match --select "编号"` 可以复用结果，不重复搜索

### 技能差距学习路径怎么用？
- **自动触发**：简历生成完成后，Agent 自动检查 JD 分析报告中的缺失技能，生成学习路径计划
- **手动触发**：说`帮我分析缺什么技能`或`技能差距学习`
- **生成学习路径**：`python scripts/skill_gap_learning.py --jd-report <JD报告> --output <目录> --top 3`
- **只看缺失技能列表**：加 `--list` 参数，不生成学习路径
- **建知识库**：选择要学的技能后，调用 topic-knowledge-base skill 建完整知识库
- **视频教程**：可选调用 video-to-knowledge skill 抓 B站/YouTube 教程
- **更新简历**：学完后说`更新简历`，重新扫描知识库并生成更强的简历

### 学习路径计划包含什么？
- 技能概述（是什么、为什么重要、在岗位中的作用）
- 知识树（核心概念→分支领域→具体技术→工具/框架，先总后细）
- 学习阶段（入门→基础→进阶→实战，每个阶段列知识点和预计时间）
- 推荐学习资源（web搜索关键词、视频搜索关键词、经典书籍/课程）
- 成果检验标准（学完能做什么、能解决什么问题、简历上可以怎么写）
- 跟目标岗位的关联（在JD中的权重、掌握后匹配度能提升多少）

### 一次学几个技能？
- 默认只生成 Top 3 技能的学习路径（用 `--top` 控制）
- 建议一次只集中学1个最关键的（权重最高的），避免贪多嚼不烂
- 学完一个再学下一个，逐步提升简历匹配度

### 学习路径跟 topic-knowledge-base 什么关系？
- skill_gap_learning.py 只生成"学习路径计划"（框架和方向）
- 具体的知识库内容（知识点笔记、搜索结果、_知识谱系.md）由 topic-knowledge-base skill 生成
- 工作流：skill_gap_learning 生成计划 → 你确认要学哪个 → 调用 topic-knowledge-base 建完整知识库
- 不重复造轮子，复用已有的建库能力
