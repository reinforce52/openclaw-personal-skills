#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 简历生成模块 v2 - 基于 ai-job-search 的 Drafter-Reviewer 双 Agent 循环
- Drafter: 基于知识库 + JD 起草定制简历
- Reviewer: 全新上下文，独立分析 JD 后批评初稿（关键词覆盖/量化/套话/岗位匹配）
- 循环修订 2 轮，最终输出高质量 ATS 友好简历
调用中南大学 deepseek-v3
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime

# ============ 中南大学 API 配置 ============
API_BASE = "https://api.chat.csu.edu.cn/v1"
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")  # 从环境变量读取，不要硬编码密钥
MODEL = "deepseek-v3"

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_REVISION_ROUNDS = 2  # 最多修订轮数


def normalize_skills(skills: list) -> list:
    """技能关键词归一化：去重、统一大小写、排序"""
    seen = {}
    for s in skills:
        key = s.lower()
        if key not in seen:
            seen[key] = s
    result = list(seen.values())
    result.sort(key=lambda x: (0 if x[0].isascii() else 1, x.lower()))
    return result


def load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.4, max_tokens: int = 6000) -> str:
    """调用 LLM，返回纯文本结果"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        resp = requests.post(f"{API_BASE}/chat/completions", headers=headers, json=payload, timeout=180)
        resp.raise_for_status()
        result = resp.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"ERROR: {str(e)[:300]}"


def build_knowledge_summary(scan_result: dict) -> str:
    """把扫描结果整理成 LLM 可读的文本"""
    projects = scan_result.get("projects", [])
    skills = normalize_skills(scan_result.get("all_skills", []))

    text = f"## 技能关键词（共{len(skills)}个）\n"
    text += ", ".join(skills) + "\n\n"
    text += f"## 项目经历（共{len(projects)}个）\n"

    for i, p in enumerate(projects, 1):
        text += f"\n### 项目{i}: {p.get('name', '未知')}\n"
        text += f"- 状态: {p.get('status', '未知')}\n"
        text += f"- 技术栈: {', '.join(p.get('tech_stack', [])[:15])}\n"
        text += f"- 项目简介: {p.get('description', '')[:400]}\n"

        achievements = p.get("achievements", [])
        if achievements:
            text += f"- 成果/产出:\n"
            for a in achievements:
                text += f"  - {a}\n"

        learnings = p.get("key_learnings", [])
        if learnings:
            text += f"- 技术要点:\n"
            for l in learnings[:5]:
                text += f"  - {l}\n"

    return text


def build_personal_info_text(personal: dict) -> str:
    """把个人信息整理成文本"""
    lines = []
    if personal.get("name"):
        lines.append(f"姓名: {personal['name']}")
    if personal.get("phone"):
        lines.append(f"电话: {personal['phone']}")
    if personal.get("email"):
        lines.append(f"邮箱: {personal['email']}")
    if personal.get("city"):
        lines.append(f"城市: {personal['city']}")

    edu = personal.get("education", {})
    if edu:
        lines.append(f"\n教育背景:")
        lines.append(f"- 学校: {edu.get('school', '')}")
        lines.append(f"- 专业: {edu.get('major', '')}")
        lines.append(f"- 学历: {edu.get('degree', '')}")
        lines.append(f"- 年级: {edu.get('grade', '')}")
        if edu.get("gpa"):
            lines.append(f"- GPA: {edu['gpa']}")
        lines.append(f"- 时间: {edu.get('start_date', '')} ~ {edu.get('end_date', '')}")

    if personal.get("languages"):
        lines.append(f"\n语言能力: {', '.join(personal['languages'])}")
    if personal.get("certifications"):
        lines.append(f"\n证书: {', '.join(personal['certifications'])}")
    if personal.get("awards"):
        lines.append(f"\n获奖: {', '.join(personal['awards'])}")

    # 实习经历
    internships = personal.get("internship_experience", [])
    if internships:
        lines.append(f"\n实习经历（共{len(internships)}条）:")
        for i, exp in enumerate(internships, 1):
            lines.append(f"- 实习{i}: {exp.get('company', '')} | {exp.get('role', '')} | {exp.get('time', '')}")
            lines.append(f"  内容: {exp.get('description', '')}")

    # 校园经历
    campus = personal.get("campus_experience", [])
    if campus:
        lines.append(f"\n校园经历（共{len(campus)}条）:")
        for i, exp in enumerate(campus, 1):
            lines.append(f"- 经历{i}: {exp.get('organization', '')} | {exp.get('role', '')} | {exp.get('time', '')}")
            lines.append(f"  内容: {exp.get('description', '')}")

    return "\n".join(lines)


# ============================================================
# JD 预分析 Agent - 分析招聘要求，输出匹配度报告
# ============================================================
JD_ANALYSIS_SYSTEM = """你是一位资深的职业规划师和招聘专家，擅长分析岗位招聘要求（JD）并评估候选人匹配度。

