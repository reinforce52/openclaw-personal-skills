#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_libraries.py — 确定性扫描 Obsidian 库，提取"能力证据"。
不依赖 LLM：只解析 frontmatter / 文件名 / 目录 / 字数 / 代码块 / 双链 / 修改时间，可复算、可溯源。

输出：文件级证据列表 list[dict]，供 update_mastery.py 聚合。
也可单独运行打印扫描概览：
  python scan_libraries.py --root "E:/obsidian/rein" --extra "E:/obsidian/考研英语长难句"
"""
import os, re, json, argparse, datetime

# 扫描根之外的额外学习库
DEFAULT_EXTRA = [r"E:\obsidian\考研英语长难句"]
# 排除目录（不参与能力评估）
EXCLUDE_DIRS = {".obsidian", "_个人镜像", "非学习内容", ".trash", "node_modules", ".git"}
# 简历/求职类目录单独归类、不计入学科掌握
JOB_DIR_HINTS = ("简历", "求职", "职位")

# 领域规则：(标准领域, 关键词)；按顺序，先命中先归（具体领域放前面）
DOMAIN_RULES = [
    ("控制工程", ["自动控制原理", "控制工程", "自控", "胡寿松", "传递函数", "根轨迹", "伯德", "bode", "pid控制", "校正", "稳定性判据"]),
    ("机器视觉", ["机器视觉", "opencv", "yolo", "裂纹", "crack", "目标检测", "图像分割", "canny", "orb", "特征提取", "计算机视觉"]),
    ("AI与深度学习", ["神经网络", "深度学习", "pytorch", "tensorflow", "大模型", "llm", "minimind", "transformer", "注意力", "机器学习", "反向传播", "梯度", "bert"]),
    ("数学", ["高数", "高等数学", "线性代数", "线代", "概率", "微积分", "数学", "统计", "stat", "berkeley", "级数", "积分"]),
    ("英语六级", ["英语六级", "六级", "cet-6", "cet6", "长难句", "听力", "词汇", "单词", "阅读", "翻译", "写作", "语法", "六级备考", "口语"]),
    ("编程工程化", ["python", "git", "node", "部署", "自动化", "openclaw", "爬虫", "api", "环境配置", "脚本", "docker", "linux", "wsl"]),
    ("土木专业", ["土木", "结构力学", "材料力学", "工程测量", "岩土", "桥梁", "道路", "混凝土", "力学"]),
    ("考研规划", ["考研", "院校", "跨考", "复试", "专业选择", "学科认知", "初试科目", "备考规划"]),
]

FEYNMAN_HINTS = ("费曼", "精讲", "讲清楚", "用自己的话", "复盘总结")
# 导航/索引类文件：体现体系化梳理，但不是编程实践，代码围栏不算动手证据
NAV_HINTS = ("_moc", "_总览", "_知识谱系", "知识谱系", "索引", "index", "导航", "大纲", "目录", "moc", "图谱")
APPLY_HINTS = ("复现", "实战", "实现", "项目", "部署", "跑通", "动手")


def count_code_lines(body):
    """统计代码围栏内的真实代码行数（排除 mermaid/纯文本结构块）。"""
    total = 0
    blocks = re.findall(r"```([A-Za-z0-9_]*)\s*\n(.*?)```", body, re.DOTALL)
    for lang, code in blocks:
        if lang.lower() in ("mermaid", "text", "plain", ""):
            # 无语言标注且像结构图的不算代码；有真实编程语言才算
            if lang.lower() != "":
                total += len([l for l in code.splitlines() if l.strip()])
            continue
        total += len([l for l in code.splitlines() if l.strip()])
    return total


def parse_frontmatter(text):
    """简易解析 --- yaml --- 头部，返回 (meta_dict, body)。"""
    meta = {}
    if text.startswith("---"):
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
        if m:
            head, body = m.group(1), m.group(2)
            for line in head.splitlines():
                mm = re.match(r'^([A-Za-z_]+)\s*:\s*(.*)$', line)
                if mm:
                    k, v = mm.group(1), mm.group(2).strip()
                    v = re.sub(r'^["\']|["\']$', '', v)
                    meta[k.lower()] = v
            return meta, body
    return meta, text


def classify_domain(haystack, rel_dir):
    """根据 topic/tags/目录/文件名/正文关键词归类领域。"""
    h = haystack.lower()
    # 目录名先给一次机会（顶层主题目录通常最准）
    for dom, kws in DOMAIN_RULES:
        for kw in kws:
            if kw.lower() in h:
                return dom
    return "未分类"


def file_category(rel_path, meta, fname, text):
    """note / project / feynman / daily / job。"""
    p = rel_path.replace("\\", "/").lower()
    tags = (meta.get("tags", "") + " " + meta.get("topic", "")).lower()
    if "03-项目库" in p or "project_name" in meta or (meta.get("status", "") and "完成" in meta.get("status", "")):
        return "project"
    if "01-每日日志" in p or "每日学习记录" in tags:
        return "daily"
    if any(x in fname for x in JOB_DIR_HINTS):
        return "job"
    if any(x in fname for x in FEYNMAN_HINTS):  # 只认用户自己命名的费曼输出
        return "feynman"
    return "note"


def scan_root(root):
    evidence = []
    if not os.path.isdir(root):
        return evidence
    for dirpath, dirnames, filenames in os.walk(root):
        # 剪枝排除目录
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            try:
                with open(full, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                continue
            meta, body = parse_frontmatter(text)
            code_fences = len(re.findall(r"^```", body, re.MULTILINE))
            code_lines = count_code_lines(body)
            h2 = len(re.findall(r"^#{2,3}\s", body, re.MULTILINE))
            wikilinks = len(re.findall(r"\[\[", body))
            char_n = len(re.sub(r"\s", "", body))
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(full))
            cat = file_category(rel, meta, fn, text)
            is_nav = any(x in fn.lower() for x in NAV_HINTS)
            tag_blob = (meta.get("tags", "") + " " + meta.get("topic", "") + " " + fn).lower()
            is_course = bool(meta.get("platform")) or any(
                x in tag_blob for x in ["视频笔记", "课程", "bilibili", "youtube", "抖音", "网课"])
            hay = " ".join([meta.get("topic", ""), meta.get("tags", ""),
                            rel.replace("\\", " "), fn, body[:300]])
            is_job_path = any(x in rel.replace("\\", "/") for x in JOB_DIR_HINTS)
            domain = "求职" if (cat == "job" or is_job_path) else classify_domain(hay, os.path.dirname(rel))
            evidence.append({
                "file": rel.replace("\\", "/"),
                "domain": domain,
                "category": cat,
                "title": (meta.get("title") or fn[:-3]).strip()[:60],
                "tags": meta.get("tags", ""),
                "topic": meta.get("topic", ""),
                "status": meta.get("status", ""),
                "chars": char_n,
                "code_fences": code_fences,
                "code_lines": code_lines,
                "is_nav": is_nav,
                "h2_count": h2,
                "wikilinks": wikilinks,
                "mtime": mtime.strftime("%Y-%m-%d %H:%M"),
                "mtime_iso": mtime.isoformat(),
                "feynman": cat == "feynman" or any(x in fn for x in FEYNMAN_HINTS),
                "is_course": is_course,
                "apply_signal": (code_fences >= 2) or (cat == "project") or
                                any(x in text[:600] for x in APPLY_HINTS),
            })
    return evidence


def scan(roots):
    all_ev, seen = [], set()
    for r in roots:
        for e in scan_root(r):
            key = e["file"]
            if key in seen:
                continue
            seen.add(key)
            all_ev.append(e)
    return all_ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"E:\obsidian\rein")
    ap.add_argument("--extra", nargs="*", default=DEFAULT_EXTRA)
    ap.add_argument("--out", default=None, help="写出原始证据 JSON")
    args = ap.parse_args()
    roots = [args.root] + [x for x in (args.extra or []) if os.path.isdir(x)]
    ev = scan(roots)
    # 概览
    by_dom, by_cat = {}, {}
    for e in ev:
        by_dom[e["domain"]] = by_dom.get(e["domain"], 0) + 1
        by_cat[e["category"]] = by_cat.get(e["category"], 0) + 1
    print(f"扫描根: {roots}")
    print(f"共 {len(ev)} 个 md 证据点")
    print("按领域:", dict(sorted(by_dom.items(), key=lambda x: -x[1])))
    print("按类型:", by_cat)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(ev, f, ensure_ascii=False, indent=2)
        print("已写:", args.out)


if __name__ == "__main__":
    main()
