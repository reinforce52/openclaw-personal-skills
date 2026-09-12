#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能差距学习路径生成器
- 从 JD 分析报告中解析缺失技能
- 按权重排序
- 用 LLM 生成学习路径计划（知识树+学习阶段+资源推荐+成果检验标准）
- 输出 Markdown 文档，供后续调用 topic-knowledge-base 建库
"""

import os
import sys
import json
import re
import argparse
import requests
from datetime import datetime

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# LLM 配置（复用中南大学 deepseek-v3）
API_BASE = "https://api.chat.csu.edu.cn/v1"
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")  # 从环境变量读取，不要硬编码密钥
MODEL = "deepseek-v3"


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.5, max_tokens: int = 4000) -> str:
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
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  ⚠️ LLM 调用失败: {e}", file=sys.stderr)
        return ""


def parse_missing_skills(jd_report_path: str) -> list:
    """
    从 JD 分析报告中解析缺失技能
    返回: [{"name": "技能名", "detail": "详情", "learn_path": "学习路径", "duration": "预计时间", "weight": 权重}]
    """
    if not os.path.exists(jd_report_path):
        print(f"❌ JD 分析报告不存在: {jd_report_path}", file=sys.stderr)
        return []

    with open(jd_report_path, "r", encoding="utf-8") as f:
        content = f.read()

    skills = []

    # 匹配 "缺失技能N: 技能名" 格式
    pattern = r'\*\*缺失技能\d+:\s*(.+?)\*\*\s*\n\s*- 建议学习路径:\s*(.+?)\n\s*- 预计学习时间:\s*(.+?)(?:\n|$)'
    matches = re.findall(pattern, content, re.DOTALL)

    for i, (name, learn_path, duration) in enumerate(matches, 1):
        name = name.strip()
        learn_path = learn_path.strip()
        duration = duration.strip()
        # 权重：按出现顺序，越靠前越重要
        weight = max(10 - i, 1)
        skills.append({
            "name": name,
            "learn_path": learn_path,
            "duration": duration,
            "weight": weight,
            "source": "JD分析报告",
        })

    # 如果没匹配到，尝试从"未满足"部分提取
    if not skills:
        unmet_section = re.search(r'### 未满足（❌）\n(.+?)(?:\n###|\n##|$)', content, re.DOTALL)
        if unmet_section:
            unmet_text = unmet_section.group(1)
            items = re.findall(r'-\s*\*\*(.+?)\*\*', unmet_text)
            for i, item in enumerate(items[:5], 1):
                skills.append({
                    "name": item.strip(),
                    "learn_path": "",
                    "duration": "",
                    "weight": max(10 - i, 1),
                    "source": "未满足列表",
                })

    # 按权重排序
    skills.sort(key=lambda x: x["weight"], reverse=True)
    return skills


def generate_learning_path(skill_name: str, jd_context: str = "") -> str:
    """
    用 LLM 生成单个技能的学习路径计划
    返回 Markdown 格式的学习路径文档
    """
    system_prompt = """你是一个资深技术学习规划专家，擅长为求职者制定精准的技能学习路径。
你的任务是为指定技能生成一份完整的学习路径计划，包含：
1. 技能概述（是什么、为什么重要、在岗位中的作用）
2. 知识树（先总后细：核心概念→分支领域→具体技术→工具/框架）
3. 学习阶段（入门→基础→进阶→实战，每个阶段列知识点和预计时间）
4. 推荐学习资源（web搜索关键词、视频搜索关键词、经典书籍/课程）
5. 成果检验标准（学完能做什么、能解决什么问题、简历上可以怎么写）
6. 跟目标岗位的关联（这个技能在JD中的权重、掌握后匹配度能提升多少）