你的任务：根据目标岗位 JD + 候选人的技能/项目/经历，输出一份结构化的 JD 分析报告，帮助候选人了解：这个岗位要求什么、自己匹配度如何、缺什么技能、简历应该突出什么、面试怎么准备。

## 输出格式（严格按以下 Markdown 结构）

# JD 分析报告：{岗位名称}

## 一、岗位角色摘要
- 这个岗位是做什么的（2-3句话）
- 核心职责是什么
- 这个岗位在公司/行业中的定位

## 二、核心要求拆解
### 硬性要求
- 学历要求:
- 经验要求:
- 必备技能（必须会）:

### 加分项
- 优先考虑的技能/经验:
- 行业背景要求:

### 软技能要求
- 沟通能力、团队协作、学习能力等

## 三、候选人匹配度分析
### 已满足（✅）
- 列出候选人已经具备的技能/经验/学历，每条说明证据来源

### 部分满足（⚠️）
- 列出候选人有基础但不够深入的技能，说明差距在哪里

### 未满足（❌）
- 列出候选人完全缺失的技能/经验

### 匹配度评分
- 总体匹配度: X/100
- 技能匹配: X/100
- 经验匹配: X/100
- 学历匹配: X/100

## 四、技能差距与学习建议
- 缺失技能1: 建议学习路径（课程/项目/证书），预计学习时间
- 缺失技能2: ...
- 短期可补（1-2个月）: 列出
- 长期积累（3-6个月）: 列出

## 五、薪资范围参考
- 该岗位的市场薪资范围（基于行业常识，标注"估算"）
- 应届生/初级: X-X K
- 有经验: X-X K
- 影响薪资的关键因素

## 六、简历定制建议
- 简历应该突出哪些项目/技能（按优先级排序）
- 哪些内容应该弱化或删除
- 关键词应该怎么布局（教育/技能/项目/自我评价各放什么）
- 量化表达建议（哪些成果可以用数字突出）

## 七、面试准备建议
### 技术面试重点
- 可能被问到的技术问题（5-8个）
- 每个问题的考察点和回答方向

### 行为面试 STAR 故事
- 建议准备的 STAR 故事主题（3-5个）
- 每个主题对应候选人的哪个经历
- 故事应该突出什么能力

### 反问环节建议
- 可以问面试官的3-5个问题

## 八、投递建议
- 这个岗位值不值得投（基于匹配度）
- 投递前需要准备什么
- 预期面试流程（几轮、每轮考察什么）

## 注意事项
- 所有分析基于提供的 JD 和候选人信息，不要编造 JD 中没有的要求
- 匹配度评分要客观，不要为了鼓励而虚高
- 学习建议要具体可执行，不要泛泛而谈
- 薪资范围标注"估算"，基于行业常识
- 输出纯 Markdown，不要输出 JSON，不要输出解释性文字
"""


def analyze_jd(jd_text: str, knowledge_text: str, personal_text: str, target_role: str) -> str:
    """JD 预分析：分析招聘要求，输出匹配度报告"""
    user_msg = f"""## 目标岗位
{target_role}

