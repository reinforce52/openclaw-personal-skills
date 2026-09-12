#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_link_notes.py - 批量自动建立笔记双向链接
解析插件生成的 note-graph.md 关系图，在原始笔记末尾添加"🔗 相关笔记"部分。
双向链接：A关联B，B也关联A。
用法:
  python auto_link_notes.py --dry-run    # 预览，不修改
  python auto_link_notes.py --apply      # 实际执行
"""
import os, re, sys, argparse
from collections import defaultdict

VAULT_BASE = r"E:\obsidian\rein"
NOTE_GRAPH = os.path.join(VAULT_BASE, "_wiki", "relations", "note-graph.md")

# 排除的系统目录（不修改这些目录下的笔记）
EXCLUDE_DIRS = {"_wiki", "_概念层", "_templates", "_vault-health",
                 "00-系统导航", ".obsidian", "01-上下文"}

# "相关笔记"部分的标记
RELATED_SECTION = "🔗 相关笔记"


def parse_note_graph():
    """解析 note-graph.md 的表格，返回 {原始笔记: [关联笔记列表]}"""
    if not os.path.exists(NOTE_GRAPH):
        print(f"❌ note-graph.md 不存在: {NOTE_GRAPH}")
        return {}

    with open(NOTE_GRAPH, 'r', encoding='utf-8') as f:
        content = f.read()

    relations = defaultdict(set)

    # 解析表格行：| [[原始笔记]] | ... | [[关联1]]<br>[[关联2]] | ... |
    for line in content.split('\n'):
        if not line.startswith('|') or '---' in line or '原始笔记' in line:
            continue

        cells = [c.strip() for c in line.split('|')]
        if len(cells) < 4:
            continue

        # 第1列：原始笔记
        source_cell = cells[1]
        source_match = re.search(r'\[\[([^\]]+)\]\]', source_cell)
        if not source_match:
            continue
        source = source_match.group(1).strip()

        # 第3列：关联原始笔记（用<br>分隔）
        related_cell = cells[3]
        related_matches = re.findall(r'\[\[([^\]]+)\]\]', related_cell)

        for related in related_matches:
            related = related.strip()
            if related and related != source:
                relations[source].add(related)
                # 双向：关联笔记也关联原始笔记
                relations[related].add(source)

    return dict(relations)


def is_system_note(rel_path):
    """判断是否是系统目录下的笔记（不修改）"""
    parts = rel_path.replace('\\', '/').split('/')
    for part in parts:
        if part in EXCLUDE_DIRS:
            return True
    return False


def note_exists(rel_path):
    """检查笔记文件是否存在（自动补.md后缀）"""
    full = os.path.join(VAULT_BASE, rel_path)
    if os.path.exists(full):
        return True
    if not full.endswith('.md'):
        full_md = full + '.md'
        if os.path.exists(full_md):
            return True
    return False


def get_full_path(rel_path):
    """获取笔记的完整路径（自动补.md后缀）"""
    full = os.path.join(VAULT_BASE, rel_path)
    if os.path.exists(full):
        return full
    if not full.endswith('.md'):
        full_md = full + '.md'
        if os.path.exists(full_md):
            return full_md
    return full


def has_related_section(content):
    """检查笔记是否已有"相关笔记"部分"""
    return RELATED_SECTION in content


def add_related_section(content, related_notes):
    """在笔记末尾添加"🔗 相关笔记"部分"""
    # 过滤掉不存在的笔记和系统笔记
    valid_related = []
    for r in related_notes:
        if note_exists(r) and not is_system_note(r):
            valid_related.append(r)

    if not valid_related:
        return content, False

    # 构建相关笔记部分
    section = f"\n---\n\n## {RELATED_SECTION}\n\n"
    section += "> 由 AI RAG 插件自动发现的关联笔记，已自动建立双向链接。\n\n"
    for r in sorted(valid_related):
        # 用笔记名作为显示文本
        display = os.path.basename(r).replace('.md', '')
        section += f"- [[{r}|{display}]]\n"
    section += "\n"

    # 如果已有"相关笔记"部分，替换它；否则追加到末尾
    if RELATED_SECTION in content:
        # 找到"相关笔记"部分，替换到文件末尾或下一个---
        pattern = rf'## {re.escape(RELATED_SECTION)}.*?(?=\n## |\Z)'
        content = re.sub(pattern, section.strip() + '\n', content, flags=re.DOTALL)
    else:
        # 追加到末尾
        content = content.rstrip() + '\n' + section

    return content, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="预览模式，不修改文件")
    ap.add_argument("--apply", action="store_true", help="实际执行")
    args = ap.parse_args()

    if not args.dry_run and not args.apply:
        print("请指定 --dry-run（预览）或 --apply（执行）")
        sys.exit(1)

    mode = "预览" if args.dry_run else "执行"
    print(f"{'='*60}")
    print(f"🔗 批量自动建立笔记双向链接 [{mode}]")
    print(f"{'='*60}")

    # 1. 解析 note-graph
    print("\n📊 解析 note-graph.md 关系图...")
    relations = parse_note_graph()
    print(f"  发现 {len(relations)} 个笔记有关联建议")

    # 统计总关联数
    total_relations = sum(len(v) for v in relations.values())
    print(f"  共 {total_relations} 条关联建议（含双向）")

    # 2. 过滤：只处理存在的、非系统的笔记
    print("\n🔍 过滤有效笔记...")
    valid_relations = {}
    skipped_system = 0
    skipped_missing = 0

    for source, related in relations.items():
        if is_system_note(source):
            skipped_system += 1
            continue
        if not note_exists(source):
            skipped_missing += 1
            continue
        valid_related = {r for r in related if note_exists(r) and not is_system_note(r)}
        if valid_related:
            valid_relations[source] = valid_related

    print(f"  跳过系统目录笔记: {skipped_system}")
    print(f"  跳过不存在的笔记: {skipped_missing}")
    print(f"  有效待处理笔记: {len(valid_relations)}")

    # 3. 检查哪些已有"相关笔记"部分
    print("\n📝 检查已有关联部分...")
    already_has = 0
    will_modify = 0
    modify_list = []

    for source, related in valid_relations.items():
        full = get_full_path(source)
        try:
            with open(full, 'r', encoding='utf-8') as f:
                content = f.read()
            if has_related_section(content):
                already_has += 1
            else:
                will_modify += 1
                modify_list.append((source, len(related)))
        except Exception as e:
            print(f"  ⚠️ 读取失败 {source}: {e}")

    print(f"  已有相关笔记部分: {already_has}")
    print(f"  需要新增关联: {will_modify}")

    # 4. 显示前10个待修改的笔记
    print("\n📋 待修改笔记预览（前10个）:")
    for source, count in sorted(modify_list, key=lambda x: -x[1])[:10]:
        print(f"  - {source} ({count}个关联)")

    if len(modify_list) > 10:
        print(f"  ... 还有 {len(modify_list)-10} 个")

    # 5. 执行模式：实际修改
    if args.apply:
        print(f"\n⚡ 开始执行修改...")
        success = 0
        failed = 0

        for source, related in valid_relations.items():
            full = get_full_path(source)
            try:
                with open(full, 'r', encoding='utf-8') as f:
                    content = f.read()

                new_content, modified = add_related_section(content, related)
                if modified:
                    with open(full, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    success += 1
                else:
                    already_has += 1
            except Exception as e:
                print(f"  ❌ 修改失败 {source}: {e}")
                failed += 1

        print(f"\n{'='*60}")
        print(f"✅ 执行完成！")
        print(f"  成功修改: {success} 个笔记")
        print(f"  已有相关部分（跳过）: {already_has}")
        print(f"  失败: {failed}")
        print(f"{'='*60}")
    else:
        print(f"\n💡 这是预览模式，没有修改任何文件。")
        print(f"   确认无误后运行: python auto_link_notes.py --apply")


if __name__ == "__main__":
    main()
