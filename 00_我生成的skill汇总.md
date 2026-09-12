# 我生成的 Skill 汇总与使用说明

> 汇总时间：2026-09-13
> 汇总范围：本人在 OpenClaw / 豆包中**自建（含深度定制）**的 14 个 Skill
> 源文件备份：本目录 `skills源文件/` 下，每个子文件夹即一个可直接放回 skills 目录使用的完整 Skill（最新版）
> 第三方下载的 Skill 不在此列，见同目录 `99_第三方已装skill清单.md`
> 成长经历档案（含简历素材，含个人身份信息，**未随公开仓库发布**）见 `01_近期成长经历总结(给OpenClaw读取).md`

---

## 一、总览表

### A. 学习 / 求职核心工作流（10 个，本人原创设计）

| # | Skill | 中文名 | 一句话定位 | 运行位置 |
|---|---|---|---|---|
| 1 | `topic-knowledge-base` | 主题知识库构建器 v2 | 给关键词→选信源模式（web/social/hybrid）→检索/采集→"先总后细"建 Obsidian 分层知识库 | OpenClaw |
| 2 | `material-to-knowledge-base` | 资料包知识库构建器 | 给一包 PDF/Word/Markdown→自动查重/OCR/分类→建知识谱系库+复习清单 | OpenClaw |
| 3 | `topic-storm-builder` | 主题风暴构建器 | STORM 多视角发散大类 + Deep Research 逐层细化 + 建库，主题库"加强版前置" | 豆包 |
| 4 | `video-to-knowledge` | 视频转知识库 v2 | B站/YouTube/抖音视频→下载→转写→知识点拆分→web深搜→9段式深度笔记+知识谱系 | OpenClaw |
| 5 | `concept-linker` | 跨主题概念层构建器 | 扫描全部主题 vault→提取核心概念→建跨主题概念页/概念图谱/知识库体检 | OpenClaw |
| 6 | `personal-twin` | 个人镜像 | 构建"用户本人"三层画像（档案/能力熟悉度/认知人格），让 Agent 每轮自动"懂你" | OpenClaw |
| 7 | `daily-learning-summary` | 每日学习汇总 | 读 daily_summary+git+会话补充→汇入日志/学科/项目/简历素材四库 | OpenClaw |
| 8 | `resume-builder` | 简历生成/求职流水线 v2 | 三渠道搜岗+AI匹配+交互选岗+双Agent定制简历+技能差距学习闭环，导出 PDF/Word | OpenClaw |
| 9 | `project-analysis` | 项目系统学习分析 | 把任意代码/开源项目拆成零基础阶梯：档位总控+六维拆解+九章报告+五阶段领学 | OpenClaw |
| 10 | `competition-analyzer` | 竞赛分析器 | 解读比赛规则/评分→技能储备→选题→五大交付物（申报书/Demo/架构图/演示/源码）制备 | OpenClaw+豆包 |

### B. 系统运维 / 模型配置（4 个，针对本机环境定制）

| # | Skill | 中文名 | 一句话定位 |
|---|---|---|---|
| 11 | `chinese-llm-router` | 中文大模型路由 | 一键在 DeepSeek/Qwen/GLM/Kimi/豆包/MiniMax 等国产模型间切换、比价、选型 |
| 12 | `token-economy` | Token 成本优化 | 廉价模型优先、零 token 心跳、上下文硬上限、预算护栏，降低调用成本 |
| 13 | `connect-wechat-qq-channel` | 微信/QQ 通道接入 | 引导接入 OpenClaw 微信（扫码）与 QQ 官方 Bot（appId/secret）通道 |
| 14 | `openclaw-plugin-native-rebuild` | 插件原生依赖重建 | 修复装插件后 `Cannot find module 'better-sqlite3'` 类原生二进制缺失报错 |

---

## 二、这些 Skill 串成了一条"学习 → 沉淀 → 输出"闭环

```text
        ┌──────────────── 知识输入（四种来源）────────────────┐
        │                                                     │
  关键词全网检索         本地资料包             视频/网课        代码/开源项目
 topic-knowledge-base  material-to-knowledge  video-to-knowledge  project-analysis
  (web/social/hybrid)  (PDF/Word/md)          (B站/YT/抖音)
        │                     │                     │                │
        ▼                     ▼                     ▼                ▼
 topic-storm-builder（先发散大类 → 再逐层细化，可作为前两者的前置增强）
        │
        ▼
  统一沉淀到 Obsidian：E:\obsidian\rein\  （每个主题独立 vault，先总后细谱系结构）
        │
        ├── concept-linker：跨主题概念层，把各主题孤岛连通（概念页+图谱+体检）
        ├── personal-twin：基于四库+错题卡点持续构建"用户画像"，反向调优其他 skill
        ├── daily-learning-summary：每天把代码项目学习/git 记录汇入四库
        ▼
  resume-builder：读取知识库+画像 → 联网搜真实岗位 → 按 JD 定制简历 → 技能差距→再学习
  competition-analyzer：把学到的能力打包成竞赛交付物（申报书/Demo/源码）
```

