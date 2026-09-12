#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
岗位 AI 匹配打分器
- 基于用户的简历/技能/项目经历，给每个岗位打分
- 多维度评估：技能匹配、经验匹配、学历匹配、项目匹配
- 输出匹配度排序 + 差距分析 + 投递建议
"""

import os
import sys
import json
import time
import requests
import argparse

# ============================================================
# API 配置（中南大学 deepseek-v3）
# ============================================================
API_BASE = "https://api.chat.csu.edu.cn/v1"
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")  # 从环境变量读取，不要硬编码密钥
MODEL = "deepseek-v3"

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.3, max_tokens: int = 4000) -> str:
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
        resp = requests.post(f"{API_BASE}/chat/completions", headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        result = resp.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"ERROR: {str(e)[:300]}"


# ============================================================
# 匹配打分系统提示词
# ============================================================
MATCHER_SYSTEM = """你是一位资深的职业规划师和招聘专家，擅长评估候选人与岗位的匹配度。

你的任务：根据候选人的背景（技能、项目、学历、经验）和岗位信息，给出客观的匹配度评分和分析。

## 评分维度（每项 0-100 分）

1. **技能匹配度**：岗位要求的核心技能，候选人掌握了多少
2. **经验匹配度**：岗位要求的工作经验/项目经验，候选人是否满足
3. **学历匹配度**：岗位要求的学历，候选人是否满足或超出
4. **项目匹配度**：候选人的项目经历与岗位业务场景的相关性
5. **总体匹配度**：综合以上维度的加权评分（技能40% + 经验25% + 项目20% + 学历15%）

## 输出格式（严格按以下 JSON 格式）

{
  "overall_score": 85,
  "skill_match": 90,
  "experience_match": 75,
  "education_match": 100,
  "project_match": 80,
  "matched_skills": ["Python", "OpenCV", "YOLO"],
  "missing_skills": ["Halcon", "C++", "3D视觉"],
  "strengths": ["有完整的机器视觉项目经验", "掌握传统CV和深度学习选型逻辑"],
  "gaps": ["缺乏工业视觉项目经验", "C++能力不足"],
  "salary_fit": "候选人当前能力对应薪资约 8-12K，岗位薪资 10-15K，基本匹配",
  "recommendation": "强烈推荐投递",
  "recommendation_level": "high",
  "interview_focus": ["可能被问到C++能力", "工业视觉项目经验", "Halcon使用经历"],
  "preparation_advice": "投递前补充C++基础，准备1-2个工业视觉场景的项目描述"
}

## 注意事项
- 评分要客观，不要为了鼓励而虚高
- 应届生/在校生的经验匹配度可以适当放宽（看潜力而非已有经验）
- 缺失技能要具体，不要泛泛而谈
- 投递建议分三档：high（强烈推荐）、medium（可以尝试）、low（不建议，差距太大）
- 只输出 JSON，不要输出解释性文字，不要输出 Markdown 代码块标记
"""


def load_user_profile(scan_result_path: str, personal_info_path: str) -> dict:
    """加载用户画像（技能+项目+个人信息）"""
    profile = {"skills": [], "projects": [], "personal": {}}

    # 加载扫描结果
    if scan_result_path and os.path.exists(scan_result_path):
        with open(scan_result_path, "r", encoding="utf-8") as f:
            scan = json.load(f)
        profile["skills"] = scan.get("all_skills", [])
        profile["projects"] = scan.get("projects", [])

    # 加载个人信息
    if personal_info_path and os.path.exists(personal_info_path):
        with open(personal_info_path, "r", encoding="utf-8") as f:
            profile["personal"] = json.load(f)

    return profile


def build_user_profile_text(profile: dict) -> str:
    """把用户画像整理成 LLM 可读的文本"""
    lines = []

    # 个人信息
    personal = profile.get("personal", {})
    if personal:
        lines.append("## 候选人基本信息")
        if personal.get("name"):
            lines.append(f"- 姓名: {personal['name']}")
        edu = personal.get("education", {})
        if edu:
            lines.append(f"- 学历: {edu.get('degree', '')} / {edu.get('school', '')} / {edu.get('major', '')} / {edu.get('grade', '')}")
            lines.append(f"- 时间: {edu.get('start_date', '')} ~ {edu.get('end_date', '')}")
        if personal.get("languages"):
            lines.append(f"- 语言: {', '.join(personal['languages'])}")
        if personal.get("certifications"):
            lines.append(f"- 证书: {', '.join(personal['certifications'])}")

    # 技能
    skills = profile.get("skills", [])
    if skills:
        lines.append(f"\n## 技能关键词（共{len(skills)}个）")
        lines.append(", ".join(skills[:50]))

    # 项目经历
    projects = profile.get("projects", [])
    if projects:
        lines.append(f"\n## 项目经历（共{len(projects)}个）")
        for i, p in enumerate(projects, 1):
            lines.append(f"\n### 项目{i}: {p.get('name', '未知')}")
            lines.append(f"- 状态: {p.get('status', '未知')}")
            lines.append(f"- 技术栈: {', '.join(p.get('tech_stack', [])[:15])}")
            desc = p.get("description", "")
            lines.append(f"- 简介: {desc[:300]}")
            achievements = p.get("achievements", [])
            if achievements:
                lines.append("- 成果:")
                for a in achievements[:3]:
                    lines.append(f"  - {a}")

    return "\n".join(lines)


def match_job(job: dict, user_profile_text: str) -> dict:
    """给单个岗位打分"""
    job_text = f"""## 岗位信息