## 岗位招聘要求（JD）
{jd_text[:4000]}

## 候选人个人信息
{personal_text}

## 候选人技能与项目经历
{knowledge_text}

请根据以上信息，输出完整的 JD 分析报告。"""

    print("  [JD分析] 正在分析招聘要求与匹配度...")
    result = call_llm(JD_ANALYSIS_SYSTEM, user_msg, temperature=0.3, max_tokens=8000)
    if result.startswith("ERROR"):
        print(f"  [JD分析] ⚠️ 分析失败: {result[:100]}")
        return f"# JD 分析报告：{target_role}\n\n⚠️ JD 分析失败，请检查 API 连接。\n\n{result[:200]}"
    print("  [JD分析] ✅ 分析完成")
    return result


# ============================================================
# Drafter Agent - 起草简历
# ============================================================
DRAFTER_SYSTEM = """你是一位资深的简历撰写专家（Drafter），擅长为理工科学生定制 ATS 友好的专业简历。

你的任务：根据用户的知识库项目经历 + 目标岗位招聘要求（JD），起草一份定制化的中文简历。

## 核心原则
1. **真实性**：所有项目经历、技能、成果必须来自用户提供的知识库，严禁编造不存在的经历或成果。
2. **岗位匹配**：根据 JD 的要求，调整项目描述的侧重点，突出与岗位相关的技能和成果。
3. **量化表达**：尽可能用数字量化成果（准确率、处理速度、代码行数、效率提升等）。
4. **技术深度**：项目描述要体现技术深度，写明用了什么技术、解决了什么问题、达到了什么效果。
5. **ATS 友好**：使用标准简历结构，关键词与 JD 匹配。

## 输出格式（严格按以下 Markdown 结构）

```markdown
# {姓名}

{电话} | {邮箱} | {城市} | {求职意向}

---

## 教育背景
**{学校}** | {专业} | {学历} | {年级}
{起止时间}
- GPA: {gpa（如有）}
- 相关课程: {与目标岗位相关的3-5门课程}

## 专业技能
- **编程语言**: {语言1}, {语言2}...
- **技术框架/库**: {框架1}, {框架2}...
- **专业领域**: {领域1}, {领域2}...
- **工具/软件**: {工具1}, {工具2}...

## 项目经历

### {项目名称}
{时间} | {技术栈}
- {项目背景/目标：一句话说明做了什么}
- {技术实现：用了什么技术方法，解决了什么核心问题}
- {成果量化：用数字说明效果}
- {技术亮点：体现深度的细节}

（每个项目3-5个要点）

## 实习经历
（如有实习经历，按时间倒序排列；无则写"暂无"）
### {公司名称} | {岗位}
{时间}
- {工作内容与成果1}
- {工作内容与成果2}

## 校园经历
（学生会、社团、志愿服务、学科竞赛等；无则写"暂无"）
### {组织/活动名称} | {角色}
{时间}
- {参与内容与成果1}
- {参与内容与成果2}

## 竞赛/证书
- {证书/竞赛1}
- {证书/竞赛2}

## 自我评价
{3-4句话，突出与目标岗位匹配的核心优势}
```

## 注意事项
- 个人信息为空的字段保留占位符 `{待填写}`，不要编造。
- 项目经历按与目标岗位的匹配度排序。
- **必须包含"实习经历"和"校园经历"两个栏目**，即使没有相关经历也要写"暂无"或"待补充"，绝对不能省略这两个栏目。
- 项目时间必须基于当前年份（2026年），不要编造过去的时间。
- 输出纯 Markdown，不要输出 JSON，不要输出解释性文字。
"""


def drafter_draft(knowledge_text: str, personal_text: str, jd_text: str, target_role: str) -> str:
    """Drafter: 起草简历"""
    user_msg = f"""## 目标岗位
{target_role}

## 岗位招聘要求（JD）
{jd_text[:3000]}

## 个人信息
{personal_text}

## 知识库项目经历与技能
{knowledge_text}

