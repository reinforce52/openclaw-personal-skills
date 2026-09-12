# personal-twin 自适应接入指南（其他 skill 用）

> 目的：让 video-to-knowledge / topic-knowledge-base / material-to-knowledge-base /
> resume-builder / deep-research 等 skill 在服务时，自动按用户画像调整
> 讲解深度、例子类型、输出形式。**读不到画像时按通用方式执行，不阻塞。**

## 一、如何读取（统一命令）

在 skill 的关键环节（见各 skill 钩子）用**系统 Python** 调用一次：

```bash
# 服务参数（每个领域的 depth/style/example_kind/pace + weak_top3 + hotspots + 硬约束）
python <personal-twin 目录>/scripts/adaptive_service.py --profile

# 下一步推荐（可选，报告/计划类可引用）
python <personal-twin 目录>/scripts/adaptive_service.py --next
```

数据源：`E:\obsidian\rein\_个人镜像\mastery_data.json`（每次刷新自动更新，无需手动维护）。
Windows PowerShell 里用 `& "C:\...\python.exe" "C:\...\adaptive_service.py" --profile`。

## 二、参数含义速查

`adaptation.<领域>` 字段：

| 字段 | 值 | 含义 |
|---|---|---|
| `depth` | from_zero / concept_plus_practice / fast_practice / expert_dialogue | 该领域该讲多深 |
| `style` | 中文描述 | 讲解风格（结构化表格/类比/实战） |
| `example_kind` | 中文描述 | 例子类型（如自控用土木类比） |
| `pace` | 中文描述 | 节奏 |
| `current_level` / `level_name` | 0-4 / 名称 | 当前熟悉度（唯一可复核依据） |

顶层：`weak_top3`（最该补的 3 个短板）、`hotspots`（高频坑点）、`hard_facts.constraints`（硬约束，如不走现场）。

## 三、通用应用规则（各 skill 共同遵守）

1. **深度匹配**：目标领域 level ≤2 → 从概念讲起、给背景；=3 → 跳过基础、直接上实践/真题；=4 → 直接讨论/迁移。
2. **例子本地化**：`example_kind` 给什么就用什么（控制工程一律用土木机械类比，六级用真题/长难句例句）。
3. **输出形式（按 VARK：K>R>A>V）**：优先**结构化分步 + 可动手/可跑的清单**，其次文字表格；纯示意图可有但绝不只给图。
4. **硬约束优先**：`hard_facts.constraints` 出现"不走施工现场/不读博"时，涉及职业/项目建议必须遵守。
5. **不编造掌握**：领域 level≤2 时，输出里不得写成"已掌握/能独立完成"，用"学习中/理解概念阶段"。
6. **坑点提醒**：若 `hotspots` 命中当前任务涉及的知识点，输出时主动带一句"这是你记过的高频坑点"。

## 四、失败降级

- 画像文件不存在 / Python 不可用 / 命令超时 → 按通用深度讲解，正常执行任务，不报错、不中断。
- 目标领域不在画像里 → 默认 concept_plus_practice 深度。
