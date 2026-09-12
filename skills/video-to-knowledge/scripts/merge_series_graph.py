#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""merge_series_graph.py - 生成合集级总知识谱系图
扫描主题目录下临时目录的所有 deep_dive.json / summary.json，合并为合集级 Mermaid mindmap：
  合集 → 每集 → 知识点 → 细分概念
同时生成学习路径（按视频顺序）和知识点总索引。
用法:
  python merge_series_graph.py --tempdir E:\openclaw-video-temp --bvid BV1ys411472E --topic 线性代数 --output E:\obsidian\rein\线性代数\_合集知识谱系总图.md
"""
import os, sys, json, re, argparse
from datetime import datetime


def load_all_data(tempdir, bvid):
    """扫描临时目录，按分P顺序收集所有视频的总结数据"""
    items = []
    if not os.path.isdir(tempdir):
        return items
    for d in os.listdir(tempdir):
        if bvid not in d:
            continue
        full = os.path.join(tempdir, d)
        if not os.path.isdir(full):
            continue
        # 分P号
        m = re.search(r"_p(\d+)$", d)
        if not m:
            continue
        page = int(m.group(1))
        # 优先 deep_dive.json，其次 summary.json
        data = None
        for name in ["deep_dive.json", "summary.json"]:
            p = os.path.join(full, name)
            if os.path.exists(p):
                try:
                    data = json.load(open(p, encoding="utf-8"))
                    break
                except Exception:
                    continue
        if not data:
            continue
        md = data.get("metadata", {})
        items.append({
            "page": page,
            "title": md.get("title", f"P{page}"),
            "url": md.get("url", ""),
            "platform": md.get("platform", ""),
            "one_line": data.get("one_sentence_summary", ""),
            "knowledge_chain": data.get("knowledge_chain", ""),
            "points": data.get("knowledge_points", []),
        })
    items.sort(key=lambda x: x["page"])
    return items


def sanitize_mm(s):
    """Mermaid mindmap 节点文本清理"""
    s = re.sub(r'[()\[\]{}<>]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s[:24]


def build_mindmap(items):
    lines = ["```mermaid", "mindmap", "  root((线性代数的本质))"]
    for it in items:
        vid = f"P{it['page']} " + sanitize_mm(it["title"].split(" p")[-1] if " p" in it["title"] else it["title"])[:20]
        lines.append(f"    第{it['page']}集：{vid}")
        for kp in it["points"][:8]:
            point = sanitize_mm(kp.get("point", "?"))
            if point:
                lines.append(f"      {point}")
    lines.append("```")
    return "\n".join(lines)


def build_learning_path(items):
    lines = ["## 📚 系列学习路径", ""]
    for it in items:
        lines.append(f"### 第{it['page']}集：{it['title'].split(' - ')[-1] if ' - ' in it['title'] else it['title']}")
        lines.append(f"> {it.get('one_line', '')}")
        if it.get("knowledge_chain"):
            lines.append(f"  知识脉络：{it['knowledge_chain']}")
        pts = [kp.get("point", "?") for kp in it["points"]]
        lines.append(f"  知识点（{len(pts)}个）：{' → '.join(pts[:8])}{'…' if len(pts)>8 else ''}")
        lines.append("")
    return "\n".join(lines)


def build_index(items):
    lines = ["## 📊 全集知识点索引", "", "| 集 | 知识点 | 重要性 | 笔记 |", "|---|--------|--------|------|"]
    for it in items:
        for kp in it["points"]:
            p = kp.get("point", "?")
            imp = kp.get("importance", "中")
            lines.append(f"| P{it['page']} | [[知识点/{p}|{p}]] | {imp} | [视频]({it['url']}) |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tempdir", required=True)
    ap.add_argument("--bvid", required=True)
    ap.add_argument("--topic", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    items = load_all_data(args.tempdir, args.bvid)
    if not items:
        print("❌ 未找到任何该BV号的总结数据"); sys.exit(1)

    total_points = sum(len(it["points"]) for it in items)
    print(f"合并 {len(items)} 集，{total_points} 个知识点")

    content = f"""---
category: "{args.topic}"
tags: ["知识谱系", "合集总图", "Mermaid", "视频学习"]
source: "3B1B 线性代数的本质 合集（{len(items)}集）+ web深度搜索"
created: "{datetime.now().strftime('%Y-%m-%d')}"
---

# {args.topic} - 合集知识谱系总图（{len(items)}集 / {total_points}知识点）

> 本图合并整个系列合集，先看全景把握体系，再按集逐知识点深入。

---

## 🗺️ 一、全景知识谱系（Mindmap）

{build_mindmap(items)}

---

{build_learning_path(items)}

---

{build_index(items)}

---

## 💡 使用说明
1. **先看全景图**：从序言→向量→组合/张成→矩阵变换→行列式→逆矩阵/列空间→点积→叉积→基变换→特征值→抽象空间→克莱姆法则，12章主线
2. **按集顺序学**：每集内的知识脉络已标注
3. **知识点独立成篇**：索引表点击跳转9段式深度笔记（定义/公式/例题/易错/关联/自测）
4. **配合视频回看**：每个知识点笔记顶部有视频时间戳
5. **复习闭环**：使用 `_复习清单.md` 按1/3/7/15天间隔重复

> 📌 由 video-to-knowledge skill v2 深度版自动生成（转写+必应web搜索+LLM知识关联）。
"""

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ 合集总谱系已生成: {args.output}")


if __name__ == "__main__":
    main()
