# OpenClaw 自研 Skill 集合

> 本人（土木工程背景、跨考控制/机器视觉方向的学习者）在 **OpenClaw + 豆包** 上自研（含深度定制）的 **14 个 Agent Skill**。
> 覆盖：知识库构建、视频转知识、个人画像、求职自动化、竞赛备赛、模型路由与系统运维。
> 核心目标：把"多源信息输入 → 结构化知识沉淀 → 求职/学习输出"串成一条自动化闭环。

---

## 📚 目录

- [一、Skill 总览](#一skill-总览)
- [二、系统架构：学习流水线](#二系统架构学习流水线)
- [三、Skill 逐个详解（功能 + 工作流）](#三skill-逐个详解功能--工作流)
- [四、快速开始](#四快速开始)
- [五、隐私与脱敏说明](#五隐私与脱敏说明)
- [六、依赖环境](#六依赖环境)
- [完整文档](./00_我生成的skill汇总.md) | [第三方 Skill 清单](./99_第三方已装skill清单.md)

---

## 一、Skill 总览

### A. 学习 / 求职核心工作流（10 个）

| Skill | 中文名 | 一句话定位 |
|---|---|---|
| `topic-knowledge-base` | 主题知识库构建器 v2 | 给关键词 → 选信源模式（web/social/hybrid）→ 检索/社媒采集 → "先总后细"建 Obsidian 分层知识库 |
| `material-to-knowledge-base` | 资料包知识库构建器 | 给一包 PDF/Word/Markdown → 查重/OCR/分类 → 建知识谱系库 + 复习清单 |
| `topic-storm-builder` | 主题风暴构建器 | STORM 多视角发散大类 + Deep Research 逐层细化 + 建库 |
| `video-to-knowledge` | 视频转知识库 v2 | B站/YouTube/抖音视频 → 下载 → 转写 → 知识点拆分 → web 深搜 → 9段式深度笔记 + 知识谱系 |
| `concept-linker` | 跨主题概念层构建器 | 扫描全部主题 vault → 建跨主题概念页 / 概念图谱 / 知识库体检 |
| `personal-twin` | 个人镜像 | 构建用户三层画像（档案/能力熟悉度/认知人格），让 Agent 每轮自动"懂你" |
| `daily-learning-summary` | 每日学习汇总 | 读 daily_summary + git + 会话补充 → 汇入日志/学科/项目/简历素材四库 |
| `resume-builder` | 简历生成/求职流水线 v2 | 三渠道搜岗 + AI 匹配 + 交互选岗 + 双 Agent 定制简历 + 技能差距学习闭环 |
| `project-analysis` | 项目系统学习分析 | 把任意代码/开源项目拆成零基础阶梯：档位总控 + 六维拆解 + 九章报告 + 五阶段领学 |
| `competition-analyzer` | 竞赛分析器 | 解读比赛规则/评分 → 技能储备 → 选题 → 五大交付物制备指引 |

### B. 系统运维 / 模型配置（4 个）

| Skill | 中文名 | 一句话定位 |
|---|---|---|
| `chinese-llm-router` | 中文大模型路由 | 一键在 DeepSeek/Qwen/GLM/Kimi/豆包/MiniMax 等国产模型间切换、比价、选型 |
| `token-economy` | Token 成本优化 | 廉价模型优先、零 token 心跳、上下文硬上限、预算护栏 |
| `connect-wechat-qq-channel` | 微信/QQ 通道接入 | 引导接入 OpenClaw 微信（扫码）与 QQ 官方 Bot 通道 |
| `openclaw-plugin-native-rebuild` | 插件原生依赖重建 | 修复装插件后 `Cannot find module 'better-sqlite3'` 类原生二进制缺失报错 |

---

## 二、系统架构：学习流水线

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

- **输入侧**：知识无论来自网络、本地文件、视频还是代码项目，最终归一到同一套 Obsidian 分层结构。
- **关联侧**：`concept-linker` 打通跨主题概念，`personal-twin` 让沉淀带"个人化"标签。
- **沉淀侧**：`daily-learning-summary` 负责日常增量，保证库随学习持续生长。
- **输出侧**：`resume-builder` / `competition-analyzer` 把"学过的东西"变现为求职与竞赛材料。

---

## 三、Skill 逐个详解（功能 + 工作流）

### 1. topic-knowledge-base —— 主题知识库构建器 v2

把任意关键词变成 `E:\obsidian\rein\<主题>\` 下的一套"先总后细"知识谱系库。v2 支持**三种信源模式**：

| 模式 | 信源 | token 预估 | 适用场景 |
|---|---|---|---|
| `web` | 纯联网 8 路搜索 | ~80K | 新领域从零了解、纯技术/学术主题 |
| `social` | MediaCrawler 7 平台社媒采集 | ~120K | 考研/考证/求职等真实经验主题 |
| `hybrid`（默认） | Web 骨架 + 社媒血肉 + 可选教材 PDF | ~150K | 既要体系又要实战经验 |

**工作流**：澄清意图 → 查已有库防重复 → 选信源模式 → 社媒采集/清洗/预压缩（596条→80-120条精华，省 83%）→ 教材 PDF 走 MinerU（≤200页拆分/压缩）→ 8 路串行搜索 → 设计知识谱系树 → **建库蓝图确认关卡** → 双信源融合写笔记（每篇含前置/后续知识 + 3-5 例题 + 3 自测题 + 易错点 + 多平台视角）→ `_媒体融合.md` → MOC 总索引 → 写后回读校验。

### 2. material-to-knowledge-base —— 资料包知识库构建器

输入一个混格式资料包（PDF/Word/Markdown），自动：澄清意图 → 指纹去重 → 逐份提取（PDF 走 OCR/渲染）→ LLM 识别主题并多级分类 → 构建"先总后细"知识谱系树 → 生成结构化笔记 + `_MOC` + `_复习清单`（间隔重复）→ 写后回读校验。分类方式由 LLM 根据内容自动判断，不预设大类。

### 3. topic-storm-builder —— 主题风暴构建器（豆包侧）

两阶段发散建库：**STORM 阶段**用 5 个视角（从业者/研究者/怀疑者/经济观察者/历史观察者）头脑风暴出 6-10 个大类（需用户确认）；**Deep 阶段**逐类深度检索细化（每类结论先展示再继续）；最后按统一模板建 Obsidian 库。适合作为 topic-knowledge-base 的前置增强。

### 4. video-to-knowledge —— 视频转知识库 v2（实战最多）

**链路**：识别平台 → 下载（字幕优先）→ faster-whisper 转写（RTX4060 GPU 加速、长视频 8 分钟分段、四级模型回退）→ LLM 拆成 5-15 个细粒度知识点 → 每知识点 4-6 路 web 深度搜索（必应中国直连）→ 主题确认关卡 → 写两层笔记（视频总览 + 9 段式知识点笔记）+ 知识谱系总图 + 复习清单（1/3/7/15 天）。

**批量能力**：B站合集断点续传、失败统一重试、运行锁防重复、按 video_id 幂等去重、多合集融合对比。已实战：139 个 B 站视频零失败。

### 5. concept-linker —— 跨主题统一概念层构建器

解决"每个主题是孤岛"：扫描所有主题 vault → 46 个核心概念种子全文匹配（线代/高数/概率/自控/神经网络/六级/机器视觉）→ 生成 9 段式概念页（定义 + 跨主题出现位置 + 关系网络 + 学习建议 + 掌握检验）→ Mermaid 概念图谱。附带：知识库体检（死链/重复/孤儿/矛盾）、8 种笔记模板、知识地图、概念掌握度推断、实体层、定时自动增量更新。

### 6. personal-twin —— 个人镜像（个性化服务中枢）

构建"用户本人"三层画像：① 静态档案；② **证据驱动能力画像**（0-4 级熟悉度，课程视频最高 2 级、到 3 级必须真实实践、错题卡点加权、超 30 天标生疏）；③ 认知人格（大五 BFI-10 + VARK 学习风格，以量表为锚、不做心理诊断）。**更新走 Windows 任务计划**（每日增量/周日全量+快照），不依赖网关在线。对外接口输出各领域讲解深度/风格/例子，已接入 5 个 skill 做自适应。

### 7. daily-learning-summary —— 每日学习汇总

读三类输入（项目 daily_summary.md + 24h git 提交只读 + 会话补充），汇入四大库（每日日志/学科库/项目库/简历素材库）。硬规则：写前预览等确认、不静默覆盖、不虚构成果。

### 8. resume-builder —— 简历生成 / 求职流水线 v2

**链路**：三渠道搜岗（BOSS直聘 Cookie 直连内部 API / 中南大学就业网 / 实习僧）→ 合并去重 → AI 5 维匹配打分 → 交互式选岗 → 抓完整 JD → JD 预分析 8 维报告 → Drafter-Reviewer 双 Agent 循环修订 2 轮 → 导出 PDF/Word。v2 新增**技能差距学习闭环**：解析 JD 缺失技能 → 生成学习路径 → 调用 topic-knowledge-base 建库 → 学完"更新简历"再投。

### 9. project-analysis —— 项目系统学习分析

把任意代码/开源项目拆成零基础可掌握的阶梯：**档位总控**（速览体检卡/标准九章报告/深度+精读副本）→ **项目适配引擎**（自动识别项目类型、重排六维权重、难度打分、方向加权）→ **六维拆解** → **九章学习报告** → **五阶段领学**（补地基→跑通→骨架→精读→改造，每阶段"做出来给我看"验收）→ 成果包自动同步 Obsidian。带双人 Review 质检与质量门禁。

### 10. competition-analyzer —— 竞赛分析器

六步闭环：读官方通知 → 比赛解读（赛制/时间线/评审标准/奖项，表格化+附来源）→ 技能与知识储备清单（P0/P1/P2）→ 选题方向（评分反推→交集定位→差异化→验证清单）→ 五大交付物制备（申报书/Demo/架构图/现场演示/源码仓库）→ GitHub 成品项目检索复用。已内置"海之子"杯 AI 智能体挑战计划档案。

### 11-14. 系统运维类

| Skill | 功能 |
|---|---|
| `chinese-llm-router` | 10+ 国产模型统一路由：场景化推荐（编程/数学/推理/廉价/Agent…）+ 切换/比价 |
| `token-economy` | 廉价优先 + 升级策略、零 token 心跳、上下文硬上限、预算护栏、token 审计 |
| `connect-wechat-qq-channel` | 微信（必须本机扫码）与 QQ 官方 Bot（appId/secret）接入与诊断 |
| `openclaw-plugin-native-rebuild` | 插件原生依赖（better-sqlite3 等）npm rebuild + 验证 |

---

## 四、快速开始

1. **安装**：把 `skills/` 下需要的 Skill 文件夹整个复制到你的 OpenClaw `workspace/skills/`（或豆包 `.user_skills/`），重启网关。
2. **改路径**：本仓库 Skill 大量使用 `E:\obsidian\rein\` 作为知识库根目录，请按你的环境全局替换。
3. **配密钥**：脚本不再内置任何 Key，统一从环境变量读取：
   - `DEEPSEEK_API_KEY`（视频转写/简历生成的 LLM 调用）
   - 各模型供应商 Key（chinese-llm-router 用 `setup.js` 交互式配置）
   - BOSS直聘 Cookie（resume-builder 运行时放入 `data/boss_cookies.json`，已 gitignore）
4. **常用触发**：详见各 Skill 的 `SKILL.md`，触发语多为自然语言（如"研究 X 并建库"、"视频笔记 <链接>"、"一键求职 关键词=xxx"）。

---

## 五、隐私与脱敏说明

本仓库为**公开仓库**，已做以下脱敏（本地完整版保留所有文件，请勿外传）：

- **已删除**：`resume-builder/config/personal_info.json`（姓名/电话/邮箱）、`data/boss_cookies.json`（登录 Cookie）、`assets/avatar.jpg`、`scan_result.json`；`video-to-knowledge/douyin-cookies.txt`、`progress/`；所有 `debug_*.py` 调试脚本、运行时 `logs/`。
- **已替换**：脚本中硬编码的 API Key → `os.environ.get("DEEPSEEK_API_KEY", "")`。
- 若你 fork 使用，请自行维护 `.gitignore`（见仓库根目录），不要把 Cookie、密钥、个人信息提交进任何公开仓库。

> ⚠️ `personal-twin` 的档案模板含个人信息示例，请按需修改后再使用。

---

## 六、依赖环境

| 能力 | 依赖 |
|---|---|
| 视频转写 | Python + faster-whisper + ffmpeg + CUDA（可选 GPU 加速） |
| 简历 PDF 导出 | Chrome / Edge headless |
| 中文 PDF 解析 | MinerU（mineru.net API） |
| 社媒采集 | MediaCrawler（7 平台，需各平台扫码登录） |
| 知识库 | Obsidian（纯 Markdown，不依赖插件） |

---

## 许可说明

本仓库内容为个人学习实践产物，**未指定开源许可**，请仅用于学习参考。其中 `chinese-llm-router`、`token-economy` 基于 ClawHub 通用模板深度定制，请遵守其原始许可。
