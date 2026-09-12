#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_knowledge_graph.py - 生成知识谱系总图（Mermaid mindmap + 知识关联图）
输入: deep_dive.json 或 summary.json（含 knowledge_points）
输出: _知识谱系总图.md（Mermaid mindmap 全景图 + 知识关联图 + 学习路径）
"""

import os
import sys
import json
import argparse
from pathlib import Path


def build_mindmap(data: dict, video_title: str = "视频课程") -> str:
    """生成 Mermaid mindmap（视频→知识点→细分概念）"""
    knowledge_points = data.get("knowledge_points", [])
    topic = data.get("topic", "未知主题")

    lines = []
    lines.append("```mermaid")
    lines.append("mindmap")
    lines.append(f"  root(({topic}))")

    # 按重要性分组
    high = [kp for kp in knowledge_points if kp.get("importance") == "高"]
    medium = [kp for kp in knowledge_points if kp.get("importance") == "中"]
    low = [kp for kp in knowledge_points if kp.get("importance") == "低"]

    def add_point(kp, indent=4):
        point = kp.get("point", "?")
        # 转义特殊字符
        point = point.replace("(", "（").replace(")", "）")
        lines.append(f"{' ' * indent}{point}")
        # 细分概念
        sub_points = kp.get("sub_points", [])
        for sp in sub_points[:3]:  # 每个知识点最多3个细分概念，避免图太大
            sp = sp.replace("(", "（").replace(")", "）")
            lines.append(f"{' ' * (indent+2)}{sp}")

    if high:
        lines.append("    核心知识点")
        for kp in high:
            add_point(kp, indent=6)

    if medium:
        lines.append("    重要知识点")
        for kp in medium:
            add_point(kp, indent=6)

    if low:
        lines.append("    了解知识点")
        for kp in low:
            add_point(kp, indent=6)

    lines.append("```")
    return "\n".join(lines)


def build_relation_graph(data: dict) -> str:
    """生成知识关联图（知识点之间的前置/后续/关联关系）"""
    knowledge_points = data.get("knowledge_points", [])
    point_names = [kp.get("point", "") for kp in knowledge_points]

    lines = []
    lines.append("```mermaid")
    lines.append("graph LR")

    # 节点定义
    for i, kp in enumerate(knowledge_points):
        point = kp.get("point", f"知识点{i}")
        # 节点标签最多12字，超出加省略号（避免关系图过宽，完整名称见索引表）
        short = point[:12] + "…" if len(point) > 12 else point
        short = short.replace("(", "（").replace(")", "）").replace('"', "'")
        node_id = f"P{i}"
        lines.append(f'    {node_id}["{short}"]')

    # 关系连线
    for i, kp in enumerate(knowledge_points):
        point = kp.get("point", "")
        node_id = f"P{i}"

        # 前置知识（指向当前知识点）
        for pre in kp.get("prerequisites", []):
            # 查找前置知识点是否在列表中
            for j, other in enumerate(knowledge_points):
                if j != i and (other.get("point", "") in pre or pre in other.get("point", "")):
                    lines.append(f"    P{j} -->|前置| {node_id}")
                    break

        # 后续知识（从当前知识点指出）
        for fol in kp.get("follow_ups", []):
            for j, other in enumerate(knowledge_points):
                if j != i and (other.get("point", "") in fol or fol in other.get("point", "")):
                    lines.append(f"    {node_id} -->|后续| P{j}")
                    break

    lines.append("```")
    return "\n".join(lines)


def build_learning_path(data: dict) -> str:
    """生成学习路径（按知识脉络排序）"""
    knowledge_chain = data.get("knowledge_chain", "")
    knowledge_points = data.get("knowledge_points", [])
    learning_suggestions = data.get("learning_suggestions", "")

    lines = []
    lines.append("## 📚 学习路径")
    lines.append("")
    lines.append("### 知识发展脉络")
    lines.append(f"> {knowledge_chain}")
    lines.append("")
    lines.append("### 推荐学习顺序")
    lines.append("")

    # 按重要性和前置关系排序
    sorted_points = sorted(
        knowledge_points,
        key=lambda x: {"高": 0, "中": 1, "低": 2}.get(x.get("importance", "中"), 1)
    )

    for i, kp in enumerate(sorted_points, 1):
        point = kp.get("point", "?")
        timestamp = kp.get("timestamp", "00:00")
        prerequisites = kp.get("prerequisites", [])
        follow_ups = kp.get("follow_ups", [])

        lines.append(f"**第{i}步：{point}**（视频 {timestamp}）")
        if prerequisites:
            lines.append(f"- 前置知识：{', '.join(prerequisites[:3])}")
        if follow_ups:
            lines.append(f"- 后续延伸：{', '.join(follow_ups[:3])}")
        lines.append("")

    lines.append("### 学习建议")
    lines.append(f"> {learning_suggestions}")
    lines.append("")

    return "\n".join(lines)


def build_knowledge_graph(input_path: str, output_path: str = None, video_title: str = None):
    """主流程：读取 deep_dive/summary → 生成知识谱系总图"""
    if not os.path.exists(input_path):
        return {"error": f"输入文件不存在: {input_path}"}

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    topic = data.get("topic", data.get("topic_suggestion", "未知主题"))
    video_overview = data.get("video_overview", data.get("one_sentence_summary", ""))
    knowledge_points = data.get("knowledge_points", [])

    print(f"[知识谱系] 主题: {topic}")
    print(f"[知识谱系] 知识点数量: {len(knowledge_points)}")

    # 生成各部分
    mindmap = build_mindmap(data, video_title or topic)
    relation_graph = build_relation_graph(data)
    learning_path = build_learning_path(data)

    # 组装完整文档
    content = f"""---
