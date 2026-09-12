#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Obsidian 写入模块 v2 - 两层笔记结构
- 视频总览笔记: 视频笔记/<视频名>.md（知识点列表+时间戳+链接到知识点笔记）
- 知识点独立笔记: 知识点/<知识点名>.md（9段式深度结构：定义/定理/例题/易错/关联/自测）
- 知识谱系总图: _知识谱系总图.md（Mermaid mindmap）
- 复习清单: _复习清单.md（间隔重复）
支持读取 summary.json（v1）和 deep_dive.json（v2，含web搜索扩展）
"""

import os
import sys
import json
import argparse
import re
from datetime import datetime, timedelta
from pathlib import Path

# ============ 配置 ============
OBSIDIAN_BASE = r"E:\obsidian\rein"


def sanitize_filename(name: str) -> str:
    """清理文件名中的非法字符（Windows + Obsidian 安全）"""
    name = re.sub(r'[\\/:*?"<>|#]', '_', name)
    name = re.sub(r'\s+', ' ', name)
    name = name.strip().strip('.')
    return name[:80] if len(name) > 80 else name


def load_data(input_path: str) -> dict:
    """加载 summary.json 或 deep_dive.json"""
    if not os.path.exists(input_path):
        return {"error": f"文件不存在: {input_path}"}
    with open(input_path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_v2_deep_dive(data: dict) -> bool:
    """判断是否是 v2 deep_dive 格式（含 enhanced 字段）"""
    points = data.get("knowledge_points", [])
    if points and "enhanced" in points[0]:
        return True
    return False


def _name_similarity(a: str, b: str) -> float:
    """两个名称的相似度：基于字符重合度（0-1）"""
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    return inter / min(len(sa), len(sb))


def link_or_text(item: str, all_points: list) -> str:
    """关联项智能匹配：匹配到本主题实际知识点→wikilink；匹配不到→纯文本（避免Obsidian死链）"""
    item = item.strip()
    if not item:
        return ""
    # 1. 精确匹配
    for p in all_points:
        if item == p:
            return f"[[知识点/{p}|{p}]]"
    # 2. 包含匹配（互为子串）
    for p in all_points:
        if item in p or p in item:
            return f"[[知识点/{p}|{item}]]"
    # 3. 字符相似度匹配（阈值0.7）
    best, best_score = None, 0.0
    for p in all_points:
        s = _name_similarity(item, p)
        if s > best_score:
            best, best_score = p, s
    if best and best_score >= 0.7:
        return f"[[知识点/{best}|{item}]]"
    # 4. 匹配不到：纯文本，标注为拓展（本库暂无独立笔记，不产生死链）
    return f"{item}（拓展·本库暂无独立笔记）"


def generate_knowledge_point_note(kp: dict, topic: str, video_title: str, video_url: str, platform: str = "unknown", all_points: list = None) -> str:
    """生成单个知识点的9段式深度笔记。all_points: 本主题全部知识点名（用于关联智能匹配，避免死链）"""
    if all_points is None:
        all_points = []
    point = kp.get("point", "未知知识点")
    detail = kp.get("detail", "")
    timestamp = kp.get("timestamp", "00:00")
    importance = kp.get("importance", "中")
    prerequisites = kp.get("prerequisites", [])
    follow_ups = kp.get("follow_ups", [])
    related = kp.get("related", [])
    sub_points = kp.get("sub_points", [])
    key_formulas = kp.get("key_formulas", [])
    examples = kp.get("examples", [])
    enhanced = kp.get("enhanced", {})

    # v2 扩展内容
    definition_enhanced = enhanced.get("definition_enhanced", "")
    application_scenarios = enhanced.get("application_scenarios", [])
    common_mistakes = enhanced.get("common_mistakes", [])
    extended_knowledge = enhanced.get("extended_knowledge", "")
    learning_path = enhanced.get("learning_path", "")
    references = enhanced.get("references", [])

    # 视频总览文件名（用于双向跳转）
    overview_filename = sanitize_filename(f"{platform}_{video_title}")
    overview_link = f"[[视频笔记/{overview_filename}|📺 返回视频总览]]"

    note = f"""---
category: "{topic}"
tags: ["知识点", "{point}", "视频学习"]
source: ["视频: {video_title}", "web深度搜索"]
importance: "{importance}"
video_timestamp: "{timestamp}"
created: "{datetime.now().strftime('%Y-%m-%d')}"
---