- **输入侧**：知识无论来自网络、本地文件、视频还是代码项目，最终都归一到同一套 Obsidian 分层结构。
- **关联侧**：`concept-linker` 打通跨主题概念，`personal-twin` 让沉淀带"个人化"标签。
- **沉淀侧**：`daily-learning-summary` 负责日常增量，保证库随学习持续生长。
- **输出侧**：`resume-builder` / `competition-analyzer` 把"学过的东西"变现为求职与竞赛材料，形成"输入→关联→沉淀→输出"闭环。

---

## 三、核心工作流 Skill 逐个详解

### 1. topic-knowledge-base —— 主题知识库构建器 v2（含三信源）

- **解决的问题**：想系统了解一个陌生主题时，不用自己到处搜、到处建文件夹。
- **核心升级（v2）**：支持**三种信源模式**：
  | 模式 | 信源 | token 预估 | 适用 |
  |---|---|---|---|
  | `web` | 纯联网 8 路搜索 | ~80K | 新领域/纯技术学术主题 |
  | `social` | MediaCrawler 7 平台社媒采集（B站/知乎/抖音/小红书/快手/微博/贴吧） | ~120K | 考研/考证/求职等真实经验主题 |
  | `hybrid`（默认） | Web 建知识骨架 + 社媒注入血肉 + 可选教材 PDF | ~150K | 既要体系又要实战经验 |