要求：
- 内容要具体、可执行，不要空泛
- 知识树要分层清晰，先总后细
- 学习阶段要循序渐进，从易到难
- 资源推荐要实用，给出具体的搜索关键词
- 用中文回答
- 直接输出 Markdown 格式，不要加额外的解释"""

    user_prompt = f"""请为以下技能生成学习路径计划：

技能名称：{skill_name}

JD上下文（可选）：
{jd_context if jd_context else "（无特定JD上下文，按通用技术岗位需求生成）"}

请生成完整的学习路径计划，包含上述6个部分。"""

    print(f"  🤖 正在生成学习路径: {skill_name}...")
    result = call_llm(system_prompt, user_prompt, temperature=0.5, max_tokens=4000)

    if not result:
        # LLM 失败时返回模板
        result = f"""# 学习路径：{skill_name}

## 一、技能概述
（LLM 生成失败，请手动补充）

## 二、知识树
### 核心概念
- 待补充
### 分支领域
- 待补充
### 工具/框架
- 待补充

## 三、学习阶段
### 阶段1：入门
- 待补充
### 阶段2：基础
- 待补充
### 阶段3：进阶
- 待补充
### 阶段4：实战
- 待补充

## 四、推荐学习资源
### Web搜索关键词
- "{skill_name} 教程"
- "{skill_name} 入门"
### 视频搜索关键词
- "{skill_name} B站"
- "{skill_name} YouTube"

## 五、成果检验标准
- 学完能做什么：待补充
- 简历上可以怎么写：待补充

