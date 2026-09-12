#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
harvest_clean.py v3 — MediaCrawler 多平台多关键词采集清洗器（topic-knowledge-base 社媒信源分支）

把 MediaCrawler 落盘的 jsonl（search_contents + search_comments）清洗成"素材包.md"：
只提取硬货（视频清单 / 课程目录 / 易错纠错 / 经验心得 / 资料链接），丢弃噪音
（三连打卡、求资料、无意义短评、重复评论）。

v3 特性：
- 支持多平台（--root 自动扫描 / --dir 逗号分隔）
- 支持同一天多关键词混文件：按 source_keyword 自动分组（视频按 source_keyword，
  评论按 video_id 映射归属）
- 每关键词每平台独立素材包；同一关键词跨 ≥2 平台时生成融合数据包
  fuse_<关键词>_<日期>.md（跨平台同源去重 + 平台分布统计），供建库 LLM 做
  "多平台视角"融合分析（共识/分歧/互补）。

用法:
  # 单平台（指定 jsonl 目录）
  python harvest_clean.py --dir <jsonl目录>
  # 多平台（逗号分隔多个目录）
  python harvest_clean.py --dir "<目录1>,<目录2>,..."
  # 自动扫描 MediaCrawler data 根目录下所有平台的 jsonl
  python harvest_clean.py --root <MediaCrawler data根目录，如 E:/tools/MediaCrawler/data>