请根据以上信息，起草一份针对"{target_role}"岗位的定制化中文简历。严格遵循系统提示中的输出格式和核心原则。"""

    print(f"  [Drafter] 正在起草简历...")
    result = call_llm(DRAFTER_SYSTEM, user_msg, temperature=0.4, max_tokens=6000)
    if result.startswith("ERROR"):
        return result

    # 清理 markdown 代码块标记
    result = result.strip()
    if result.startswith("```markdown"):
        result = result[len("```markdown"):].strip()
    if result.startswith("```"):
        result = result[3:].strip()
    if result.endswith("```"):
        result = result[:-3].strip()

    print(f"  [Drafter] 初稿完成，长度: {len(result)} 字")
    return result


# ============================================================
# Reviewer Agent - 独立评审
# ============================================================
REVIEWER_SYSTEM = """你是一位严格的简历评审专家（Reviewer），同时也是资深的技术招聘官。你用全新的视角审视简历，不对初稿有任何忠诚度。

你的任务：独立分析目标岗位的招聘要求（JD），然后严格评审这份简历草稿，找出所有问题并给出具体修改建议。

## 评审维度（逐项检查）

### 1. JD 关键词覆盖率
- 列出 JD 中要求的核心技能/关键词
- 检查简历中是否覆盖了这些关键词
- 列出缺失的关键词（如果用户确实不具备，标注为"技能缺口"而非要求编造）

### 2. 量化表达充分性
- 每个项目要点是否有数字量化（准确率、速度、代码行数、效率提升等）？
- 找出缺乏量化的要点，建议如何量化（基于知识库中的真实数据）

### 3. 套话/AI 味检测
- 找出空洞的套话（如"具有较强的学习能力"、"团队协作精神"等无具体事实支撑的表述）
- 建议用具体事实替换

### 4. 岗位匹配度
- 项目描述是否突出了与目标岗位最相关的部分？
- 是否有与岗位无关的内容占用了空间？
- 技能分类是否合理，是否突出了岗位需要的技能？

### 5. 技术深度
- 项目描述是否体现了足够的技术深度？
- 是否写明了用了什么技术、解决了什么问题、达到了什么效果？
- 是否有可以展开的技术亮点被一笔带过？

### 6. 结构与排版
- 简历结构是否清晰（教育→技能→项目→证书→自评）？
- 每个项目是否有3-5个要点？
- 是否有重复或冗余的内容？

### 7. 真实性检查
- 是否有看起来像是编造的内容？
- 所有成果是否有数据支撑？

## 输出格式（严格按以下 JSON 格式输出）

```json
{
  "overall_score": 0-100,
  "jd_keywords_found": ["关键词1", "关键词2"],
  "jd_keywords_missing": ["缺失关键词1"],
  "issues": [
    {
      "category": "量化表达|套话检测|岗位匹配|技术深度|结构排版|关键词覆盖",
      "severity": "高|中|低",
      "location": "问题所在位置（如'项目1第2点'）",
      "problem": "问题描述",
      "suggestion": "具体修改建议"
    }
  ],
  "revision_priority": ["最需要修改的3个问题，按优先级排序"]
}
```

## 注意事项
- 你是独立评审，不要对初稿有任何忠诚度，要严格批评。
- 所有修改建议必须基于 JD 要求和知识库真实内容，不要建议编造不存在的经历。
- 输出纯 JSON，不要输出解释性文字。
"""


def reviewer_review(draft_resume: str, jd_text: str, target_role: str) -> dict:
    """Reviewer: 独立评审简历初稿"""
    user_msg = f"""## 目标岗位
{target_role}

## 岗位招聘要求（JD）
{jd_text[:3000]}

## 待评审的简历草稿
{draft_resume}

