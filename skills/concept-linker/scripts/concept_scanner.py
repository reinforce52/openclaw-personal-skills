#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
concept_scanner.py - 扫描所有主题 vault，提取高频概念，建立概念索引
输出: concepts_index.json（概念→出现位置的映射），供后续 LLM 生成概念页使用
"""
import os, re, json, argparse
from collections import defaultdict
from pathlib import Path

# 学习类主题目录（排除系统/配置/非学习目录）
LEARNING_TOPICS = [
    "线性代数", "考研数学", "考研高数", "英语六级", "六级备考技巧",
    "自动控制原理", "土木跨考控制工程", "神经网络基础",
    "berkeley-stat-157_learning_assets", "MiniMind_Learning",
]
# 排除的目录名关键词
EXCLUDE_DIRS = [".obsidian", "视频笔记", "_vault-health", "_概念层", "_templates"]
# 通用停用词（不建概念页）
STOP_WORDS = {
    "知识点", "视频笔记", "学习", "笔记", "总结", "总览", "复习", "复习清单",
    "知识谱系", "知识谱系总图", "核心知识点", "视频", "课程", "教程",
    "每日学习记录", "每日日志", "项目", "模板", "索引", "目录",
    "考研", "备考", "技巧", "方法", "基础", "进阶", "强化",
    "真题", "例题", "习题", "答案", "解析",
    "第一章", "第二章", "第三章", "第四章", "第五章",
    "第一讲", "第二讲", "第三讲",
}


def sanitize_concept(name):
    """清理概念名"""
    name = re.sub(r'[#*_`~|<>\\/\[\]{}]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    # 去掉常见前缀
    for prefix in ["知识点/", "视频笔记/", "99-教材原文/"]:
        if name.startswith(prefix):
            name = name[len(prefix):]
    return name.strip()


def is_valid_concept(name):
    """判断是否是有效概念"""
    if not name or len(name) < 2 or len(name) > 30:
        return False
    if name in STOP_WORDS:
        return False
    # 纯数字/日期
    if re.match(r'^[\d\s\-:./]+$', name):
        return False
    # 纯英文停用词
    if name.lower() in {"the", "a", "an", "and", "or", "of", "to", "in", "for", "is", "are"}:
        return False
    return True


def extract_frontmatter(text):
    """提取 YAML frontmatter"""
    m = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).split('\n'):
        line = line.strip()
        if ':' in line:
            key, val = line.split(':', 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            fm[key] = val
    return fm


def extract_tags(fm):
    """从 frontmatter 提取 tags"""
    tags = []
    tags_str = fm.get("tags", "")
    if tags_str:
        # 处理 ["a","b"] 格式
        m = re.findall(r'"([^"]+)"', tags_str)
        if m:
            tags.extend(m)
        else:
            tags.extend([t.strip() for t in tags_str.split(',') if t.strip()])
    # category
    cat = fm.get("category", "")
    if cat and cat not in tags:
        tags.append(cat)
    # topic
    topic = fm.get("topic", "")
    if topic and topic not in tags:
        tags.append(topic)
    return tags


def extract_wikilinks(text):
    """提取 wikilink 目标（[[xxx]] 或 [[xxx|yyy]]）"""
    links = []
    for m in re.finditer(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', text):
        target = m.group(1).strip()
        # 去掉路径前缀，只取最后一部分
        if '/' in target:
            target = target.split('/')[-1]
        links.append(target)
    return links


def extract_from_filename(filepath, vault_base):
    """从文件名和路径提取概念"""
    rel = os.path.relpath(filepath, vault_base)
    parts = Path(rel).parts
    concepts = []
    # 主题名（第一级目录）
    if len(parts) > 1:
        concepts.append(parts[0])
    # 子目录名（如"知识点"下的不算，但"行列式"等算）
    if len(parts) > 2:
        subdir = parts[1]
        if subdir not in ["知识点", "视频笔记", "99-教材原文", "images"]:
            concepts.append(subdir)
    # 文件名（去掉.md）
    fname = Path(filepath).stem
    # 去掉视频前缀如 "bilibili_xxx p01"
    fname = re.sub(r'^(bilibili|youtube|douyin)_', '', fname)
    fname = re.sub(r'^.*?p\d+\s*[-—]\s*', '', fname)
    concepts.append(fname)
    return concepts


def scan_vault(vault_base):
    """扫描整个 vault，提取概念索引"""
    concept_locations = defaultdict(list)  # 概念 -> [{topic, file, title, tags}]
    file_count = 0
    topic_files = defaultdict(int)

    for root, dirs, files in os.walk(vault_base):
        # 排除目录
        dirs[:] = [d for d in dirs if not any(ex in d for ex in EXCLUDE_DIRS)]

        for fname in files:
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, vault_base)
            topic = rel.split(os.sep)[0] if os.sep in rel else rel

            # 只扫描学习类主题
            if topic not in LEARNING_TOPICS:
                continue

            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    text = f.read()
            except Exception:
                continue

            file_count += 1
            topic_files[topic] += 1

            fm = extract_frontmatter(text)
            tags = extract_tags(fm)
            wikilinks = extract_wikilinks(text)
            filename_concepts = extract_from_filename(fpath, vault_base)
            title = fm.get("title", Path(fpath).stem)

            # 合并所有概念来源
            all_concepts = set()
            for src in [tags, wikilinks, filename_concepts]:
                for c in src:
                    c = sanitize_concept(c)
                    if is_valid_concept(c):
                        all_concepts.add(c)

            # 记录每个概念的出现位置
            for concept in all_concepts:
                concept_locations[concept].append({
                    "topic": topic,
                    "file": rel.replace("\\", "/"),
                    "title": title[:80],
                    "tags": tags[:5],
                })

    return concept_locations, file_count, topic_files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=r"E:\obsidian\rein", help="Vault 根目录")
    ap.add_argument("--output", default=None, help="输出 JSON 路径")
    ap.add_argument("--top", type=int, default=50, help="提取 top N 高频概念")
    args = ap.parse_args()

    print(f"扫描 vault: {args.vault}")
    concept_locations, file_count, topic_files = scan_vault(args.vault)

    print(f"\n扫描完成: {file_count} 个学习类笔记文件")
    print(f"涉及主题: {len(topic_files)} 个")
    for t, c in sorted(topic_files.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c} 个")

    # 按出现频率排序
    sorted_concepts = sorted(concept_locations.items(), key=lambda x: -len(x[1]))

    print(f"\n共提取 {len(sorted_concepts)} 个概念")
    print(f"\n=== Top {args.top} 高频概念 ===")
    for i, (concept, locs) in enumerate(sorted_concepts[:args.top], 1):
        topics = set(l["topic"] for l in locs)
        print(f"  {i:2d}. {concept:30s} 出现{len(locs):3d}次  跨{len(topics)}主题: {', '.join(sorted(topics)[:4])}")

    # 输出 JSON
    if args.output:
        output_data = {
            "total_files": file_count,
            "total_concepts": len(sorted_concepts),
            "topics": dict(topic_files),
            "concepts": [
                {
                    "name": c,
                    "count": len(locs),
                    "topics": list(set(l["topic"] for l in locs)),
                    "locations": locs,
                }
                for c, locs in sorted_concepts
            ],
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 概念索引已保存: {args.output}")


if __name__ == "__main__":
    main()