"""
import argparse
import datetime
import json
import os
import re
import sys

# ---------- 平台名 ----------
PLATFORM_NAMES = {
    "bili": "B站", "zhihu": "知乎", "dy": "抖音", "douyin": "抖音", "xhs": "小红书",
    "ks": "快手", "kuaishou": "快手", "wb": "微博", "tieba": "贴吧",
}

# ---------- 硬货分类规则 ----------
PATTERNS = {
    "资料链接": [
        "网盘", "链接", "提取码", "讲义", "ppt", "课件", "答案", "获取",
        "私信", "b23.tv", "pan.baidu", "夸克", "资料", "教材", "pdf",
    ],
    "课程目录": [
        "目录", "第\\s*[0-9一二三四五六七八九十]+\\s*讲", "第\\s*[0-9一二三四五六七八九十]+\\s*章",
        "第\\s*[0-9一二三四五六七八九十]+\\s*节", "总结", "梳理", "体系", "知识点",
        "框架", "导图", "课程内容", "学习路线", "章节", "大纲", "目录供参考",
    ],
    "易错纠错": [
        "注意", "错误", "修正", "纠正", "区别", "不是", "补充", "勘误", "陷阱",
        "易错", "细节", "争议", "更正", "混淆", "反例", "提醒", "别踩",
    ],
    "经验心得": [
        "考研", "跨考", "上岸", "考了", "复习", "经验", "学完", "刷题", "复试",
        "期末", "突击", "零基础", "基础", "补考", "重修", "学习", "时间", "规划",
        "心得", "建议", "来得及", "进度", "踩坑",
    ],
}
NOISE_PATTERNS = [
    "三连", "打卡", "求讲义", "求资料", "已关注", "一键三连", "谢谢", "支持",
    "顶", "马克", "收藏", "蹲", "滴滴", "占楼", "路过", "哈哈", "哈哈哈",
    "已三连", "求课件", "求私信",
]
MIN_LEN = 8
MAX_LEN = 600
URL_RE = re.compile(r"https?://\S+|b23\.tv\S+|pan\.\w+\.\w+/\S+", re.I)
QUESTION_RE = re.compile(r"(吗|呢|？|\?|有什么区别|能不能|怎么|为啥|为什么|求教|求解答)", re.I)
FLUFF_RE = re.compile(r"(打卡|路过|收藏了|已三连|打个卡|顶一下|留个名|前排|沙发)", re.I)


def classify(text: str) -> str:
    """返回硬货分类：资料链接/课程目录/易错纠错/经验心得/None(噪音)"""
    t = text.lower()
    if len(text) < 40:
        for n in NOISE_PATTERNS:
            if n.lower() in t:
                return None
    if FLUFF_RE.search(t) and not URL_RE.search(text):
        for k in ("课程目录", "易错纠错"):
            if any(re.search(p, t) for p in PATTERNS[k]):
                break
        else:
            return None
    if QUESTION_RE.search(t) and len(text) < 60 and not URL_RE.search(text):
        if not any(re.search(p, t) for p in PATTERNS["易错纠错"]):
            return None
    scores = {}
    for cat, pats in PATTERNS.items():
        s = sum(1 for p in pats if re.search(p, t))
        if s:
            scores[cat] = s
    if not scores:
        return "资料链接" if URL_RE.search(text) else None
    if "资料链接" in scores:
        return "资料链接"
    return max(scores, key=scores.get)


def load_jsonl(path: str):
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        return None
    return rows


def pick_latest(directory: str, prefix: str):
    try:
        cands = [os.path.join(directory, f) for f in os.listdir(directory)
                 if f.startswith(prefix) and f.endswith(".jsonl")]
    except FileNotFoundError:
        return None
    if not cands:
        return None
    return max(cands, key=os.path.getmtime)


def short(s: str, n=MAX_LEN) -> str:
    s = s.strip().replace("\r", " ").replace("\n", " ")
    return s[:n] + ("…" if len(s) > n else "")


def safe_name(s: str) -> str:
    return re.sub(r"[\\/:*?"<>|\s]+", "-", s).strip("-") or "topic"


def detect_platform(directory: str) -> str:
    full = directory.replace("\\", "/")
    for key in PLATFORM_NAMES:
        if "/%s/" % key in full + "/" or full.endswith("/" + key):
            return key
    parent = os.path.basename(os.path.normpath(os.path.dirname(directory)))
    if parent in PLATFORM_NAMES:
        return parent
    return ""


def build_result(platform: str, keyword: str, videos: list, comments: list) -> dict:
    video_rows = []
    for i, v in enumerate(videos, 1):
        video_rows.append({
            "title": short(v.get("title") or "", 80),
            "nickname": short(v.get("nickname") or "?", 20),
            "play": v.get("video_play_count") or "",
            "url": v.get("video_url") or "",
            "desc": short(v.get("desc") or "", 150),
        })

    buckets = {"课程目录": [], "易错纠错": [], "经验心得": [], "资料链接": []}
    seen = set()
    dropped = 0
    for c in comments:
        content = c.get("content") or ""
        if len(content.strip()) < MIN_LEN and not URL_RE.search(content):
            dropped += 1
            continue
        cat = classify(content)
        if cat is None:
            dropped += 1
            continue
        key = content.strip()
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
        buckets[cat].append(short(content))

    return {
        "platform": platform,
        "keyword": keyword,
        "videos": video_rows,
        "buckets": buckets,
        "dropped": dropped,
        "comments_total": len(comments),
    }


def scan_dir(directory: str) -> list:
    """扫描单个 jsonl 目录，按 source_keyword 分组返回 result dict 列表"""
    content_path = pick_latest(directory, "search_contents")
    comment_path = pick_latest(directory, "search_comments")
    if not content_path:
        return []
    videos = load_jsonl(content_path) or []
    comments = load_jsonl(comment_path) if comment_path else []
    if not videos:
        return []
    platform = detect_platform(directory)

    # 视频按关键词分组
    by_kw = {}
    for v in videos:
        kw = (v.get("source_keyword") or "").strip()
        if kw:
            by_kw.setdefault(kw, []).append(v)

    # 评论按 video_id 归属到关键词
    vmap = {str(v.get("video_id")): (v.get("source_keyword") or "").strip() for v in videos}
    com_by_kw = {}
    for c in comments:
        kw = vmap.get(str(c.get("video_id")), "")
        if kw:
            com_by_kw.setdefault(kw, []).append(c)

    results = []
    for kw, vids in by_kw.items():
        results.append(build_result(platform, kw, vids, com_by_kw.get(kw, [])))
    return results


def write_platform_md(result: dict, out_dir: str, date: str) -> str:
    """写单平台素材包，返回文件路径"""
    keyword = result["keyword"]
    platform = result["platform"]
    videos = result["videos"]
    buckets = result["buckets"]
    total_hard = sum(len(v) for v in buckets.values())

    pname = PLATFORM_NAMES.get(platform, platform or "未知平台")
    L = [f"# 社媒采集素材：{keyword}（{pname}）", ""]
    L.append(f"> 采集日期：{date} ｜ 来源：MediaCrawler-{platform or '?'} ｜ "
             f"视频 **{len(videos)}** 条 ｜ 评论 **{result['comments_total']}** 条 ｜ 硬货 **{total_hard}** 条（丢弃 {result['dropped']}）")
    L.append("")
    L.append("## 1. 视频/内容清单")
    L.append("")
    if videos:
        L.append("| # | 标题 | UP主 | 播放 | 链接 |")
        L.append("|---|------|------|------|------|")
        for i, v in enumerate(videos, 1):
            L.append(f"| {i} | {v['title']} | {v['nickname']} | {v['play']} | {v['url']} |")
    else:
        L.append("（无数据）")
    L.append("")

    for cat, label in [("课程目录", "课程目录与知识框架"), ("易错纠错", "易错与纠错"),
                       ("经验心得", "经验心得"), ("资料链接", "资料链接")]:
        L.append(f"## {label}")
        L.append("")
        items = buckets[cat]
        if not items:
            L.append("（无）")
        else:
            for it in items:
                L.append(f"- {it}")
        L.append("")

    L.append("---")
    L.append("> 由 harvest_clean.py 自动清洗，仅供自用学习建库。")

    fname = f"harvest_{safe_name(keyword)}_{pname}_{date}.md"
    path = os.path.join(out_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return path


def write_fusion_md(results: list, keyword: str, date: str, out_dir: str) -> str:
    """写跨平台融合数据包（去重 + 平台分布），返回文件路径"""
    L = [f"# 媒体融合数据包：{keyword}", ""]
    total_v = sum(len(r["videos"]) for r in results)
    total_h = sum(sum(len(v) for v in r["buckets"].values()) for r in results)

    L.append(f"> 采集日期：{date} ｜ 平台 **{len(results)}** 个 ｜ "
             f"内容合计 **{total_v}** 条 ｜ 硬货合计 **{total_h}** 条")
    L.append("")
    L.append("## 1. 平台覆盖总览")
    L.append("")
    L.append("| 平台 | 内容数 | 硬货(目录/纠错/经验/资料) |")
    L.append("|------|--------|--------------------------|")
    for r in results:
        pname = PLATFORM_NAMES.get(r["platform"], r["platform"] or "?")
        b = r["buckets"]
        L.append(f"| {pname} | {len(r['videos'])} | {sum(len(v) for v in b.values())} "
                 f"({len(b['课程目录'])}/{len(b['易错纠错'])}/{len(b['经验心得'])}/{len(b['资料链接'])}) |")
    L.append("")

    # 跨平台内容去重（按标题前 24 字）
    def title_key(t):
        return re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]", "", t)[:24]

    seen = {}
    for r in results:
        pname = PLATFORM_NAMES.get(r["platform"], r["platform"] or "?")
        for v in r["videos"]:
            k = title_key(v["title"])
            if not k:
                continue
            if k not in seen:
                seen[k] = {"platforms": [pname], "title": v["title"], "url": v["url"]}
            else:
                seen[k]["platforms"].append(pname)

    dup = [v for v in seen.values() if len(v["platforms"]) > 1]
    L.append("## 2. 跨平台同源内容（多平台出现 = 高关注度，建库重点）")
    L.append("")
    if dup:
        for v in dup:
            L.append(f"- **{v['title']}**（{ ' + '.join(v['platforms']) }）{v['url']}")
    else:
        L.append("（本次无跨平台同源内容）")
    L.append("")

    # 按硬货类别汇总各平台条目（带平台前缀，供 LLM 融合）
    for cat, label in [("课程目录", "课程目录（跨平台合并，建谱系主干）"),
                       ("易错纠错", "易错与纠错（跨平台合并，标分歧）"),
                       ("经验心得", "经验心得（跨平台合并）"),
                       ("资料链接", "资料链接（跨平台合并）")]:
        L.append(f"## {label}")
        L.append("")
        for r in results:
            pname = PLATFORM_NAMES.get(r["platform"], r["platform"] or "?")
            items = r["buckets"][cat]
            if not items:
                continue
            for it in items:
                L.append(f"- [{pname}] {it}")
        L.append("")

    L.append("---")
    L.append("> 融合数据包由 harvest_clean.py 自动生成；共识/分歧/互补的最终分析由建库 LLM 在 _媒体融合.md 中完成。")

    fname = f"fuse_{safe_name(keyword)}_{date}.md"
    path = os.path.join(out_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return path


def main():
    ap = argparse.ArgumentParser(description="MediaCrawler 多平台多关键词 jsonl 清洗 → 素材包 + 融合数据包")
    ap.add_argument("--dir", default=None, help="jsonl 目录，多个用英文逗号分隔")
    ap.add_argument("--root", default=None, help="MediaCrawler data 根目录，自动扫描各平台")
    ap.add_argument("--out", default=None, help="输出目录（默认各 jsonl 所在目录）")
    args = ap.parse_args()

    if not args.dir and not args.root:
        ap.error("必须提供 --dir 或 --root")

    dirs = []
    if args.root:
        if not os.path.isdir(args.root):
            print(f"❌ root 不存在: {args.root}", file=sys.stderr)
            sys.exit(1)
        for platform_dir in os.listdir(args.root):
            jdir = os.path.join(args.root, platform_dir, "jsonl")
            if os.path.isdir(jdir) and any(f.startswith("search_contents") and f.endswith(".jsonl") for f in os.listdir(jdir)):
                dirs.append(jdir)
        if not dirs:
            print(f"❌ root 下未找到任何平台的 jsonl（{args.root}）", file=sys.stderr)
            sys.exit(1)
    else:
        dirs = [d.strip() for d in args.dir.split(",") if d.strip()]

    date = datetime.datetime.now().strftime("%Y-%m-%d")

    # 收集所有 (platform, keyword) 结果
    all_results = []
    for d in dirs:
        if not os.path.isdir(d):
            print(f"⚠️ 跳过不存在目录: {d}", file=sys.stderr)
            continue
        results = scan_dir(d)
        if not results:
            print(f"⚠️ 该目录无有效 jsonl: {d}", file=sys.stderr)
            continue
        out_dir = args.out or d
        for r in results:
            path = write_platform_md(r, out_dir, date)
            pname = PLATFORM_NAMES.get(r["platform"], r["platform"] or "?")
            total_h = sum(len(v) for v in r["buckets"].values())
            print(f"✅ [{pname}] {r['keyword']}: {path}")
            print(f"   视频 {len(r['videos'])} | 评论 {r['comments_total']} → 硬货 {total_h}"
                  f"（目录 {len(r['buckets']['课程目录'])} / 纠错 {len(r['buckets']['易错纠错'])}"
                  f" / 经验 {len(r['buckets']['经验心得'])} / 资料 {len(r['buckets']['资料链接'])}）| 丢弃 {r['dropped']}")
            all_results.append(r)

    if not all_results:
        print("❌ 没有成功清洗任何数据", file=sys.stderr)
        sys.exit(1)

    # 按关键词分组，跨平台生成融合包
    by_kw = {}
    for r in all_results:
        by_kw.setdefault(r["keyword"], []).append(r)
    for kw, results in by_kw.items():
        if len(results) >= 2:
            out_dir = args.out or os.path.dirname(dirs[0])
            fuse_path = write_fusion_md(results, kw, date, out_dir)
            platforms = " + ".join(PLATFORM_NAMES.get(r["platform"], r["platform"] or "?") for r in results)
            print(f"\n✅ 融合数据包 [{kw}]（{platforms}）: {fuse_path}")
            print(f"   请在建库时读取全部素材包 + 融合数据包，做多平台视角分析")


if __name__ == "__main__":
    main()