# {point}

{overview_link}

> 视频讲解位置：**{timestamp}** — [{video_title}]({video_url})

---

## 📌 一、核心定义与原理

{detail}

"""

    if definition_enhanced:
        note += f"### 📖 定义补充（web搜索扩展）\n{definition_enhanced}\n\n"

    if key_formulas:
        note += "### 📐 关键公式\n"
        for f in key_formulas:
            note += f"- {f}\n"
        note += "\n"

    note += "## 🧩 二、细分概念\n\n"
    if sub_points:
        for i, sp in enumerate(sub_points, 1):
            note += f"{i}. **{sp}**\n"
    else:
        note += "- （视频中未明确细分）\n"
    note += "\n"

    note += "## 📝 三、典型例题与应用\n\n"
    if examples:
        for i, ex in enumerate(examples, 1):
            note += f"**例{i}**：{ex}\n\n"
    else:
        note += "- （视频中未讲到具体例题）\n\n"

    if application_scenarios:
        note += "### 🌐 应用场景（web搜索扩展）\n"
        for app in application_scenarios:
            note += f"- {app}\n"
        note += "\n"

    note += "## ⚠️ 四、易错点与常见错误\n\n"
    if common_mistakes:
        for i, m in enumerate(common_mistakes, 1):
            note += f"{i}. {m}\n"
    else:
        note += "- （暂无明确易错点，学习时注意概念辨析）\n"
    note += "\n"

    if extended_knowledge:
        note += f"## 🚀 五、拓展知识\n\n{extended_knowledge}\n\n"

    note += "## 🔗 六、知识关联\n\n"
    note += "### 📚 前置知识（学习本知识点需要先掌握）\n"
    if prerequisites:
        for p in prerequisites:
            note += f"- {link_or_text(p, all_points)}\n"
    else:
        note += "- （无明确前置知识）\n"

    note += "\n### ➡️ 后续延伸（学完后可以继续学习）\n"
    if follow_ups:
        for f in follow_ups:
            note += f"- {link_or_text(f, all_points)}\n"
    else:
        note += "- （无明确后续延伸）\n"

    note += "\n### 🔄 关联知识点\n"
    if related:
        for r in related:
            note += f"- {link_or_text(r, all_points)}\n"
    else:
        note += "- （无明确关联知识点）\n"
    note += "\n"

    note += "## ✅ 七、掌握检验（自测清单）\n\n"
    note += f"- [ ] 能复述 {point} 的核心定义\n"
    note += f"- [ ] 理解 {point} 的原理和推导过程\n"
    if key_formulas:
        note += f"- [ ] 能熟练运用相关公式\n"
    if application_scenarios:
        note += f"- [ ] 能举出至少1个应用场景\n"
    note += f"- [ ] 能区分 {point} 与相关概念的区别\n"
    note += f"- [ ] 能独立完成视频中的相关例题\n\n"

    if learning_path:
        note += f"## 📖 八、学习建议\n\n{learning_path}\n\n"

    note += "## 📚 九、参考来源\n\n"
    note += f"- **视频**：[{video_title}]({video_url})（{timestamp}）\n"
    if references:
        for i, ref in enumerate(references, 1):
            title = ref.get("title", f"参考资料{i}")
            url = ref.get("url", "")
            if url:
                note += f"- **web扩展{i}**：[{title}]({url})\n"
            else:
                note += f"- **web扩展{i}**：{title}\n"
    note += "\n---\n"
    note += f"> 📌 本笔记由 video-to-knowledge skill v2 自动生成，基于视频转写 + web深度搜索 + LLM知识关联分析。\n"

    return note


def _fmt_duration(d) -> str:
    """把秒数（可能是字符串/浮点）格式化为 'X分Y秒'"""
    try:
        sec = int(float(d))
        if sec >= 3600:
            return f"{sec//3600}时{sec%3600//60}分{sec%60}秒"
        if sec >= 60:
            return f"{sec//60}分{sec%60}秒"
        return f"{sec}秒"
    except (ValueError, TypeError):
        return str(d)


def generate_video_overview_note(data: dict, topic: str) -> str:
    """生成视频总览笔记（知识点列表+时间戳+链接到知识点笔记）"""
    metadata = data.get("metadata", {})
    title = metadata.get("title", "未知视频")
    uploader = metadata.get("uploader", "未知")
    platform = metadata.get("platform", "unknown")
    duration = metadata.get("duration", "0")
    url = metadata.get("url", "")
    video_id = metadata.get("video_id", "")

    one_sentence = data.get("one_sentence_summary", "")
    video_overview = data.get("video_overview", "")
    knowledge_chain = data.get("knowledge_chain", "")
    knowledge_points = data.get("knowledge_points", [])
    key_timestamps = data.get("key_timestamps", [])
    learning_suggestions = data.get("learning_suggestions", "")

    note = f"""---
