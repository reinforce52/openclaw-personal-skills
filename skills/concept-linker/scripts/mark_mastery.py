#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mark_mastery.py - 人工标记概念掌握度
标记后优先级高于自动推断，update_mastery.py 运行时不会覆盖人工标记。
用法:
  python mark_mastery.py --concept 矩阵 --level 已掌握
  python mark_mastery.py --concept 矩阵 --level 学习中
  python mark_mastery.py --concept 矩阵 --clear  # 清除人工标记，恢复自动推断
  python mark_mastery.py --list  # 列出所有人工标记的概念
"""
import os, re, sys, argparse
from datetime import datetime

VAULT_BASE = r"E:\obsidian\rein"
CONCEPT_DIR = os.path.join(VAULT_BASE, "_概念层", "concepts")

MASTERY_LEVELS = ["待学习", "学习中", "已掌握", "需复习", "薄弱"]
MASTERY_ICONS = {
    "待学习": "⚪", "学习中": "🔄", "已掌握": "✅",
    "需复习": "🔁", "薄弱": "⚠️"
}


def read_file_safe(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""


def mark_concept(concept_name, level):
    """标记单个概念的掌握度"""
    page_path = os.path.join(CONCEPT_DIR, concept_name + ".md")
    if not os.path.exists(page_path):
        # 尝试模糊匹配
        matches = [f[:-3] for f in os.listdir(CONCEPT_DIR)
                   if f.endswith('.md') and concept_name in f[:-3]]
        if matches:
            print(f"未找到精确匹配，相似概念: {matches}")
        else:
            print(f"❌ 概念不存在: {concept_name}")
        return False

    content = read_file_safe(page_path)

    # 写入/更新 manual_mastery 字段
    if "manual_mastery:" not in content:
        content = re.sub(
            r'(mastery_evidence: ".*?")',
            r'\1\nmanual_mastery: ""',
            content
        )
    content = re.sub(
        r'manual_mastery: ".*?"',
        f'manual_mastery: "{level}"',
        content
    )

    # 更新显示用的 mastery 字段
    content = re.sub(
        r'mastery: ".*?"',
        f'mastery: "{level}"',
        content
    )
    content = re.sub(
        r'mastery_evidence: ".*?"',
        f'mastery_evidence: "人工标记（{datetime.now().strftime("%Y-%m-%d")}）"',
        content
    )
    content = re.sub(
        r'updated: ".*?"',
        f'updated: "{datetime.now().strftime("%Y-%m-%d")}"',
        content
    )

    # 更新标题行
    icon = MASTERY_ICONS.get(level, "⚪")
    content = re.sub(
        r'\*\*掌握状态\*\*：.*?\n',
        f'**掌握状态**：{icon} {level} 👤人工\n',
        content
    )

    # 更新掌握状态章节
    content = re.sub(
        r'> 当前掌握度：\*\*.*?\*\*',
        f'> 当前掌握度：**{level}**（人工标记，优先于自动推断）',
        content
    )

    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 已标记 [{concept_name}] 为 [{level}] 👤人工")
    return True


def clear_mark(concept_name):
    """清除人工标记，恢复自动推断"""
    page_path = os.path.join(CONCEPT_DIR, concept_name + ".md")
    if not os.path.exists(page_path):
        print(f"❌ 概念不存在: {concept_name}")
        return False

    content = read_file_safe(page_path)
    content = re.sub(
        r'manual_mastery: ".*?"',
        'manual_mastery: ""',
        content
    )
    content = re.sub(
        r'\*\*掌握状态\*\*：.*?\n',
        '**掌握状态**：🔄 学习中（自动推断中，运行【更新概念掌握度】刷新）\n',
        content
    )

    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 已清除 [{concept_name}] 的人工标记，恢复自动推断")
    return True


def list_manual_marks():
    """列出所有人工标记的概念"""
    print("=" * 50)
    print("👤 人工标记的概念")
    print("=" * 50)
    count = 0
    for fname in sorted(os.listdir(CONCEPT_DIR)):
        if not fname.endswith('.md'):
            continue
        content = read_file_safe(os.path.join(CONCEPT_DIR, fname))
        m = re.search(r'manual_mastery: "([^"]*)"', content)
        if m and m.group(1).strip():
            level = m.group(1).strip()
            icon = MASTERY_ICONS.get(level, "⚪")
            print(f"  {icon} {fname[:-3]}: {level}")
            count += 1
    if count == 0:
        print("  （暂无人工标记）")
    print(f"\n共 {count} 个人工标记")
    print("=" * 50)


def main():
    ap = argparse.ArgumentParser(description="人工标记概念掌握度")
    ap.add_argument("--concept", "-c", help="概念名称")
    ap.add_argument("--level", "-l", choices=MASTERY_LEVELS, help="掌握度等级")
    ap.add_argument("--clear", action="store_true", help="清除人工标记")
    ap.add_argument("--list", action="store_true", help="列出所有人工标记")
    args = ap.parse_args()

    if args.list:
        list_manual_marks()
        return

    if not args.concept:
        print("❌ 请指定概念名称 --concept")
        print("用法: python mark_mastery.py --concept 矩阵 --level 已掌握")
        print("      python mark_mastery.py --list")
        sys.exit(1)

    if args.clear:
        clear_mark(args.concept)
    elif args.level:
        mark_concept(args.concept, args.level)
    else:
        print("❌ 请指定 --level 或 --clear")
        print(f"可选等级: {', '.join(MASTERY_LEVELS)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
