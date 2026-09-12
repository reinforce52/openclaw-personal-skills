#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多合集融合对比生成模块
- 扫描临时目录下所有 summary.json
- 按 BV号 分组（同一主题下的不同合集/博主）
- 提取每个视频的精炼大纲，调用 LLM 生成「相关性 / 区别点 / 互补内容 / 学习顺序」融合文档
- 写入 Obsidian 主题目录的 _融合对比.md
"""

import os
import sys
import json
import glob
import argparse
import requests
from datetime import datetime

# ============ LLM 配置（与 summarize.py 一致，中南大学 deepseek-v3）============
API_BASE = "https://api.chat.csu.edu.cn/v1"
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")  # 从环境变量读取，不要硬编码密钥
MODEL = "deepseek-v3"

TEMP_BASE = r"E:\openclaw-video-temp"
OBSIDIAN_BASE = r"E:\obsidian\rein"


def collect_summaries(temp_base: str) -> dict:
    """按 BV号 分组收集所有 summary.json 的精炼信息"""
    groups = {}
    for sp in glob.glob(os.path.join(temp_base, "*", "summary.json")):
        try:
            with open(sp, "r", encoding="utf-8") as f:
                d = json.load(f)
            meta = d.get("metadata", {})
            vid = meta.get("video_id", "") or os.path.basename(os.path.dirname(sp))
            # BV号 = video_id 下划线前部分（BV1xxx_pN → BV1xxx）
            bv = vid.split("_p")[0].split("_")[0] if "_p" in vid else vid
            title = meta.get("title", "未知")
            points = d.get("core_knowledge_points", [])
            point_titles = []
            for p in points:
                if isinstance(p, dict):
                    point_titles.append(p.get("point", ""))
                elif isinstance(p, str):
                    point_titles.append(p)
            groups.setdefault(bv, []).append({
                "video_id": vid,
                "title": title,
                "uploader": meta.get("uploader", "?"),
                "duration_sec": round(float(meta.get("duration", 0) or 0), 0),
                "one_sentence": d.get("one_sentence_summary", ""),
                "topic": d.get("topic_suggestion", ""),
                "points": [t for t in point_titles if t][:10],
                "suggest": d.get("learning_suggestions", ""),
            })
        except Exception as e:
            print(f"  跳过 {sp}: {e}")
    # 每组按 video_id 排序
    for bv in groups:
        groups[bv].sort(key=lambda x: x["video_id"])
    return groups


def build_outline(items: list, name: str) -> str:
    """把一组视频压缩成大纲文本"""
    lines = [f"### 合集：{name}（共 {len(items)} 个视频）"]
    uploaders = sorted(set(i["uploader"] for i in items))
    lines.append(f"UP主：{'、'.join(uploaders)}")
    total_min = sum(i["duration_sec"] for i in items) / 60
    lines.append(f"总时长：约 {total_min:.0f} 分钟\n")
    for i, it in enumerate(items, 1):
        lines.append(f"{i}. 【{it['title']}】")
        if it["one_sentence"]:
            lines.append(f"   概述：{it['one_sentence']}")
        if it["points"]:
            lines.append(f"   知识点：{'；'.join(it['points'][:8])}")
    return "\n".join(lines)


def call_llm(group_outlines: str, topic: str, group_meta: list) -> str:
    """调用 LLM 生成融合对比 Markdown"""
    group_desc = "\n".join(f"- {g['name']}（BV号 {g['bv']}，{g['count']}个视频，UP主 {g['uploader']}）" for g in group_meta)
    system_prompt = (
        "你是资深学习规划师和学科教研专家。用户把同一主题下、来自不同合集/UP主的多套视频课都转写成了结构化笔记，"
        "现在需要你通读各合集大纲，产出一份「多合集融合对比与学习指南」，帮助用户高效整合这些资料。"
        "输出必须是结构清晰的中文 Markdown，客观、具体、可执行，不要空泛套话。"
    )
    user_prompt = f"""主题：{topic}

本主题下共有 {len(group_meta)} 个合集：
{group_desc}

以下是各合集每个视频的精炼大纲（含概述与核心知识点）：

{group_outlines}

请生成融合对比文档，严格包含以下部分：

