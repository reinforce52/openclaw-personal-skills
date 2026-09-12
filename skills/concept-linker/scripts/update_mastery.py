#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_mastery.py - 基于 personal-twin 推断概念掌握度，更新概念页 frontmatter
推断逻辑：
  - 错题卡点中出现 ≥2 次 → 薄弱（⚠️）
  - 错题卡点中出现 1 次 → 需复习（🔁）
  - 项目库中实际应用 → 已掌握（✅）
  - 有学习笔记但无卡点 → 学习中（🔄）
  - 无任何笔记 → 待学习（⚪）
用法:
  python update_mastery.py --vault "E:\obsidian\rein"
"""
import os, re, json, argparse
from datetime import datetime
from pathlib import Path

VAULT_BASE = r"E:\obsidian\rein"
CONCEPT_DIR = os.path.join(VAULT_BASE, "_概念层", "concepts")
PERSONAL_TWIN_DIR = os.path.join(VAULT_BASE, "_个人镜像")

MASTERY_LEVELS = {
    "待学习": {"icon": "⚪", "rank": 0},
    "学习中": {"icon": "🔄", "rank": 1},
    "已掌握": {"icon": "✅", "rank": 2},
    "需复习": {"icon": "🔁", "rank": 3},
    "薄弱": {"icon": "⚠️", "rank": 4},
}


def read_file_safe(path):
    """安全读取文件"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""


def extract_mistake_concepts():
    """从错题卡点日志中提取概念和出现次数"""
    mistake_file = os.path.join(PERSONAL_TWIN_DIR, "03_错题卡点日志.md")
    content = read_file_safe(mistake_file)
    if not content:
        return {}

    concept_counts = {}
    # 提取所有wikilink中的概念
    for m in re.finditer(r'\[\[([^\]|#]+)', content):
        target = m.group(1).strip()
        # 只保留概念层中的概念
        concept_name = os.path.basename(target)
        if os.path.exists(os.path.join(CONCEPT_DIR, concept_name + ".md")):
            concept_counts[concept_name] = concept_counts.get(concept_name, 0) + 1

    # 也从正文中提取概念关键词
    concept_files = [f[:-3] for f in os.listdir(CONCEPT_DIR) if f.endswith('.md')]
    for concept in concept_files:
        # 统计概念名在错题日志中出现的次数
        count = content.count(concept)
        if count > 0 and concept not in concept_counts:
            concept_counts[concept] = count

    return concept_counts


def extract_project_concepts():
    """从项目库中提取实际应用的概念"""
    project_dir = os.path.join(VAULT_BASE, "03-项目库")
    if not os.path.exists(project_dir):
        return set()

    applied_concepts = set()
    for root, dirs, files in os.walk(project_dir):
        for fname in files:
            if not fname.endswith('.md'):
                continue
            content = read_file_safe(os.path.join(root, fname))
            concept_files = [f[:-3] for f in os.listdir(CONCEPT_DIR) if f.endswith('.md')]
            for concept in concept_files:
                if concept in content:
                    applied_concepts.add(concept)
    return applied_concepts


def infer_mastery(concept_name, mistake_counts, applied_concepts, occurrence_count):
    """推断单个概念的掌握度"""
    # 1. 错题卡点中出现 ≥2 次 → 薄弱
    if mistake_counts.get(concept_name, 0) >= 2:
        return "薄弱", f"错题卡点中出现{mistake_counts[concept_name]}次"

    # 2. 错题卡点中出现 1 次 → 需复习
    if mistake_counts.get(concept_name, 0) == 1:
        return "需复习", "错题卡点中出现1次"

    # 3. 项目库中实际应用 → 已掌握
    if concept_name in applied_concepts:
        return "已掌握", "项目库中实际应用"

    # 4. 有学习笔记（出现次数 > 0）但无卡点 → 学习中
    if occurrence_count > 0:
        return "学习中", f"在{occurrence_count}篇笔记中出现"

    # 5. 无任何笔记 → 待学习
    return "待学习", "暂无学习笔记"


def update_concept_page(concept_name, mastery, evidence, is_manual=False):
    """更新概念页的 frontmatter 和掌握状态章节
    is_manual=True 时，写入 manual_mastery 字段，优先级高于自动推断
    """
    page_path = os.path.join(CONCEPT_DIR, concept_name + ".md")
    if not os.path.exists(page_path):
        return False

    content = read_file_safe(page_path)

    # 如果是人工标记，写入 manual_mastery 字段
    if is_manual:
        # 检查是否已有 manual_mastery 字段，没有则插入
        if "manual_mastery:" not in content:
            content = re.sub(
                r'(mastery_evidence: ".*?")',
                r'\1\nmanual_mastery: ""',
                content
            )
        content = re.sub(
            r'manual_mastery: ".*?"',
            f'manual_mastery: "{mastery}"',
            content
        )
        evidence = f"人工标记（{datetime.now().strftime('%Y-%m-%d')}）"

    # 更新 frontmatter 中的 mastery 字段（显示用）
    content = re.sub(
        r'mastery: ".*?"',
        f'mastery: "{mastery}"',
        content
    )
    content = re.sub(
        r'mastery_evidence: ".*?"',
        f'mastery_evidence: "{evidence}"',
        content
    )
    content = re.sub(
        r'updated: ".*?"',
        f'updated: "{datetime.now().strftime("%Y-%m-%d")}"',
        content
    )

    # 更新标题行中的掌握状态图标
    icon = MASTERY_LEVELS[mastery]["icon"]
    manual_tag = " 👤人工" if is_manual or 'manual_mastery: "' in content and 'manual_mastery: ""' not in content else ""
    content = re.sub(
        r'\*\*掌握状态\*\*：.*?\n',
        f'**掌握状态**：{icon} {mastery}{manual_tag}\n',
        content
    )

    # 更新"掌握状态"章节中的当前掌握度行
    content = re.sub(
        r'> 当前掌握度：\*\*.*?\*\*',
        f'> 当前掌握度：**{mastery}**（{evidence}）',
        content
    )

    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True


