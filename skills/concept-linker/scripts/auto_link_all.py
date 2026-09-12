#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_link_all.py - 批量建立所有笔记的双向链接（解析全部Meta页面的建议关联）
比 auto_link_notes.py 更全面：解析所有533个Meta页面的"建议关联笔记"，
过滤系统目录，去重，批量建立双向链接。
用法:
  python auto_link_all.py --dry-run    # 预览
  python auto_link_all.py --apply      # 执行
"""
import os, re, sys, argparse
from collections import defaultdict

VAULT_BASE = r"E:\obsidian\rein"
META_DIR = os.path.join(VAULT_BASE, "_wiki", "meta")

# 排除的系统目录（不修改这些目录下的笔记，也不关联到这些目录）
EXCLUDE_DIRS = {"_wiki", "_概念层", "_templates", "_vault-health",
                 "00-系统导航", ".obsidian", "01-上下文", "_个人镜像"}

RELATED_SECTION = "🔗 相关笔记"


def is_system_note(rel_path):
    """判断是否是系统目录下的笔记"""
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


def extract_source_note_from_meta(meta_content, meta_filename):
    """从Meta页面提取对应的原始笔记路径"""
    # 方法1：从"原始笔记"部分提取
    m = re.search(r'## 原始笔记\s*\n(?:- \[\[([^\]]+)\]\])+', meta_content)
    if m:
        links = re.findall(r'\[\[([^\]]+)\]\]', m.group(0))
        if links:
            return links[0].strip()

    # 方法2：从Meta文件名推断（去掉"Meta-"前缀，可能和原始笔记同名）
    # Meta文件名格式：Meta-<原始笔记名>.md
    if meta_filename.startswith("Meta-"):
        inferred = meta_filename[5:]  # 去掉"Meta-"
        return inferred

    return None


def extract_suggested_links(meta_content):
    """从Meta页面提取"建议关联笔记"的链接列表"""
    m = re.search(r'## 建议关联笔记\s*\n(.*?)(?=\n## |\Z)', meta_content, re.DOTALL)
    if not m:
        return []
    links = re.findall(r'\[\[([^\]]+)\]\]', m.group(1))
    return [l.strip() for l in links if l.strip()]


def parse_all_meta():
    """解析所有Meta页面，返回 {原始笔记: set(关联笔记)}"""
    relations = defaultdict(set)
    meta_count = 0
    no_source = 0

    for meta_file in os.listdir(META_DIR):
        if not meta_file.endswith('.md'):
            continue
        meta_path = os.path.join(META_DIR, meta_file)
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            continue

        meta_count += 1

        # 提取原始笔记
        source = extract_source_note_from_meta(content, meta_file[:-3])
        if not source:
            no_source += 1
            continue

        # 提取建议关联
        suggested = extract_suggested_links(content)

        for related in suggested:
            if related == source:
                continue
            # 过滤系统目录
            if is_system_note(source) or is_system_note(related):
                continue
            # 过滤不存在的笔记
            if not note_exists(source) or not note_exists(related):
                continue
            relations[source].add(related)
            relations[related].add(source)  # 双向

    return dict(relations), meta_count, no_source


def add_related_section(content, related_notes):
    """在笔记末尾添加/更新"🔗 相关笔记"部分"""
    valid_related = sorted([r for r in related_notes if note_exists(r) and not is_system_note(r)])
    if not valid_related:
        return content, False

    section = f"\n---\n\n## {RELATED_SECTION}\n\n"
    section += "> 由 AI RAG 插件自动发现的关联笔记，已自动建立双向链接。\n\n"
    for r in valid_related:
        display = os.path.basename(r).replace('.md', '')
        section += f"- [[{r}|{display}]]\n"
    section += "\n"

    if RELATED_SECTION in content:
        pattern = rf'## {re.escape(RELATED_SECTION)}.*?(?=\n## |\Z)'
        content = re.sub(pattern, section.strip() + '\n', content, flags=re.DOTALL)
    else:
        content = content.rstrip() + '\n' + section

    return content, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not args.dry_run and not args.apply:
        print("请指定 --dry-run 或 --apply")
        sys.exit(1)

    mode = "预览" if args.dry_run else "执行"
    print(f"{'='*60}")
    print(f"🔗 全量批量建立笔记双向链接 [{mode}]")
    print(f"{'='*60}")

    # 1. 解析所有Meta页面
    print(f"\n📊 解析所有Meta页面...")
    relations, meta_count, no_source = parse_all_meta()
    print(f"  Meta页面总数: {meta_count}")
    print(f"  无法识别原始笔记的Meta: {no_source}")
    print(f"  有关联建议的笔记: {len(relations)}")
    total_links = sum(len(v) for v in relations.values())
    print(f"  关联总数(含双向): {total_links}")

    # 2. 统计每个笔记的关联数
    print(f"\n📋 关联数最多的前15个笔记:")
    sorted_relations = sorted(relations.items(), key=lambda x: -len(x[1]))
    for source, related in sorted_relations[:15]:
        display = os.path.basename(source).replace('.md', '')
        if len(display) > 50:
            display = display[:47] + "..."
        print(f"  [{len(related):2d}个] {display}")

    # 3. 检查哪些已有"相关笔记"部分
    print(f"\n📝 检查已有关联部分...")
    already_has = 0
    will_modify = 0
    will_update = 0  # 已有但需要更新（关联数变了）

    for source, related in relations.items():
        full = get_full_path(source)
        try:
            with open(full, 'r', encoding='utf-8') as f:
                content = f.read()
            if RELATED_SECTION in content:
                already_has += 1
                # 检查现有链接数是否和建议数一致
                existing = re.findall(rf'## {re.escape(RELATED_SECTION)}.*?(?=\n## |\Z)', content, re.DOTALL)
                if existing:
                    existing_links = re.findall(r'\[\[([^\]]+)\]\]', existing[0])
                    if len(existing_links) != len(related):
                        will_update += 1
            else:
                will_modify += 1
        except Exception as e:
            print(f"  ⚠️ 读取失败 {source}: {e}")

    print(f"  已有相关笔记部分: {already_has}")
    print(f"  需要新增: {will_modify}")
    print(f"  需要更新(关联数变化): {will_update}")

    # 4. 执行
    if args.apply:
        print(f"\n⚡ 开始执行...")
        success = 0
        failed = 0
        skipped = 0

        for source, related in relations.items():
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
                    skipped += 1
            except Exception as e:
                print(f"  ❌ 失败 {source}: {e}")
                failed += 1

        print(f"\n{'='*60}")
        print(f"✅ 执行完成！")
        print(f"  成功修改: {success} 个笔记")
        print(f"  跳过(无有效关联): {skipped}")
        print(f"  失败: {failed}")
        print(f"{'='*60}")
    else:
        print(f"\n💡 这是预览模式，没有修改任何文件。")
        print(f"   确认无误后运行: python auto_link_all.py --apply")


if __name__ == "__main__":
    main()
