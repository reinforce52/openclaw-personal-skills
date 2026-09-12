#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从画像文件抽取 ≤1500 字《_注入摘要.md》，用于同步 openwave self-model。
用法: python build_injection.py --vault "E:/obsidian/rein/_个人镜像"
稳健抽取：缺文件/缺段落时留占位，不报错中断。
"""
import argparse, os, re, sys
from datetime import datetime

BUDGET = 1500  # 字


def read(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def section(md, header_keyword, max_lines=12):
    """抽取包含某关键词的标题下内容；遇到同级或更高级标题才结束，更深的子标题继续。"""
    if not md:
        return []
    lines = md.splitlines()
    out, capture, base_level = [], False, 99
    for ln in lines:
        m = re.match(r"^(#{2,4})\s", ln)
        if m:
            lvl = len(m.group(1))
            if capture and lvl <= base_level:
                break  # 同级/更高级标题 → 本段结束
            if header_keyword in ln:
                capture, base_level = True, lvl
            continue
        if capture and ln.strip():
            t = ln.strip()
            if t == "-":
                continue  # 孤立空项
            if re.search(r"[：:]\s*$", t) and not t.startswith("|"):
                continue  # "标签："后无内容的空占位（保留表格行）
            out.append(t)
            if len(out) >= max_lines:
                break
    return out


def collect_hotspots(error_md, limit=5):
    """从03错题日志提取 🔺 高频坑点与最近标题。"""
    # 先剔除 HTML 注释（里面是模板示例，不是真实记录）
    error_md = re.sub(r"<!--[\s\S]*?-->", "", error_md)
    hot, recent = [], []
    for ln in error_md.splitlines():
        s = ln.strip()
        if s.startswith("## [") and "YYYY" not in s:  # 排除占位模板
            recent.append(s.lstrip("# ").strip())
        # 只把"列表项里、且非汇总区占位"的 🔺 当坑点，排除 ## 🔺汇总标题
        if s.startswith("-") and "🔺" in s and "自动汇总" not in s and "暂无" not in s:
            hot.append(s.lstrip("- ").strip())
    # 去重保序
    def uniq(seq):
        seen, r = set(), []
        for x in seq:
            if x not in seen:
                seen.add(x); r.append(x)
        return r
    return uniq(hot)[:limit], uniq(recent)[:limit]


def build(vault):
    p00 = read(os.path.join(vault, "00_我的档案.md"))
    p01 = read(os.path.join(vault, "01_能力画像.md"))
    p02 = read(os.path.join(vault, "02_认知与人格画像.md"))
    p03 = read(os.path.join(vault, "03_错题卡点日志.md"))

    goals = section(p00, "目标", 10)
    constraints = section(p00, "硬约束", 6)
    prefs = section(p00, "偏好与禁忌", 8)
    overview = section(p01, "总览", 10)
    weak = section(p01, "最该补", 5)
    serve = section(p02, "最佳服务方式", 10)
    style = section(p02, "学习风格", 4)
    hot, recent_err = collect_hotspots(p03)

    L = []
    L.append("# 关于我的一句话画像")
    L.append("- 中南大学土木工程大三，跨考控制工程（土木基建×机器视觉方向），不读博、不走施工现场，当前考研优先。")
    L.append("")
    L.append("# 当前核心目标")
    L.extend(("- " + g if not g.startswith("-") else g) for g in goals) if goals else L.append("- 待在 00_我的档案.md 补充")
    L.append("")
    L.append("# 各领域熟悉度速览")
    L.extend(overview) if overview else L.append("- 待 P1 扫描后生成")
    if weak:
        L.append("- **当前最该补的短板：**")
        L.extend(weak)
    L.append("")
    L.append("# 学习风格与最佳服务方式")
    L.extend(style) if style else None
    L.extend(serve) if serve else L.append("- 待量表完成后生成")
    L.append("")
    L.append("# 高频坑点 TOP（≤5）")
    if hot:
        L.extend("- " + h for h in hot)
    elif recent_err:
        L.append("- 近期卡点：")
        L.extend("  - " + e for e in recent_err)
    else:
        L.append("- 暂无（通过【记录卡点】积累）")
    L.append("")
    L.append("# 偏好与硬约束")
    L.extend(prefs) if prefs else None
    L.extend(constraints) if constraints else L.append("- 不走施工现场、不读博")

    text = "\n".join(x for x in L if x is not None).strip()
    header = ("---\ntype: 注入摘要\nupdated: \"%s\"\nnote: 自动生成，≤1500字，同步 openwave self-model；勿手改\n---\n\n"
              % datetime.now().strftime("%Y-%m-%d %H:%M"))
    # 总长（含 header 与截断省略号）控制在 BUDGET 内
    ELLIPSIS = "\n…（详见画像文件）"
    remain = BUDGET - len(header) - len(ELLIPSIS)
    if len(text) > remain:
        text = text[:remain].rstrip() + ELLIPSIS
    return header + text + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=r"E:\obsidian\rein\_个人镜像")
    ap.add_argument("--print", action="store_true", help="只打印不写文件")
    args = ap.parse_args()
    summary = build(args.vault)
    if args.print:
        print(summary)
        return
    out = os.path.join(args.vault, "_注入摘要.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"✅ 注入摘要已生成: {out}（{len(summary)} 字）")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("❌ 生成失败:", e, file=sys.stderr); sys.exit(1)