- 岗位名称: {job.get('job_name', '')}
- 公司: {job.get('company_name', '')} ({job.get('company_industry', '')}, {job.get('company_scale', '')})
- 薪资: {job.get('salary', '')}
- 地点: {job.get('city', '')}·{job.get('district', '')}
- 经验要求: {job.get('experience', '')}
- 学历要求: {job.get('degree', '')}
- 岗位标签: {', '.join(job.get('job_labels', []))}
- 岗位链接: {job.get('job_url', '')}
"""

    user_msg = f"""## 候选人画像
{user_profile_text}

{job_text}

请根据以上信息，给出这个岗位与候选人的匹配度评分。只输出 JSON。"""

    result = call_llm(MATCHER_SYSTEM, user_msg, temperature=0.2, max_tokens=2000)

    # 解析 JSON
    try:
        # 清理可能的 Markdown 代码块标记
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1] if "\n" in result else result
            if result.endswith("```"):
                result = result.rsplit("```", 1)[0]
            result = result.strip()

        match_result = json.loads(result)
        match_result["job"] = job
        return match_result
    except Exception as e:
        print(f"  ⚠️ 解析评分失败: {str(e)[:80]}")
        print(f"  原始结果: {result[:200]}")
        return {
            "overall_score": 0,
            "skill_match": 0,
            "experience_match": 0,
            "education_match": 0,
            "project_match": 0,
            "error": str(e)[:100],
            "raw_result": result[:500],
            "job": job,
        }


def match_jobs(jobs: list, user_profile_text: str, max_jobs: int = None) -> list:
    """给多个岗位打分，按匹配度排序"""
    if max_jobs:
        jobs = jobs[:max_jobs]

    results = []
    total = len(jobs)

    for i, job in enumerate(jobs, 1):
        print(f"[{i}/{total}] 评估: {job.get('job_name', '')} @ {job.get('company_name', '')}")
        result = match_job(job, user_profile_text)
        score = result.get("overall_score", 0)
        level = result.get("recommendation_level", "unknown")
        print(f"  → 匹配度: {score}/100 ({level})")
        results.append(result)

        # 限流
        if i < total:
            time.sleep(1)

    # 按匹配度排序
    results.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
    return results


def print_results(results: list, top_n: int = 10):
    """打印匹配结果"""
    print("\n" + "=" * 90)
    print(f"岗位匹配度排名（共 {len(results)} 个岗位，展示前 {min(top_n, len(results))} 个）")
    print("=" * 90)

    for i, r in enumerate(results[:top_n], 1):
        job = r.get("job", {})
        score = r.get("overall_score", 0)
        level = r.get("recommendation_level", "")
        level_icon = {"high": "🔥", "medium": "✅", "low": "⚠️"}.get(level, "❓")

        print(f"\n{i}. {level_icon} [{score}/100] {job.get('job_name', '')} | {job.get('salary', '')}")
        print(f"   公司: {job.get('company_name', '')} ({job.get('company_industry', '')})")
        print(f"   地点: {job.get('city', '')}·{job.get('district', '')} | 经验: {job.get('experience', '')} | 学历: {job.get('degree', '')}")
        print(f"   技能匹配: {r.get('skill_match', 0)} | 经验匹配: {r.get('experience_match', 0)} | 项目匹配: {r.get('project_match', 0)} | 学历匹配: {r.get('education_match', 0)}")

        if r.get("matched_skills"):
            print(f"   ✅ 已匹配技能: {', '.join(r['matched_skills'][:8])}")
        if r.get("missing_skills"):
            print(f"   ❌ 缺失技能: {', '.join(r['missing_skills'][:8])}")
        if r.get("strengths"):
            print(f"   💪 优势: {'; '.join(r['strengths'][:3])}")
        if r.get("gaps"):
            print(f"   📉 差距: {'; '.join(r['gaps'][:3])}")
        if r.get("recommendation"):
            print(f"   💡 建议: {r['recommendation']}")
        if r.get("preparation_advice"):
            print(f"   📝 准备: {r['preparation_advice']}")
        print(f"   🔗 链接: {job.get('job_url', '')}")

    # 统计
    high = sum(1 for r in results if r.get("recommendation_level") == "high")
    medium = sum(1 for r in results if r.get("recommendation_level") == "medium")
    low = sum(1 for r in results if r.get("recommendation_level") == "low")
    avg_score = sum(r.get("overall_score", 0) for r in results) / len(results) if results else 0

    print(f"\n{'=' * 90}")
    print(f"统计: 🔥强烈推荐 {high} 个 | ✅可以尝试 {medium} 个 | ⚠️不建议 {low} 个 | 平均匹配度 {avg_score:.1f}/100")
    print("=" * 90)


def main():
    parser = argparse.ArgumentParser(description="岗位 AI 匹配打分器")
    parser.add_argument("--jobs", "-j", required=True, help="岗位列表 JSON 文件路径（boss_client.py 的输出）")
    parser.add_argument("--scan", "-s", default=None, help="知识库扫描结果 JSON 路径")
    parser.add_argument("--personal", "-p", default=None, help="个人信息配置 JSON 路径")
    parser.add_argument("--output", "-o", default=None, help="匹配结果输出路径")
    parser.add_argument("--top", "-t", type=int, default=10, help="展示前 N 个岗位")
    parser.add_argument("--max-jobs", type=int, default=None, help="最多评估多少个岗位（默认全部）")
    args = parser.parse_args()

    # 默认路径
    if not args.scan:
        args.scan = os.path.join(SKILL_DIR, "scan_result.json")
    if not args.personal:
        args.personal = os.path.join(SKILL_DIR, "config", "personal_info.json")

    # 加载岗位列表
    if not os.path.exists(args.jobs):
        print(f"❌ 岗位文件不存在: {args.jobs}", file=sys.stderr)
        sys.exit(1)

    with open(args.jobs, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    print(f"📋 加载到 {len(jobs)} 个岗位")

    # 加载用户画像
    profile = load_user_profile(args.scan, args.personal)
    profile_text = build_user_profile_text(profile)
    print(f"👤 用户画像: {len(profile.get('skills', []))} 个技能, {len(profile.get('projects', []))} 个项目")

    # 匹配打分
    print(f"\n🔍 开始 AI 匹配打分...")
    results = match_jobs(jobs, profile_text, max_jobs=args.max_jobs)

    # 打印结果
    print_results(results, top_n=args.top)

    # 保存结果
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        # 保存时去掉 job 字段的冗余，保留关键信息
        save_results = []
        for r in results:
            item = {k: v for k, v in r.items() if k != "job"}
            item["job_name"] = r.get("job", {}).get("job_name", "")
            item["company"] = r.get("job", {}).get("company_name", "")
            item["salary"] = r.get("job", {}).get("salary", "")
            item["url"] = r.get("job", {}).get("job_url", "")
            save_results.append(item)

        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(save_results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 匹配结果已保存: {args.output}")


if __name__ == "__main__":
    main()