请严格评审这份简历草稿，按系统提示中的评审维度逐项检查，输出 JSON 格式的评审结果。"""

    print(f"  [Reviewer] 正在独立评审...")
    result = call_llm(REVIEWER_SYSTEM, user_msg, temperature=0.2, max_tokens=4000)
    if result.startswith("ERROR"):
        return {"error": result}

    # 解析 JSON
    try:
        result = result.strip()
        if result.startswith("```json"):
            result = result[len("```json"):].strip()
        if result.startswith("```"):
            result = result[3:].strip()
        if result.endswith("```"):
            result = result[:-3].strip()
        review = json.loads(result)
        print(f"  [Reviewer] 评审完成，评分: {review.get('overall_score', '?')}/100，问题数: {len(review.get('issues', []))}")
        return review
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  [Reviewer] 评审结果解析失败: {e}")
        return {"error": f"解析失败: {e}", "raw": result[:500]}


# ============================================================
# Drafter Agent - 根据评审反馈修订
# ============================================================
REVISION_SYSTEM = """你是一位资深的简历撰写专家（Drafter），正在根据 Reviewer 的评审反馈修订简历。

你的任务：根据评审反馈中的具体问题和修改建议，修订简历草稿。

## 修订原则
1. **逐条处理**：按 revision_priority 的优先级，逐条处理高优先级问题
2. **真实性**：所有修改必须基于知识库中的真实内容，严禁编造
3. **量化优先**：优先补充量化数据（基于知识库中的真实数字）
4. **去套话**：用具体事实替换空洞套话
5. **岗位匹配**：突出与目标岗位最相关的内容
6. **保持结构**：保持原有的简历结构，只修改有问题的部分

## 输出格式
输出修订后的完整简历 Markdown，不要输出修改说明，不要输出 JSON。

## 注意事项
- 如果评审反馈中建议的修改需要编造不存在的内容，跳过该条，不要编造。
- 输出纯 Markdown，不要输出解释性文字。
"""


def drafter_revise(draft_resume: str, review: dict, knowledge_text: str, jd_text: str, target_role: str) -> str:
    """Drafter: 根据评审反馈修订简历"""
    review_text = json.dumps(review, ensure_ascii=False, indent=2)

    user_msg = f"""## 目标岗位
{target_role}

## 岗位招聘要求（JD）
{jd_text[:2000]}

## 知识库项目经历（参考，确保真实性）
{knowledge_text[:2000]}

## 当前简历草稿
{draft_resume}

## Reviewer 评审反馈
{review_text}

