#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_update.py - 概念层一键自动更新
流程：扫描所有笔记 → 核心概念全文匹配 → 生成概念页+图谱 → 更新掌握度
用法:
  python auto_update.py --vault "E:/obsidian/rein"
  python auto_update.py --incremental --hours 1  # 增量模式：只扫描最近1小时修改的文件，无变化则跳过
  或在 OpenClaw 中说【更新概念层】
"""
import os, sys, subprocess, argparse, json
from datetime import datetime, timedelta

VAULT_BASE = r"E:\obsidian\rein"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = r"E:\openclaw-video-temp"
STATE_FILE = os.path.join(TEMP_DIR, "concept_update_state.json")


def check_incremental(vault, hours):
    """增量检测：检查最近N小时是否有新/修改的 .md 文件
    返回 (has_changes, changed_files, last_check_time)
    """
    cutoff = datetime.now() - timedelta(hours=hours)
    changed = []

    # 读取上次检查时间
    last_check = None
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
                last_check = datetime.fromisoformat(state.get("last_check", ""))
        except Exception:
            pass

    # 扫描所有 .md 文件（排除系统目录）
    exclude_dirs = {"_概念层", "_templates", "_vault-health", ".obsidian", "00-系统导航"}
    for root, dirs, files in os.walk(vault):
        # 排除系统目录
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
        for fname in files:
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(root, fname)
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                if mtime > cutoff:
                    rel = os.path.relpath(fpath, vault)
                    changed.append(rel)
            except Exception:
                pass

    # 保存检查时间
    os.makedirs(TEMP_DIR, exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump({"last_check": datetime.now().isoformat(), "last_changed_count": len(changed)}, f, ensure_ascii=False, indent=2)

    return len(changed) > 0, changed, last_check


def run_step(name, cmd):
    """运行一个步骤"""
    print(f"\n{'='*60}")
    print(f"▶ 步骤: {name}")
    print(f"  命令: {' '.join(cmd)}")
    print(f"{'='*60}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
        print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr[-500:])
        if result.returncode != 0:
            print(f"⚠️ 步骤返回码: {result.returncode}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"❌ 步骤超时（>300秒）")
        return False
    except Exception as e:
        print(f"❌ 步骤失败: {e}")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=VAULT_BASE)
    ap.add_argument("--skip-mastery", action="store_true", help="跳过掌握度更新")
    ap.add_argument("--incremental", action="store_true", help="增量模式：只扫描最近修改的文件，无变化则跳过")
    ap.add_argument("--hours", type=int, default=1, help="增量模式：检查最近N小时（默认1小时）")
    args = ap.parse_args()

    python = sys.executable
    start_time = datetime.now()

    print("=" * 60)
    print("🔄 概念层一键自动更新")
    print(f"  Vault: {args.vault}")
    print(f"  模式: {'增量检测（最近' + str(args.hours) + '小时）' if args.incremental else '全量更新'}")
    print(f"  开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 增量模式：先检测是否有变化
    if args.incremental:
        print("\n🔍 增量检测中...")
        has_changes, changed_files, last_check = check_incremental(args.vault, args.hours)
        if last_check:
            print(f"  上次检查: {last_check.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  最近{args.hours}小时修改的文件: {len(changed_files)}个")
        if changed_files:
            for f in changed_files[:10]:
                print(f"    - {f}")
            if len(changed_files) > 10:
                print(f"    ... 还有 {len(changed_files)-10} 个")

        if not has_changes:
            print("\n✅ 无变化，跳过概念层更新（节省资源）")
            print("=" * 60)
            return

        print(f"\n▶ 检测到 {len(changed_files)} 个文件变化，开始更新...")

    # 步骤1：核心概念全文匹配
    matched_file = os.path.join(TEMP_DIR, "concepts_matched.json")
    step1_ok = run_step(
        "核心概念全文匹配（46概念种子）",
        [python, os.path.join(SCRIPT_DIR, "concept_matcher.py"),
         "--vault", args.vault, "--output", matched_file]
    )

    if not step1_ok:
        print("\n❌ 概念匹配失败，终止更新")
        sys.exit(1)

    # 步骤2：生成概念页和概念图谱
    step2_ok = run_step(
        "生成概念页（46个）+ 概念图谱",
        [python, os.path.join(SCRIPT_DIR, "concept_page_builder.py"),
         "--input", matched_file, "--output-dir", os.path.join(args.vault, "_概念层")]
    )

    if not step2_ok:
        print("\n❌ 概念页生成失败，终止更新")
        sys.exit(1)

    # 步骤3：更新掌握度
    if not args.skip_mastery:
        step3_ok = run_step(
            "更新概念掌握度（结合 personal-twin）",
            [python, os.path.join(SCRIPT_DIR, "update_mastery.py"),
             "--vault", args.vault]
        )
    else:
        print("\n⏭️ 跳过掌握度更新")
        step3_ok = True

    # 完成
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"\n{'='*60}")
    print(f"✅ 概念层更新完成！")
    print(f"  耗时: {duration:.1f}秒")
    print(f"  概念页: {os.path.join(args.vault, '_概念层', 'concepts')}")
    print(f"  概念图谱: {os.path.join(args.vault, '_概念层', '_概念图谱.md')}")
    print(f"  掌握度总览: {os.path.join(args.vault, '_概念层', '_掌握度总览.md')}")
    print(f"{'='*60}")

    # 建议运行体检
    print("\n💡 建议：运行【知识库体检】检查死链和重复")


if __name__ == "__main__":
    main()