## 六、跟目标岗位的关联
- 在JD中的权重：待补充
- 掌握后匹配度提升：待补充
"""

    return result


def generate_summary(skills: list, output_dir: str) -> str:
    """生成缺失技能汇总文档"""
    summary_path = os.path.join(output_dir, "缺失技能汇总.md")

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"# 缺失技能汇总\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**缺失技能数**: {len(skills)}  \n\n")

        f.write("## 技能列表（按权重排序）\n\n")
        f.write("| 优先级 | 技能名称 | 预计学习时间 | 权重 | 来源 |\n")
        f.write("|---|---|---|---|---|\n")
        for i, skill in enumerate(skills, 1):
            priority = "🔥 最关键" if i == 1 else ("⭐ 重要" if i <= 3 else "📌 一般")
            f.write(f"| {i} | **{skill['name']}** | {skill.get('duration', '待评估')} | {skill['weight']}/10 | {skill['source']} |\n")

        f.write("\n## 推荐学习顺序\n\n")
        f.write("建议按以下顺序学习（先攻克最关键的，再逐步扩展）：\n\n")
        for i, skill in enumerate(skills, 1):
            f.write(f"{i}. **{skill['name']}**（{skill.get('duration', '待评估')}）\n")
            if skill.get("learn_path"):
                f.write(f"   - JD建议路径: {skill['learn_path'][:100]}...\n")
            f.write("\n")

        f.write("## 下一步操作\n\n")
        f.write("1. 查看上方技能列表，选择你想先学的技能（默认推荐第1个）\n")
        f.write("2. 告诉我「帮我学XX技能」，我会调用 topic-knowledge-base 为你建完整知识库\n")
        f.write("3. （可选）如果还需要视频教程，告诉我「还要视频」，我会调用 video-to-knowledge 抓B站/YouTube教程\n")
        f.write("4. 学完后，说「更新简历」，我会重新扫描知识库并生成更强的简历\n\n")

        f.write("## 学习路径文档\n\n")
        for i, skill in enumerate(skills, 1):
            safe_name = skill["name"].replace("/", "_").replace("\\", "_").replace(":", "_")[:40]
            f.write(f"- [{i}. {skill['name']}](学习路径_{safe_name}.md)\n")

    return summary_path


def main():
    parser = argparse.ArgumentParser(description="技能差距学习路径生成器")
    parser.add_argument("--jd-report", "-j", help="JD 分析报告路径（从中解析缺失技能）")
    parser.add_argument("--skill", "-s", help="直接指定技能名称（不解析JD报告）")
    parser.add_argument("--output", "-o", required=True, help="输出目录")
    parser.add_argument("--list", action="store_true", help="只列出缺失技能，不生成学习路径")
    parser.add_argument("--top", type=int, default=3, help="生成前N个技能的学习路径（默认3）")
    parser.add_argument("--resume-dir", help="简历生成目录（自动查找JD分析报告）")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    # 确定技能列表
    skills = []

    if args.jd_report:
        print(f"📄 从 JD 分析报告解析缺失技能: {args.jd_report}")
        skills = parse_missing_skills(args.jd_report)
    elif args.resume_dir:
        # 自动查找简历目录下的 JD 分析报告
        jd_report = None
        for root, dirs, files in os.walk(args.resume_dir):
            for f in files:
                if "JD分析报告" in f and f.endswith(".md"):
                    jd_report = os.path.join(root, f)
                    break
            if jd_report:
                break
        if jd_report:
            print(f"📄 自动找到 JD 分析报告: {jd_report}")
            skills = parse_missing_skills(jd_report)
        else:
            print(f"❌ 未在 {args.resume_dir} 下找到 JD 分析报告", file=sys.stderr)
            sys.exit(1)
    elif args.skill:
        skills = [{
            "name": args.skill,
            "learn_path": "",
            "duration": "",
            "weight": 10,
            "source": "手动指定",
        }]
    else:
        print("❌ 请指定 --jd-report 或 --skill 或 --resume-dir", file=sys.stderr)
        sys.exit(1)

    if not skills:
        print("❌ 未解析到缺失技能", file=sys.stderr)
        sys.exit(1)

    print(f"\n✅ 解析到 {len(skills)} 个缺失技能:")
    for i, skill in enumerate(skills, 1):
        print(f"  {i}. [{skill['weight']}/10] {skill['name']} ({skill.get('duration', '待评估')})")

    # 只列出，不生成
    if args.list:
        print(f"\n📋 缺失技能列表（共 {len(skills)} 个）")
        return

    # 生成汇总文档
    print(f"\n📝 生成缺失技能汇总文档...")
    summary_path = generate_summary(skills, args.output)
    print(f"  ✅ 汇总文档: {summary_path}")

    # 为 Top N 技能生成学习路径
    top_skills = skills[:args.top]
    print(f"\n🚀 为 Top {len(top_skills)} 技能生成学习路径...")

    for i, skill in enumerate(top_skills, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(top_skills)}] {skill['name']}")
        print(f"{'='*60}")

        # 生成学习路径
        jd_context = f"JD建议学习路径: {skill.get('learn_path', '')}\n预计学习时间: {skill.get('duration', '')}" if skill.get("learn_path") else ""
        learning_path = generate_learning_path(skill["name"], jd_context)

        # 保存
        safe_name = skill["name"].replace("/", "_").replace("\\", "_").replace(":", "_")[:40]
        path_file = os.path.join(args.output, f"学习路径_{safe_name}.md")
        with open(path_file, "w", encoding="utf-8") as f:
            f.write(learning_path)

        print(f"  ✅ 学习路径已保存: {path_file}")
        print(f"  📏 文档长度: {len(learning_path)} 字")

    # 完成
    print(f"\n\n{'='*60}")
    print(f"✅ 技能差距学习路径生成完成！")
    print(f"{'='*60}")
    print(f"输出目录: {args.output}")
    print(f"汇总文档: {summary_path}")
    print(f"\n💡 下一步：")
    print(f"  1. 打开「缺失技能汇总.md」查看所有缺失技能")
    print(f"  2. 选择你想先学的技能（默认推荐第1个）")
    print(f"  3. 告诉我「帮我学XX技能」，我会调用 topic-knowledge-base 建完整知识库")
    print(f"  4. 学完后说「更新简历」，重新生成更强的简历")


if __name__ == "__main__":
    main()