title: "{title}"
platform: "{platform}"
uploader: "{uploader}"
duration: "{duration}秒"
url: "{url}"
video_id: "{video_id}"
topic: "{topic}"
created: "{datetime.now().strftime('%Y-%m-%d %H:%M')}"
tags: ["视频总览", "{topic}"]
---

# {title}

## 📌 基本信息
- **平台**: {platform}
- **UP主**: {uploader}
- **时长**: {_fmt_duration(duration)}
- **原始链接**: [{url}]({url})

## 💡 一句话总结
{one_sentence}

"""

    if video_overview:
        note += f"## 📖 视频内容概述\n{video_overview}\n\n"

    if knowledge_chain:
        note += f"## 🔗 知识发展脉络\n> {knowledge_chain}\n\n"

    # 核心知识点快速跳转（简洁列表，手机端易点击，直接跳深度笔记）
    note += "## 🎯 核心知识点（点击跳转深度笔记）\n\n"
    for i, kp in enumerate(knowledge_points, 1):
        point = kp.get("point", "?")
        importance = kp.get("importance", "中")
        detail = kp.get("detail", "")
        # 取detail前40字作为一句话提示
        brief = detail[:40] + "…" if len(detail) > 40 else detail
        imp_icon = "🔴" if importance == "高" else ("🟡" if importance == "中" else "⚪")
        note += f"{imp_icon} **{i}. [[知识点/{point}|{point}]]** — {brief}\n"
    note += "\n"

    note += "## 📋 知识点详细索引\n\n"
    note += "| # | 知识点 | 重要性 | 视频时间 | 核心内容 |\n"
    note += "|---|--------|--------|----------|----------|\n"

    for i, kp in enumerate(knowledge_points, 1):
        point = kp.get("point", "?")
        importance = kp.get("importance", "中")
        timestamp = kp.get("timestamp", "00:00")
        detail = kp.get("detail", "")[:60] + "..." if len(kp.get("detail", "")) > 60 else kp.get("detail", "")
        note += f"| {i} | [[知识点/{point}|{point}]] | {importance} | {timestamp} | {detail} |\n"

    note += "\n"

    if key_timestamps:
        note += "## ⏱️ 关键时间点（点击回看）\n\n"
        for ts in key_timestamps:
            time_str = ts.get("time", "00:00")
            content = ts.get("content", "")
            if "youtube" in url or "youtu.be" in url:
                parts = time_str.split(":")
                if len(parts) == 2:
                    seconds = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                else:
                    seconds = 0
                link = f"{url}&t={seconds}s" if "?" in url else f"{url}?t={seconds}s"
                note += f"- **[{time_str}]({link})**: {content}\n"
            else:
                note += f"- **{time_str}**: {content} （[回看视频]({url})）\n"
        note += "\n"

    if learning_suggestions:
        note += f"## 📚 学习建议\n{learning_suggestions}\n\n"

    note += "---\n"
    note += f"> 📌 本视频共拆解出 **{len(knowledge_points)} 个知识点**，每个知识点都有独立的9段式深度笔记。\n"

    return note


def generate_review_list(topic_dir: str, knowledge_points: list, topic: str):
    """生成复习清单（间隔重复：1/3/7/15天）"""
    review_path = os.path.join(topic_dir, "_复习清单.md")

    today = datetime.now()
    intervals = [1, 3, 7, 15]

    content = f"""---
topic: "{topic}"
type: "复习清单"
created: "{today.strftime('%Y-%m-%d')}"
---

# {topic} - 复习清单

> 基于间隔重复法（1/3/7/15天），自动生成复习计划。

## 📅 复习日程