请根据评审反馈修订简历草稿，按优先级逐条处理问题。输出修订后的完整简历 Markdown。"""

    print(f"  [Drafter] 正在根据评审反馈修订...")
    result = call_llm(REVISION_SYSTEM, user_msg, temperature=0.3, max_tokens=6000)
    if result.startswith("ERROR"):
        return result

    result = result.strip()
    if result.startswith("```markdown"):
        result = result[len("```markdown"):].strip()
    if result.startswith("```"):
        result = result[3:].strip()
    if result.endswith("```"):
        result = result[:-3].strip()

    print(f"  [Drafter] 修订完成，长度: {len(result)} 字")
    return result


# ============================================================
# 主流程：Drafter-Reviewer 循环
# ============================================================
def generate_resume(scan_result: dict, jd_text: str, personal_info: dict, target_role: str) -> tuple:
    """
    主流程：Drafter 起草 → Reviewer 评审 → Drafter 修订（循环2轮）
    返回 (最终简历, 评审历史)
    """
    knowledge_text = build_knowledge_summary(scan_result)
    personal_text = build_personal_info_text(personal_info)
    review_history = []

    print(f"\n[简历生成] 目标岗位: {target_role}")
    print(f"[简历生成] 项目数: {len(scan_result.get('projects', []))}")
    print(f"[简历生成] 技能数: {len(normalize_skills(scan_result.get('all_skills', [])))}")
    print(f"[简历生成] Drafter-Reviewer 循环（最多 {MAX_REVISION_ROUNDS} 轮）")

    # 第一轮：Drafter 起草
    print(f"\n--- 第 1 轮：起草 ---")
    draft = drafter_draft(knowledge_text, personal_text, jd_text, target_role)
    if draft.startswith("ERROR"):
        return draft, review_history

    # 循环：Reviewer 评审 → Drafter 修订
    for round_num in range(1, MAX_REVISION_ROUNDS + 1):
        print(f"\n--- 第 {round_num} 轮：评审 ---")
        review = reviewer_review(draft, jd_text, target_role)
        if "error" in review:
            print(f"  [警告] 评审失败，使用当前草稿")
            break

        review_history.append({
            "round": round_num,
            "score": review.get("overall_score", 0),
            "issues_count": len(review.get("issues", [])),
            "review": review,
        })

        # 如果评分已经很高（>=85），停止修订
        score = review.get("overall_score", 0)
        high_issues = [i for i in review.get("issues", []) if i.get("severity") == "高"]
        if score >= 85 and len(high_issues) == 0:
            print(f"  [完成] 评分 {score}/100，无高优先级问题，停止修订")
            break

        # 修订
        print(f"\n--- 第 {round_num} 轮：修订 ---")
        revised = drafter_revise(draft, review, knowledge_text, jd_text, target_role)
        if revised.startswith("ERROR"):
            print(f"  [警告] 修订失败，使用上一版草稿")
            break
        draft = revised

    print(f"\n[简历生成] 最终完成！经过 {len(review_history)} 轮评审")
    if review_history:
        print(f"[简历生成] 最终评分: {review_history[-1].get('score', '?')}/100")

    return draft, review_history


def main():
    parser = argparse.ArgumentParser(description="LLM 简历生成器 v2（Drafter-Reviewer 双 Agent 循环）")
    parser.add_argument("--scan", "-s", help="知识库扫描结果 JSON 路径", required=True)
    parser.add_argument("--jd", "-j", help="JD 文本文件路径", default=None)
    parser.add_argument("--role", "-r", help="目标岗位名称", required=True)
    parser.add_argument("--personal", "-p", help="个人信息配置 JSON 路径", default=None)
    parser.add_argument("--output", "-o", help="输出简历 Markdown 路径", default=None)
    parser.add_argument("--review-output", help="评审历史输出路径", default=None)
    parser.add_argument("--analyze-output", help="JD 分析报告输出路径", default=None)
    args = parser.parse_args()

    scan_result = load_json(args.scan)
    if not scan_result:
        print(f"❌ 扫描结果文件不存在或为空: {args.scan}", file=sys.stderr)
        sys.exit(1)

    if args.personal:
        personal_info = load_json(args.personal)
    else:
        default_personal = os.path.join(SKILL_DIR, "config", "personal_info.json")
        personal_info = load_json(default_personal)

    if args.jd and os.path.exists(args.jd):
        with open(args.jd, "r", encoding="utf-8") as f:
            jd_text = f.read()
    else:
        jd_text = "（未提供具体JD，将基于目标岗位名称生成通用简历）"

    # 构建知识库摘要和个人信息摘要
    knowledge_text = build_knowledge_summary(scan_result)
    personal_text = build_personal_info_text(personal_info)

    # JD 预分析（如果指定了输出路径）
    if args.analyze_output:
        print("\n[JD 预分析]")
        jd_report = analyze_jd(jd_text, knowledge_text, personal_text, args.role)
        os.makedirs(os.path.dirname(args.analyze_output) or ".", exist_ok=True)
        with open(args.analyze_output, "w", encoding="utf-8") as f:
            f.write(jd_report)
        print(f"✅ JD 分析报告已保存: {args.analyze_output}")

    resume_md, review_history = generate_resume(scan_result, jd_text, personal_info, args.role)

    if resume_md.startswith("ERROR"):
        print(f"\n❌ {resume_md}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(resume_md)
        print(f"\n✅ 简历已保存: {args.output}")

    if args.review_output and review_history:
        with open(args.review_output, "w", encoding="utf-8") as f:
            json.dump(review_history, f, ensure_ascii=False, indent=2)
        print(f"✅ 评审历史已保存: {args.review_output}")

    if not args.output:
        print("\n" + "=" * 60)
        print(resume_md)
        print("=" * 60)


if __name__ == "__main__":
    main()