## 一、各合集定位与内容地图
分别用一段话概括每个合集的定位、教学体系、覆盖的知识模块，列出该合集的模块/章节脉络（用列表）。

## 二、合集之间的相关性
说明它们在知识体系上如何关联、共同服务于什么目标，哪些内容是互相呼应、重复覆盖或前后衔接的。

## 三、合集之间的区别点
用表格对比：教学侧重、讲解风格、难度层次、适用阶段、内容颗粒度等维度，逐个合集对比。

## 四、互补内容与各自不可替代之处
说明哪个合集在哪些知识点上讲得更深/更全，另一个补上了什么，哪些是某合集独有。

## 五、融合学习路线（推荐顺序）
结合各合集特点，给出一套最优学习顺序与时间安排建议（比如先学哪个打基础、再用哪个强化、怎么穿插），分阶段列出。

## 六、知识盲区与补充建议
指出这些合集合起来仍可能没覆盖到的考点或能力，建议补充什么资料/练习。

只输出 Markdown 正文，不要输出与上述六部分无关的开场白或结束语。"""

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.5,
        "max_tokens": 8000,
    }
    print(f"[融合] 调用LLM生成对比文档（大纲约{len(user_prompt)}字）...")
    resp = requests.post(
        f"{API_BASE}/chat/completions",
        headers=headers, json=payload, timeout=600,
        proxies={"http": None, "https": None},
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def main():
    parser = argparse.ArgumentParser(description="多合集融合对比生成")
    parser.add_argument("--topic", required=True, help="Obsidian主题名（如 英语六级）")
    parser.add_argument("--bvs", default=None, help="只对比指定BV号，逗号分隔（默认该主题临时目录下全部）")
    parser.add_argument("--names", default=None, help="各BV号对应的合集名称，逗号分隔（与--bvs同序）")
    parser.add_argument("--output", default=None, help="输出md路径（默认主题目录/_融合对比.md）")
    args = parser.parse_args()

    groups = collect_summaries(TEMP_BASE)
    if not groups:
        print("❌ 未在临时目录找到任何 summary.json")
        sys.exit(1)

    # 筛选要对比的BV
    if args.bvs:
        want = [b.strip() for b in args.bvs.split(",")]
        groups = {b: groups[b] for b in want if b in groups}
    if len(groups) < 1:
        print("❌ 没有可对比的合集")
        sys.exit(1)

    name_list = [n.strip() for n in args.names.split(",")] if args.names else []
    # 按 --bvs 指定顺序遍历（若指定），保证 BV号与合集名称严格对应；否则按BV号排序
    if args.bvs:
        ordered_bvs = [b.strip() for b in args.bvs.split(",") if b.strip() in groups]
    else:
        ordered_bvs = sorted(groups.keys())
    group_meta, outlines = [], []
    for idx, bv in enumerate(ordered_bvs):
        items = groups[bv]
        uploader = items[0]["uploader"] if items else "?"
        name = name_list[idx] if idx < len(name_list) else f"{uploader}合集"
        group_meta.append({"bv": bv, "name": name, "count": len(items), "uploader": uploader})
        outlines.append(build_outline(items, name))
        print(f"[融合] {bv} → {name}: {len(items)}个视频 (UP:{uploader})")

    body = call_llm("\n\n".join(outlines), args.topic, group_meta)

    # 组装文档
    header = f"""---
topic: "{args.topic}"
type: "多合集融合对比"
created: "{datetime.now().strftime('%Y-%m-%d %H:%M')}"
collections: {json.dumps([g['bv'] for g in group_meta], ensure_ascii=False)}
tags: ["融合对比", "{args.topic}"]
---

# {args.topic} · 多合集融合对比与学习指南

> 本文档由 video-to-knowledge 自动生成，整合了 {len(group_meta)} 个合集、共 {sum(g['count'] for g in group_meta)} 个视频笔记。
> 合集清单：{'；'.join(f"{g['name']}（{g['count']}个）" for g in group_meta)}

"""
    out_path = args.output or os.path.join(OBSIDIAN_BASE, args.topic, "_融合对比.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header + body + "\n")
    print(f"\n✅ 融合对比文档已生成: {out_path}")
    print(f"   大小: {os.path.getsize(out_path)/1024:.1f} KB")


if __name__ == "__main__":
    main()