| 复习日期 | 间隔 | 待复习知识点 |
|----------|------|-------------|
"""

    for interval in intervals:
        review_date = today + timedelta(days=interval)
        date_str = review_date.strftime("%Y-%m-%d")
        points_str = "、".join([f"[[知识点/{kp.get('point', '?')}|{kp.get('point', '?')}]]" for kp in knowledge_points[:5]])
        if len(knowledge_points) > 5:
            points_str += f" 等{len(knowledge_points)}个"
        content += f"| {date_str} | 第{interval}天 | {points_str} |\n"

    content += f"""
## 📝 知识点复习状态

| # | 知识点 | 重要性 | 第1次 | 第2次 | 第3次 | 第4次 | 掌握程度 |
|---|--------|--------|-------|-------|-------|-------|----------|
"""

    for i, kp in enumerate(knowledge_points, 1):
        point = kp.get("point", "?")
        importance = kp.get("importance", "中")
        content += f"| {i} | [[知识点/{point}|{point}]] | {importance} | ☐ | ☐ | ☐ | ☐ | 待复习 |\n"

    content += """
---

> 💡 **使用方法**：每复习完一个知识点，在对应日期打勾，并更新掌握程度（待复习/复习中/已掌握）。
> 掌握程度为"已掌握"的知识点可延长复习间隔（30天）。
"""

    with open(review_path, "w", encoding="utf-8") as f:
        f.write(content)

    return review_path


def write_to_obsidian(input_path: str, topic: str = None, dry_run: bool = False) -> dict:
    """
    主流程 v2：读取 summary/deep_dive → 生成视频总览 + 知识点独立笔记 → 复习清单 → 更新索引
    """
    data = load_data(input_path)
    if "error" in data:
        return data

    # 判断格式
    v2 = is_v2_deep_dive(data)
    format_label = "v2深度版" if v2 else "v1基础版"
    print(f"[写入] 检测到 {format_label} 格式")

    # 确定主题
    if topic is None:
        topic = data.get("topic", data.get("topic_suggestion", "未分类"))
    topic = sanitize_filename(topic)

    # 主题目录
    topic_dir = os.path.join(OBSIDIAN_BASE, topic)
    video_dir = os.path.join(topic_dir, "视频笔记")
    knowledge_dir = os.path.join(topic_dir, "知识点")
    os.makedirs(video_dir, exist_ok=True)
    os.makedirs(knowledge_dir, exist_ok=True)

    # 元数据
    metadata = data.get("metadata", {})
    title = metadata.get("title", "未知视频")
    platform = metadata.get("platform", "unknown")
    video_id = metadata.get("video_id", "")
    video_url = metadata.get("url", "")

    # 知识点列表
    knowledge_points = data.get("knowledge_points", data.get("core_knowledge_points", []))

    # 收集本主题全部知识点名（当前视频 + 主题目录已有），用于关联智能匹配/跨视频互链
    all_point_names = [kp.get("point", "") for kp in knowledge_points if kp.get("point")]
    if os.path.isdir(knowledge_dir):
        for fn in os.listdir(knowledge_dir):
            if fn.endswith(".md"):
                stem = fn[:-3]
                if stem not in all_point_names:
                    all_point_names.append(stem)

    # 1. 生成视频总览笔记
    overview_filename = sanitize_filename(f"{platform}_{title}") + ".md"
    overview_path = os.path.join(video_dir, overview_filename)
    overview_content = generate_video_overview_note(data, topic)

    # 2. 生成每个知识点的独立笔记
    knowledge_notes = []
    for kp in knowledge_points:
        point = kp.get("point", "未知知识点")
        kp_filename = sanitize_filename(point) + ".md"
        kp_path = os.path.join(knowledge_dir, kp_filename)
        kp_content = generate_knowledge_point_note(kp, topic, title, video_url, platform, all_point_names)
        knowledge_notes.append({
            "point": point,
            "filename": kp_filename,
            "path": kp_path,
        })

    if dry_run:
        return {
            "topic": topic,
            "topic_dir": topic_dir,
            "video_overview": {"filename": overview_filename, "path": overview_path},
            "knowledge_points": len(knowledge_notes),
            "knowledge_notes": knowledge_notes[:3],
            "dry_run": True,
            "format": format_label,
        }

    # 写入视频总览
    with open(overview_path, "w", encoding="utf-8") as f:
        f.write(overview_content)
    print(f"[写入] 视频总览: {overview_path}")

    # 写入知识点笔记
    for kn in knowledge_notes:
        with open(kn["path"], "w", encoding="utf-8") as f:
            f.write(generate_knowledge_point_note(
                next(kp for kp in knowledge_points if kp.get("point") == kn["point"]),
                topic, title, video_url, platform, all_point_names
            ))
    print(f"[写入] 知识点笔记: {len(knowledge_notes)} 个 → {knowledge_dir}")

    # 生成复习清单
    review_path = generate_review_list(topic_dir, knowledge_points, topic)
    print(f"[写入] 复习清单: {review_path}")

    # 更新总览索引
    update_topic_overview(topic_dir, data, overview_filename, len(knowledge_points))

    # 清理临时文件
    output_dir = metadata.get("output_dir", "")
    cleaned = []
    if output_dir and os.path.exists(output_dir):
        for f in os.listdir(output_dir):
            if f.endswith((".mp3", ".m4a", ".wav", ".mp4", ".mkv", ".webm")):
                fp = os.path.join(output_dir, f)
                try:
                    os.remove(fp)
                    cleaned.append(f)
                except:
                    pass
    if cleaned:
        print(f"[清理] 已删除临时媒体文件: {len(cleaned)} 个")

    return {
        "topic": topic,
        "topic_dir": topic_dir,
        "video_overview": overview_path,
        "knowledge_points": len(knowledge_notes),
        "knowledge_dir": knowledge_dir,
        "review_list": review_path,
        "overview_path": os.path.join(topic_dir, "_总览.md"),
        "cleaned_files": len(cleaned),
        "format": format_label,
        "success": True,
    }


def update_topic_overview(topic_dir: str, data: dict, overview_filename: str, point_count: int):
    """更新或创建主题 _总览.md"""
    overview_path = os.path.join(topic_dir, "_总览.md")
    metadata = data.get("metadata", {})
    title = metadata.get("title", "未知")
    uploader = metadata.get("uploader", "?")
    platform = metadata.get("platform", "?")
    url = metadata.get("url", "")
    one_line = data.get("one_sentence_summary", "")
    video_id = str(metadata.get("video_id", "")).strip()

    if os.path.exists(overview_path):
        with open(overview_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        topic_name = os.path.basename(topic_dir)
        content = f"""---
