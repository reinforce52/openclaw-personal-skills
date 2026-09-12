#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简历生成主流程 - 串联：扫描知识库 → 生成简历 → 导出 PDF/Word → 写入 Obsidian
用法: python pipeline.py --role "机器视觉工程师" --jd jd.txt
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")

# 输出目录（Obsidian 简历库）
OUTPUT_BASE = r"E:\obsidian\rein\简历库"


def run_script(script_name: str, args: list, timeout: int = 300) -> tuple:
    """运行子脚本"""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    cmd = [sys.executable, script_path] + args
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return result.returncode, result.stdout, result.stderr


def main():
    parser = argparse.ArgumentParser(description="简历生成主流程")
    parser.add_argument("--role", "-r", help="目标岗位名称", required=True)
    parser.add_argument("--jd", "-j", help="JD 文本文件路径（可选，不提供则生成通用简历）", default=None)
    parser.add_argument("--personal", "-p", help="个人信息配置路径", default=None)
    parser.add_argument("--skip-scan", action="store_true", help="跳过扫描，使用已有 scan_result.json")
    parser.add_argument("--no-export", action="store_true", help="只生成 Markdown，不导出 PDF/Word")
    args = parser.parse_args()

    role = args.role
    date_str = datetime.now().strftime("%Y-%m-%d")
    role_safe = role.replace("/", "_").replace(" ", "_")[:30]

    # 输出目录
    output_dir = os.path.join(OUTPUT_BASE, f"{role_safe}_{date_str}")
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print(f"📋 简历生成主流程")
    print(f"   目标岗位: {role}")
    print(f"   输出目录: {output_dir}")
    print("=" * 60)

    # ===== 步骤1: 扫描知识库 =====
    scan_result_path = os.path.join(SKILL_DIR, "scan_result.json")
    if not args.skip_scan or not os.path.exists(scan_result_path):
        print("\n[步骤 1/4] 扫描知识库...")
        rc, stdout, stderr = run_script("scan_knowledge.py", ["--output", scan_result_path], timeout=120)
        if rc != 0:
            print(f"❌ 扫描失败: {stderr[-500:]}", file=sys.stderr)
            sys.exit(1)
        print("  ✅ 扫描完成")
    else:
        print("\n[步骤 1/4] 跳过扫描，使用已有结果")

    # ===== 步骤2: 生成简历 Markdown =====
    print("\n[步骤 2/4] 生成简历 Markdown...")
    md_path = os.path.join(output_dir, f"简历_{role_safe}_{date_str}.md")

    gen_args = ["--scan", scan_result_path, "--role", role, "--output", md_path]
    if args.jd:
        gen_args.extend(["--jd", args.jd])
    if args.personal:
        gen_args.extend(["--personal", args.personal])

    rc, stdout, stderr = run_script("generate_resume.py", gen_args, timeout=300)
    if rc != 0:
        print(f"❌ 简历生成失败: {stderr[-500:]}\nstdout: {stdout[-500:]}", file=sys.stderr)
        sys.exit(1)
    print(f"  ✅ 简历已生成: {md_path}")

    # ===== 步骤3: 导出 PDF + Word =====
    if not args.no_export:
        print("\n[步骤 3/4] 导出 PDF...")
        pdf_path = os.path.join(output_dir, f"简历_{role_safe}_{date_str}.pdf")
        rc, stdout, stderr = run_script("export_pdf.py", [md_path, "--output", pdf_path], timeout=120)
        if rc != 0:
            print(f"  ⚠️ PDF 导出失败: {stderr[-300:]}")
        else:
            print(f"  ✅ PDF 已导出")

        print("\n[步骤 3/4] 导出 Word...")
        docx_path = os.path.join(output_dir, f"简历_{role_safe}_{date_str}.docx")
        rc, stdout, stderr = run_script("export_docx.py", [md_path, "--output", docx_path], timeout=120)
        if rc != 0:
            print(f"  ⚠️ Word 导出失败: {stderr[-300:]}")
        else:
            print(f"  ✅ Word 已导出")
    else:
        print("\n[步骤 3/4] 跳过导出")

    # ===== 步骤4: 完成报告 =====
    print("\n" + "=" * 60)
    print("✅ 全部完成！")
    print("=" * 60)
    print(f"  输出目录: {output_dir}")
    print(f"  Markdown: {md_path}")
    if not args.no_export:
        print(f"  PDF: {os.path.join(output_dir, f'简历_{role_safe}_{date_str}.pdf')}")
        print(f"  Word: {os.path.join(output_dir, f'简历_{role_safe}_{date_str}.docx')}")
    print(f"\n  提示: 个人信息如未填写，请编辑 {os.path.join(SKILL_DIR, 'config', 'personal_info.json')}")

    # 输出 JSON 结果
    result = {
        "success": True,
        "role": role,
        "output_dir": output_dir,
        "markdown": md_path,
        "pdf": os.path.join(output_dir, f"简历_{role_safe}_{date_str}.pdf") if not args.no_export else None,
        "docx": os.path.join(output_dir, f"简历_{role_safe}_{date_str}.docx") if not args.no_export else None,
    }
    print(f"\n---JSON---\n{json.dumps(result, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