category: "{topic}"
tags: ["知识谱系", "思维导图", "Mermaid", "视频学习"]
source: "视频转写 + web深度搜索"
created: "{__import__('datetime').datetime.now().strftime('%Y-%m-%d')}"
---

# {topic} - 知识谱系总图

> 基于视频内容 + web深度搜索自动生成的知识谱系，包含全景思维导图、知识关联图和学习路径。

---

## 🎯 视频内容概述

{video_overview}

---

## 🗺️ 一、全景知识谱系（Mindmap）

{mindmap}

---

## 🔗 二、知识关联图（前置/后续关系）

{relation_graph}

---

{learning_path}

---

## 📊 三、知识点索引

| # | 知识点 | 重要性 | 视频时间 | 前置知识 | 后续延伸 |
|---|--------|--------|----------|----------|----------|
"""

    for i, kp in enumerate(knowledge_points, 1):
        point = kp.get("point", "?")
        importance = kp.get("importance", "中")
        timestamp = kp.get("timestamp", "00:00")
        prerequisites = ", ".join(kp.get("prerequisites", [])[:2]) or "-"
        follow_ups = ", ".join(kp.get("follow_ups", [])[:2]) or "-"
        content += f"| {i} | [[知识点/{point}|{point}]] | {importance} | {timestamp} | {prerequisites} | {follow_ups} |\n"

    content += f"""
---

## 💡 四、使用说明

1. **先看全景图**：了解整个知识体系的结构和脉络
2. **按学习路径顺序学**：从核心知识点开始，逐步延伸
3. **每个知识点独立成篇**：点击索引中的知识点链接，查看9段式深度笔记
4. **关注知识关联**：注意前置/后续关系，确保学习顺序正确
5. **配合视频回看**：每个知识点标注了视频时间戳，可点击回看

---

> 📌 本图谱由 video-to-knowledge skill v2 自动生成，基于视频转写 + web深度搜索 + LLM知识关联分析。
"""

    # 保存
    if output_path is None:
        output_path = os.path.join(os.path.dirname(input_path), "_知识谱系总图.md")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[知识谱系] 完成！保存到: {output_path}")
    return {"output": output_path, "points": len(knowledge_points)}


def main():
    parser = argparse.ArgumentParser(description="生成知识谱系总图")
    parser.add_argument("input_path", help="deep_dive.json 或 summary.json 路径")
    parser.add_argument("--output", "-o", default=None, help="输出 _知识谱系总图.md 路径")
    parser.add_argument("--video-title", default=None, help="视频标题（用于mindmap根节点）")
    args = parser.parse_args()

    result = build_knowledge_graph(args.input_path, args.output, args.video_title)
    if "error" in result:
        print(f"错误: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