topic: "{topic_name}"
created: "{datetime.now().strftime('%Y-%m-%d')}"
---

# {topic_name} 学习总览

## 🗺️ 知识谱系
- [[_知识谱系总图|知识谱系总图]]（Mermaid mindmap 全景图）

## 📚 复习计划
- [[_复习清单|复习清单]]（间隔重复 1/3/7/15天）

## 📹 视频索引

| # | 标题 | UP主 | 平台 | 知识点数 | 一句话总结 | 笔记 |
|---|------|------|------|----------|-----------|------|
"""

    # 按 video_id 去重
    anchor = f"<!--vid:{video_id}-->" if video_id else ""
    if video_id:
        kept = []
        for line in content.splitlines(keepends=True):
            is_row = line.lstrip().startswith("|")
            if is_row and (anchor in line or video_id in line):
                continue
            kept.append(line)
        content = "".join(kept)
        if content and not content.endswith("\n"):
            content += "\n"

    now = datetime.now().strftime("%Y-%m-%d")
    new_row = f"| {now} | [[视频笔记/{overview_filename[:-3]}|{title[:30]}]] | {uploader} | {platform} | {point_count} | {one_line[:30]}... | [笔记](视频笔记/{overview_filename}) {anchor} |\n"
    content += new_row

    with open(overview_path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    parser = argparse.ArgumentParser(description="Obsidian 写入模块 v2（两层笔记结构）")
    parser.add_argument("input", help="summary.json 或 deep_dive.json 路径")
    parser.add_argument("--topic", "-t", help="指定主题（默认用 LLM 建议）", default=None)
    parser.add_argument("--dry-run", action="store_true", help="只预览不写入")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    result = write_to_obsidian(args.input, args.topic, args.dry_run)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif "error" in result:
        print(f"❌ 错误: {result['error']}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\n✅ 写入完成！主题: {result.get('topic')}")
        print(f"   格式: {result.get('format')}")
        print(f"   视频总览: {result.get('video_overview')}")
        print(f"   知识点笔记: {result.get('knowledge_points')} 个")
        print(f"   复习清单: {result.get('review_list')}")


if __name__ == "__main__":
    main()