- **完整工作流**：澄清意图（Clarification Gate）→ 查已有库防重复 → 选信源模式 → 社媒采集+清洗+预压缩（596条→80-120条精华，省 83%）→ 教材 PDF 走 MinerU（≤200页拆分/压缩）→ 8 路串行搜索 → 设计"先总后细"知识谱系树 → **建库蓝图确认关卡**（谱系+笔记清单+信源构成，等用户确认）→ 双信源融合写笔记（每篇含前置/后续知识+3-5例题+3自测题+易错点+多平台视角）→ `_媒体融合.md`（平台覆盖/共识/分歧）→ MOC 总索引 → 写后回读校验。
- **输出**：`E:\obsidian\rein\<主题>\` 下 `_知识谱系.md` + 分层目录 + 每类 `_总览.md` + 知识点笔记 + `_log.md` 增量日志。
- **触发**："研究/学习/了解 X"、"建库 关键词=X 模式=hybrid"、"采集并建库 X"。

### 2. material-to-knowledge-base —— 资料包知识库构建器

- **解决的问题**：手上有一堆混格式学习资料（PDF/Word/Markdown），杂乱无章。
- **做什么**：澄清整理意图 → 查已有库/指纹去重 → 扫描预检 → 逐份提取文本（PDF 走 OCR/渲染管线）→ LLM 自动识别主题、多级分类并构建"先总后细"知识谱系树 → 按谱系建目录、生成 `_知识谱系.md` 与各 `_总览.md` → 结构化笔记（来源/前置知识/关联知识点/自我检测/复习排期）→ `_MOC` + `_复习清单` → 写后回读校验。
- **核心文件**：`scripts/probe_pdf.py`、`render_pdf.py`、`ocr_windows.ps1`；`references/templates.md`、`spaced-repetition.md`。
- **特点**：分类方式由 LLM 根据内容自动判断，不预设固定大类；自带间隔重复复习闭环。

### 3. topic-storm-builder —— 主题风暴构建器（豆包侧）

- **解决的问题**：topic-knowledge-base 直接检索可能角度不够全、不够发散。
- **三个阶段**：① **STORM 发散**——5 个视角（从业者/研究者/怀疑者/经济观察者/历史观察者）各产出"关注点+支持/挑战+独特信息"，构建矛盾图与 6-10 个大类的知识树（**大类清单必须经用户确认**）；② **Deep 细化**——逐类生成 2-3 路搜索、每类产出核心发现/定量数据/洞察/争议/信息缺口（**每类结论先展示再继续**）；③ **建库**——在 `E:\obsidian\rein\<主题>\` 写 `_知识谱系.md`（Mermaid mindmap）/`_MOC.md`/`_log.md`/分目录笔记，写后回读校验。
- **运行位置**：豆包 `.user_skills`（不依赖 OpenClaw）。

### 4. video-to-knowledge —— 视频转知识库 v2（最成熟，实战最多）

- **解决的问题**：B站/YouTube/抖音网课无法变成可检索、可复习的文字笔记。
- **v2 核心升级**：单篇总结 → **两层深度笔记**（视频总览 + 每个知识点独立 9 段式笔记）；3-8 个知识点 → **5-15 个细粒度知识点**（含前置/后续/关联/公式/例题）；单信源 → **三信源融合**（视频+web 深度搜索+可选教材）；新增**知识谱系总图**（Mermaid mindmap+关联图）与**复习清单**（1/3/7/15 天间隔重复）。
- **完整链路**：识别平台 → 抓元数据 → 有字幕优先/无字幕 faster-whisper 转写（RTX4060 GPU 加速、8分钟分段、四级模型回退）→ LLM 知识点拆分 → 每知识点 4-6 路 web 搜索（必应中国直连为主，DDG 仅 VPN 备选）→ 主题确认关卡（**禁止静默写入**）→ 写入 Obsidian → 自动删除音视频。
- **批量能力**：B站合集/分P，断点续传、失败统一 `--retry-failed`、运行锁防重复、按 video_id 幂等去重、多合集 `fusion_compare.py` 融合对比。
- **已实战验证**：139 个 B 站视频（自控原理 47 集 + 六级 91 集 + 考研高数）全部转写零失败。
- **自带故障排查手册**：下载/转写/GPU/编码/重复/搜索 6 大类 30+ 实战坑位速查表。

### 5. concept-linker —— 跨主题统一概念层构建器

- **解决的问题**："每个主题是孤岛"——同一个概念散落在不同 vault，学新知识关联不到已学。
- **做什么**：扫描所有主题笔记 → 46 个核心概念种子全文匹配（覆盖线代/高数/概率/自控/神经网络/六级/机器视觉 7 大学科）→ 按主题分组出现位置 → 生成**9 段式概念页**（定义+跨主题出现位置+概念关系网络+学习建议+掌握检验）→ Mermaid 概念图谱 → 概念层总索引 `_概念图谱.md`。
- **附加能力**：①**知识库体检**（死链/重复/孤儿/矛盾四检）；②8 种标准笔记模板；③**知识地图**（8 大导航入口+总仪表盘，不物理移动现有目录）；④**概念掌握度**（结合 personal-twin 错题卡点推断，人工标记优先）；⑤**实体层**（人物/书籍/工具跨主题关联页）；⑥Windows 任务计划每小时增量自动更新。
- **红线**：只在 `E:\obsidian\rein\_概念层\` 下创建文件，不触碰现有主题 vault。

### 6. personal-twin —— 个人镜像（个性化自适应服务中枢）

- **解决的问题**：让 Agent 从"通用助手"变成"了解用户本人的专属助手"。
- **三层画像**：① 静态档案（基本情况/目标/硬约束）；② 证据驱动能力画像（0-4 级熟悉度：0未接触→4能教别人，课程视频最高 2 级、到 3 级必须有真实实践，错题卡点加权、30天无接触标生疏）；③ 认知与人格画像（大五 BFI-10 量表 + VARK 学习风格 + AI 微调，**以量表为锚、不做心理诊断**）。
- **工作流**：`【个人镜像 初始化】`（建档案+量表）→ `【记录卡点】`一句话（高频低摩擦，自动补全结构化条目）→ `【个人镜像 刷新】`（全量重算）→ `【我现在什么水平】`（读画像出分析+短板 TOP3+建议）。更新走 **Windows 任务计划**（每日 23:00 增量、周日 21:00 全量+快照），不依赖 OpenClaw 网关在线。
- **对外接口**：`adaptive_service.py --profile/--next` 输出各领域讲解深度/风格/例子与"下一步学什么"；`_注入摘要.md`（≤1500字）同步 openwave self-model，实现每轮自动"懂你"。已接入 video-to-knowledge / topic-knowledge-base / material-to-knowledge-base / resume-builder / deep-research。

### 7. daily-learning-summary —— 每日学习汇总

- **解决的问题**：每天在 VSCode+DeepSeek-Harness 里学的东西零散，需要稳定汇入长期知识库。
- **三类输入**：① 项目根目录 `daily_summary.md`；② 最近 24h git 提交（**只读，绝不 commit/push**）；③ 会话补充。**禁止抓取 VSCode 插件内部对话**。
- **四个输出库**：`01-每日日志/Daily/`、`02-学习库/{学科}/`（费曼总结/易混/错题）、`03-项目库/{项目}/README.md`（环境/技术点/代码片段/bug/简历素材）、`04-简历成长库/简历素材库.md`。
- **触发**：`【同步Obsidian 项目路径=xxx】`；`【追加补充学习】`。
- **硬规则**：写前完整预览并等【确认】，禁止静默写入/覆盖；不虚构成果。

### 8. resume-builder —— 简历生成 / 求职一键流水线 v2

- **解决的问题**：把知识库积累变成针对具体岗位的高质量简历，并自己找岗位。
- **v2 新增**：**技能差距学习闭环**——简历生成后自动解析 JD 缺失技能 → 生成学习路径计划（知识树/阶段/资源/检验标准）→ 确认后调用 topic-knowledge-base 建库 → 学完说"更新简历"重新生成，形成"找工作→发现差距→学习→更新简历"闭环。
- **完整链路**：三渠道搜岗（BOSS直聘 Cookie 直连内部 API 绕过字体反爬 / 中南大学就业网 / 实习僧免 Cookie）→ 合并去重 → AI 5 维匹配打分 → **交互式选岗**（Top20 清单，输入编号/范围/topN）→ 自动抓取 BOSS 完整 JD → JD 预分析 8 维报告 → **Drafter-Reviewer 双 Agent 循环修订 2 轮** → 导出 Markdown/PDF（Chrome headless）/Word。
- **自适应接入**：读取 personal-twin 画像——level≥3 领域可写"独立完成"级描述，level≤2 只能写"学习中"；"不走现场/不读博"硬约束自动过滤施工岗。
- **红线**：项目经历必须来自知识库严禁编造；个人信息从配置读取；Cookie 不上传不外泄。

### 9. project-analysis —— 项目系统学习分析

- **解决的问题**：把任意代码/开源项目拆解成零基础学生可逐步掌握的阶梯，并产出《项目学习报告》。
- **核心机制**：
  - **深度档位总控**：速览（单屏体检卡）/ 标准（九章报告）/ 深度（+精读副本+改造挑战+复盘），可无缝升降档；
  - **项目适配引擎**：自动识别项目类型（算法库/深度学习/Web/CLI/桌面/ETL）→ 重排六维权重 → 专属章节插队 → 难度 0-100 打分 → 按用户方向（控制/机器视觉/土木检测）加权；
  - **六维拆解**：宏观定位→架构骨架→核心算法→数据流→工程实践→可扩展性；
  - **九章报告**：概览/技术栈/架构图/核心流程/算法详解/代码精读/运行调试/思考收获/下一步；
  - **五阶段路径**：补地基→环境跑通→骨架通读→核心精读→动手改造（每阶段设"做出来给我看"验收，不过不退）；
  - **对话教练型交互**：分阶段解锁领学 + 关键词扩写沉浸 + Socratic 追问 + 讲解/报告双轨；
  - **成果包**：`<项目名>_learning_assets/`（report + annotated_code 三级注释 + flashcards + todo_list），自动同步 Obsidian；
  - **质量闭环**：六维质检清单 + AI 双角色对弈复审 + Review 留痕 + 反馈修订。
- **触发**："学习/分析某个项目"、"出一份项目学习报告"。

### 10. competition-analyzer —— 竞赛分析器

- **解决的问题**：参加竞赛（挑战杯/互联网+/AI 智能体类赛事）时，花最少时间看清比赛、选对方向、交付能过评审的成品。
- **六步闭环**：① 收集输入（用 web_fetch 读官方通知原文）；② 比赛解读（主办方/赛道/时间线/评审标准/奖项，表格化输出并附来源）；③ 技能与知识储备（硬技能/软技能/知识储备三列清单 + P0/P1/P2 优先级）；④ 选题方向（评分反推→交集定位→差异化→验证清单，输出 2-3 候选方向）；⑤ 交付物制备（初赛申报书+≤5min Demo+1页架构图；决赛可交互原型+源码仓库；全国赛加技术文档+路演）；⑥ GitHub 开源检索（克隆即跑→二开→框架→思路四档，核验许可证）。
- **已内置档案**："海之子"杯 AI 智能体挑战计划完整档案 + 绿色建筑赛道落地思路（references/）。
- **输出规范**：所有事实附官方来源链接、标注"已查证"；时间线/架构用可视化呈现。

---

## 四、系统运维 / 模型配置类 Skill

### 11. chinese-llm-router 中文大模型路由
- 统一界面切换国产大模型：DeepSeek、Qwen、GLM、Kimi、豆包、MiniMax、Step、百川、讯飞星火、混元。
- 按场景路由：编程/数学/推理/写作/对话/快速/廉价/Agent 各有推荐模型链 + fallback。
- 触发：`list models`、`use <model>`、`compare <models>`。
- 来源：基于通用路由模板，按本人已配置的各家密钥深度定制。

### 12. token-economy 成本优化
- 廉价模型优先 + 复杂任务逐级升级；上下文硬上限（默认单包 1 万 token 自动截断）；心跳文件为空就跳过 API 调用（零 token）；预算护栏与 token 审计。
- 触发：问成本、路由、省 token、预算时。

### 13. connect-wechat-qq-channel 通道接入
- 区分两套机制：微信 `openclaw-weixin` 必须**用户本人在真实终端扫码**（exec 工具会硬拦截代跑）；QQ 官方 Bot 用 appId+clientSecret，不需扫码。
- 内置诊断命令（`channels list/status`）和常见误判澄清（enabled 不等于已登录，要看 configured 字段）。

### 14. openclaw-plugin-native-rebuild 原生依赖重建
- 解决 OpenClaw 插件安装用 `--ignore-scripts` 导致 better-sqlite3/sqlite-vec 缺编译二进制、网关加载报 `Cannot find module` 的问题。
- 流程：定位插件目录 → 看 package.json 原生依赖 → `npm rebuild` → `node -e "require(...)"` 验证 → 每次插件更新后重跑。

---

## 五、典型配合场景

1. **从零学一个新方向**：`topic-storm-builder` 发散大类 → `topic-knowledge-base` 检索建库 → 网课链接丢给 `video-to-knowledge` 转笔记 → PDF 资料用 `material-to-knowledge-base` 并入 → 建完跑 `concept-linker` 更新概念层 → `personal-twin` 记录卡点更新画像。
2. **学一个开源项目**：`project-analysis` 六维拆解+九章报告 → 成果同步 Obsidian → 概念层自动关联 → 简历素材入库。
3. **日常学习闭环**：白天在项目里学，晚上发 `【同步Obsidian 项目路径=...】`，`daily-learning-summary` 汇入四库并积累简历素材。
4. **找工作冲刺**：`resume-builder` 三渠道搜岗 → 匹配选岗 → 定制 PDF/Word 简历 → 技能差距 → 用 `topic-knowledge-base`/`video-to-knowledge` 补课 → "更新简历"再投。
5. **打比赛**：`competition-analyzer` 解读规则 → 结合 `topic-knowledge-base` 建赛题知识库 → 产出申报书/Demo/架构图/源码仓库。
6. **模型与成本**：平时用 `chinese-llm-router` 选模型，`token-economy` 压成本，大批量转写前先切廉价模型预览。

---

## 六、维护与安全提醒（重要）

1. **含敏感个人信息，禁止上传公开仓库/外传**（公开仓库已脱敏，本地完整版注意保管）：
   - `resume-builder/config/personal_info.json`（姓名、电话、邮箱）、`data/boss_cookies.json`（登录 Cookie）、`assets/avatar.jpg`；
   - `video-to-knowledge/douyin-cookies.txt`（抖音登录态）；
   - 各脚本中硬编码的 API Key（已全部改为 `os.environ.get("DEEPSEEK_API_KEY")` 读取）。
   - 公开版本已删除：上述文件 + `debug_*.py` 调试脚本 + `progress/`/`logs/` 运行时数据。
2. **统一路径约定**：知识库输出根目录 `E:\obsidian\rein\<主题>\`；视频临时目录 `E:\openclaw-video-temp\`；简历输出 `E:\obsidian\rein\简历库\`。迁移电脑时这些路径要一起改。
3. **放回 OpenClaw 的方法**：把 `skills源文件/` 下对应文件夹整个复制到 `C:\Users\Lenovo\.openclaw\workspace\skills\`，重启网关即可；`topic-storm-builder`、`competition-analyzer` 也放豆包 `.user_skills` 目录。
4. **依赖环境**：视频转写需 Python + faster-whisper + ffmpeg + CUDA（RTX4060）；简历 PDF 导出依赖本机 Chrome/Edge；中文 PDF 解析依赖 MinerU；社媒采集依赖 MediaCrawler。
5. **备份内容说明**：本次为完整备份，包含运行产生的进度文件、调试脚本，不影响使用，需要精简可自行删除。
