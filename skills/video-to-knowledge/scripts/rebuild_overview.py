#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主题总览重建模块
- 扫描某主题目录下所有视频笔记（非 _ 开头的 .md）
- 解析 frontmatter 与「一句话总结」
- 按合集(BV号)分组、组内按分P号排序，重建干净的 _总览.md
- 用于修复重复追加/链接失效的总览，也可日常重建
"""

import os
import re
import sys
import argparse
from datetime import datetime

OBSIDIAN_BASE = r"E:\obsidian\rein"


def parse_frontmatter_and_summary(text: str) -> dict:
    """提取 frontmatter 字段和一句话总结"""
    meta = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if m:
        for line in m.group(1).splitlines():
            mm = re.match(r'^(\w+)\s*:\s*"?(.*?)"?\s*$', line)
            if mm:
                meta[mm.group(1)] = mm.group(2)
    # 一句话总结：## 💡 一句话总结 之后的第一个非空行
    sm = re.search(r"##\s*💡\s*一句话总结\s*\n+([^\n]+)", text)
    meta["_summary"] = sm.group(1).strip() if sm else ""
    return meta


def sort_key(video_id: str):
    """BV号 + 分P数字 排序"""
    bv, _, p = video_id.partition("_p")
    try:
        pn = int(p)
    except ValueError:
        pn = 0
    return (bv, pn)


def short_title(full_title: str) -> str:
    """从冗长标题里提取 pXX 之后的小节名"""
    m = re.search(r"p\s*\d+\s*(.+)$", full_title, re.IGNORECASE)
    if m and m.group(1).strip():
        return f"P{re.search(r'p\s*(\d+)', full_title, re.IGNORECASE).group(1)} {m.group(1).strip()}"
    return full_title


def rebuild(topic_dir: str):
    notes = []
    for fn in os.listdir(topic_dir):
        if not fn.endswith(".md") or fn.startswith("_"):
            continue
        path = os.path.join(topic_dir, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception:
            continue
        meta = parse_frontmatter_and_summary(text)
        vid = meta.get("video_id", os.path.splitext(fn)[0])
        notes.append({
            "file": fn,
            "stem": os.path.splitext(fn)[0],
            "vid": vid,
            "title": meta.get("title", fn),
            "uploader": meta.get("uploader", "?"),
            "platform": meta.get("platform", "?"),
            "summary": meta.get("_summary", ""),
        })

    if not notes:
        print("❌ 目录下没有笔记")
        return False

    notes.sort(key=lambda n: sort_key(n["vid"]))

    # 按合集(BV)分组
    groups = {}
    for n in notes:
        bv = n["vid"].partition("_p")[0]
        groups.setdefault(bv, []).append(n)

    topic = os.path.basename(topic_dir)
    lines = [
        "---",
        f'topic: "{topic}"',
        f'created: "{datetime.now().strftime("%Y-%m-%d")}"',
        f'note_count: {len(notes)}',
        "---",
        "",
        f"# {topic} 学习总览",
        "",
        f"> 共 {len(notes)} 个视频笔记，按合集与分P顺序排列（{datetime.now().strftime('%Y-%m-%d %H:%M')} 重建）",
        "",
    ]

    multi = len(groups) > 1
    idx = 0
    for bv, items in sorted(groups.items()):
        uploader = items[0]["uploader"]
        if multi:
            lines += [f"## 📦 合集 {bv}（{uploader}，{len(items)}个）", ""]
        lines += [
            "| # | 章节 | UP主 | 平台 | 一句话总结 | 笔记 |",
            "|---|------|------|------|-----------|------|",
        ]
        for n in items:
            idx += 1
            st = short_title(n["title"]).replace("|", "丨")
            sm = (n["summary"][:48] + "...") if len(n["summary"]) > 48 else n["summary"]
            sm = sm.replace("|", "丨").replace("\n", " ")
            lines.append(
                f"| {idx} | {st} | {n['uploader']} | {n['platform']} | {sm} | [[{n['stem']}]] |"
            )
        lines.append("")

    out = os.path.join(topic_dir, "_总览.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ 总览已重建: {out}")
    print(f"   笔记 {len(notes)} 个，合集 {len(groups)} 个，索引行 {idx} 条")
    return True


def main():
    parser = argparse.ArgumentParser(description="重建主题总览")
    parser.add_argument("topic", help="主题名（E:\obsidian\rein 下的目录名）或绝对路径")
    args = parser.parse_args()
    topic_dir = args.topic if os.path.isabs(args.topic) else os.path.join(OBSIDIAN_BASE, args.topic)
    if not os.path.isdir(topic_dir):
        print(f"❌ 主题目录不存在: {topic_dir}")
        sys.exit(1)
    ok = rebuild(topic_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