def get_manual_mastery(concept_name):
    """读取概念页的人工标记，返回 (mastery, has_manual)"""
    page_path = os.path.join(CONCEPT_DIR, concept_name + ".md")
    if not os.path.exists(page_path):
        return None, False
    content = read_file_safe(page_path)
    m = re.search(r'manual_mastery: "([^"]*)"', content)
    if m and m.group(1).strip():
        return m.group(1).strip(), True
    return None, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=VAULT_BASE)
    args = ap.parse_args()

    print("=" * 50)
    print("🔄 概念掌握度推断与更新")
    print("=" * 50)

    # 1. 提取错题卡点中的概念
    print("\n📋 扫描错题卡点日志...")
    mistake_counts = extract_mistake_concepts()
    print(f"  发现 {len(mistake_counts)} 个概念在错题卡点中出现")
    for c, n in sorted(mistake_counts.items(), key=lambda x: -x[1]):
        print(f"    {c}: {n}次")

    # 2. 提取项目库中应用的概念
    print("\n💼 扫描项目库...")
    applied_concepts = extract_project_concepts()
    print(f"  发现 {len(applied_concepts)} 个概念在项目中实际应用")

    # 3. 读取每个概念的出现次数
    print("\n📊 推断掌握度...")
    concept_files = sorted([f[:-3] for f in os.listdir(CONCEPT_DIR) if f.endswith('.md')])

    results = {"待学习": [], "学习中": [], "已掌握": [], "需复习": [], "薄弱": []}

    for concept in concept_files:
        # 从概念页 frontmatter 读取出现次数
        page_path = os.path.join(CONCEPT_DIR, concept + ".md")
        content = read_file_safe(page_path)
        occ_match = re.search(r'occurrence_count: (\d+)', content)
        occurrence = int(occ_match.group(1)) if occ_match else 0

        # 优先使用人工标记
        manual, has_manual = get_manual_mastery(concept)
        if has_manual and manual in MASTERY_LEVELS:
            mastery = manual
            evidence = f"人工标记（优先于自动推断）"
            print(f"  👤 {concept}: 人工标记为 {mastery}")
        else:
            mastery, evidence = infer_mastery(concept, mistake_counts, applied_concepts, occurrence)

        update_concept_page(concept, mastery, evidence, is_manual=has_manual)
        results[mastery].append((concept, evidence))

    # 4. 输出统计
    print("\n" + "=" * 50)
    print("📊 掌握度统计")
    print("=" * 50)
    for level in ["已掌握", "学习中", "需复习", "薄弱", "待学习"]:
        icon = MASTERY_LEVELS[level]["icon"]
        count = len(results[level])
        print(f"  {icon} {level}: {count}个")
        if level in ["薄弱", "需复习"] and results[level]:
            for c, e in results[level]:
                print(f"    - {c}（{e}）")

    # 5. 生成掌握度总览
    overview_path = os.path.join(VAULT_BASE, "_概念层", "_掌握度总览.md")
    overview = f"""---
type: "mastery-overview"
tags: ["概念层", "掌握度"]
updated: "{datetime.now().strftime('%Y-%m-%d')}"
---

# 📊 概念掌握度总览

> 基于 personal-twin 错题卡点日志和项目库自动推断。运行 `【更新概念掌握度】` 刷新。

---

## 统计

| 等级 | 数量 | 图标 |
|------|------|------|
| ✅ 已掌握 | {len(results['已掌握'])} | 项目中实际应用 |
| 🔄 学习中 | {len(results['学习中'])} | 有笔记无卡点 |
| 🔁 需复习 | {len(results['需复习'])} | 错题出现1次 |
| ⚠️ 薄弱 | {len(results['薄弱'])} | 错题出现≥2次 |
| ⚪ 待学习 | {len(results['待学习'])} | 暂无笔记 |

---

## ⚠️ 需重点关注（薄弱+需复习）

"""
    for level in ["薄弱", "需复习"]:
        if results[level]:
            icon = MASTERY_LEVELS[level]["icon"]
            overview += f"### {icon} {level}\n\n"
            for c, e in results[level]:
                overview += f"- [[{c}]]（{e}）\n"
            overview += "\n"

    overview += "---\n\n## ✅ 已掌握\n\n"
    for c, e in results["已掌握"]:
        overview += f"- [[{c}]]（{e}）\n"

    overview += "\n---\n\n## 🔄 学习中\n\n"
    for c, e in results["学习中"][:20]:
        overview += f"- [[{c}]]（{e}）\n"
    if len(results["学习中"]) > 20:
        overview += f"- …等共{len(results['学习中'])}个\n"

    with open(overview_path, 'w', encoding='utf-8') as f:
        f.write(overview)

    print(f"\n✅ 掌握度总览已生成: {overview_path}")
    print("=" * 50)


if __name__ == "__main__":
    main()
