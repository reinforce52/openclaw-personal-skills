#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_mastery.py — personal-twin 能力画像主入口（确定性、可复算，不用 LLM）。
流程：scan_libraries 扫描 → 文件级 0-4 评级 → 领域聚合 → 关联错题卡点 → 时间衰减
     → 写 mastery_data.json + 01_能力画像.md；--full 额外存快照并追加 04_成长轨迹。

用法:
  python update_mastery.py --full          # 每周全量：重算+快照+成长轨迹
  python update_mastery.py                 # 每日增量：重算（确定性很快）+记录今日新增
"""
import os, re, json, argparse, datetime, sys, glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_libraries import scan, DEFAULT_EXTRA  # noqa

VAULT = r"E:\obsidian\rein\_个人镜像"
SCAN_ROOT = r"E:\obsidian\rein"
CORE = ["控制工程", "机器视觉", "AI与深度学习", "数学", "英语六级", "编程工程化"]
LEVEL_NAME = {0: "未接触", 1: "见过", 2: "能复述", 3: "能应用", 4: "能教·迁移"}
STALE_DAYS, RUST_DAYS = 30, 60


# ---------- 文件级评级 ----------
# 关键原则：看课/视频笔记是"输入"，最高 2 级；3 级必须有自己的项目/代码/复现等"输出型实践"。
def file_level(e):
    if e["category"] == "daily" or e["category"] == "job":
        return None  # 日志/简历不计知识点等级
    # 导航/索引文件：体系化梳理，最高 2，代码围栏不算动手
    if e.get("is_nav"):
        return 2 if (e["chars"] >= 120 or e["h2_count"] >= 2) else 1
    # 4：自己命名输出的费曼讲解（非课程），结构化且够长
    if e["feynman"] and not e["is_course"] and e["chars"] >= 500 and e["h2_count"] >= 2:
        return 4
    # 3：真实项目实践——项目库且（有真实代码量 或 标记完成）
    if e["category"] == "project":
        if e["code_lines"] >= 10 or "完成" in e.get("status", ""):
            return 3
        return 2  # 纯文字项目/实习总结，没有代码，只算复述
    # 3：非课程、非导航，标题明确是自己的复现/实战（研读/注释别人代码不算独立应用）
    if not e["is_course"] and not e.get("is_nav") and any(
            x in e["title"] for x in ("复现", "实战", "亲手", "实现记录", "项目实战")):
        return 3
    # 课程/视频/普通笔记：输入型，最高 2（能复述）
    if e["chars"] >= 400 or e["h2_count"] >= 3:
        return 2
    if e["chars"] >= 120:
        return 2
    return 1


# ---------- 领域级聚合 ----------
def domain_level(total, practice, feynman):
    if total == 0:
        return 0
    if feynman >= 1 and practice >= 2 and total >= 8:
        return 4  # 有输出、有实践且覆盖面够，才到"能教迁移"
    if practice >= 1:
        return 3  # 有真实动手项目=能应用（笔记少也认，但在明细体现覆盖窄）
    if total >= 3:
        return 2  # 系统笔记/课程积累=能复述
    return 1


def parse_hotspots(error_md):
    """从 03 错题卡点日志解析 🔺高频坑点，返回 [(知识点/标题, 次数, 领域)]。"""
    error_md = re.sub(r"<!--[\s\S]*?-->", "", error_md or "")
    spots = []
    for line in error_md.splitlines():
        s = line.strip()
        if "🔺" in s and not s.startswith("##"):
            spots.append(s.lstrip("- ").replace("🔺", "").strip())
    return spots


def stale_flag(last_iso, now):
    if not last_iso:
        return ""
    dt = datetime.datetime.fromisoformat(last_iso)
    days = (now - dt).days
    if days >= RUST_DAYS:
        return f"🔕{days}天未碰"
    if days >= STALE_DAYS:
        return f"⚠️{days}天未碰"
    return ""


def build(roots, now):
    ev = scan(roots)
    for e in ev:
        e["level"] = file_level(e)

    domains = {}
    for e in ev:
        d = e["domain"]
        dom = domains.setdefault(d, {"files": [], "total": 0, "practice": 0, "feynman": 0,
                                     "projects": 0, "chars": 0, "last": "", "dist": {0:0,1:0,2:0,3:0,4:0}})
        if e["level"] is None:
            continue
        dom["total"] += 1
        dom["chars"] += e["chars"]
        dom["files"].append(e)
        dom["dist"][e["level"]] += 1
        if e["level"] >= 3:
            dom["practice"] += 1
        if e["level"] == 4:
            dom["feynman"] += 1
        if e["category"] == "project":
            dom["projects"] += 1
        if not dom["last"] or e["mtime_iso"] > dom["last"]:
            dom["last"] = e["mtime_iso"]

    summary = {}
    for d, dom in domains.items():
        lvl = domain_level(dom["total"], dom["practice"], dom["feynman"])
        files_sorted = sorted(dom["files"], key=lambda x: (-x["level"], x["mtime_iso"]), reverse=False)
        top = sorted(dom["files"], key=lambda x: (-x["level"], x["mtime_iso"]))[:6]
        summary[d] = {
            "level": lvl, "level_name": LEVEL_NAME[lvl],
            "total": dom["total"], "practice": dom["practice"], "feynman": dom["feynman"],
            "projects": dom["projects"], "chars": dom["chars"],
            "distribution": {str(k): dom["dist"][k] for k in range(5)},
            "last_active": dom["last"][:10], "stale": stale_flag(dom["last"], now),
            "evidence_top": [{"title": t["title"], "level": t["level"], "file": t["file"], "date": t["mtime"][:10]} for t in top],
        }

    # 活跃度（每日日志）
    daily = [e for e in ev if e["category"] == "daily"]
    today_new = [e for e in ev if e["mtime_iso"][:10] == now.strftime("%Y-%m-%d")]
    return ev, summary, daily, today_new


def weak_top3(summary):
    """短板：核心领域优先，按 等级低→实践少→覆盖少→生疏 排序。"""
    rows = []
    for d, s in summary.items():
        if d == "求职":
            continue
        core_bonus = 0 if d in CORE else 10
        rows.append((core_bonus + s["level"], -s["practice"], -s["total"], d, s))
    rows.sort(key=lambda x: (x[0], x[1], x[2]))
    out = []
    for _, _, _, d, s in rows[:3]:
        reason = []
        if s["level"] <= 1:
            reason.append("刚接触、笔记很少")
        if s["practice"] == 0 and s["total"] > 0:
            if "英语" in d or "六级" in d or "语言" in d:
                reason.append("看课输入多，缺真题训练与写作/口语输出")
            elif d in ("数学", "控制工程") or "理论" in d:
                reason.append("停留在看课复述，缺独立做题/推导")
            else:
                reason.append("缺项目/代码等动手实践")
        if s["stale"]:
            reason.append(s["stale"])
        if not reason:
            reason.append("覆盖偏窄，需扩知识点")
        out.append({"domain": d, "level": s["level"], "reason": "；".join(reason)})
    return out


def render_md(summary, weak, hotspots, now, today_n):
    L = ["---", "type: 能力画像",
         f'updated: "{now.strftime("%Y-%m-%d %H:%M")}"',
         'method: 确定性证据驱动 0-4 级（扫描笔记/项目，非 BKT；规则见 references/familiarity-rubric.md）',
         "---", "", "# 01 · 能力画像", "",
         "> 0 未接触 / 1 见过 / 2 能复述 / 3 能应用 / 4 能教能迁移。自动生成，手改会在下次刷新覆盖。", ""]
    L.append("## 总览")
    L.append("| 领域 | 熟悉度 | 等级分布(0-4) | 知识点 | 实践项 | 费曼 | 最近活跃 | 提示 |")
    L.append("|---|---|---|---|---|---|---|---|")
    order = sorted(summary, key=lambda d: (0 if d in CORE else 1, -summary[d]["total"]))
    for d in order:
        s = summary[d]
        dist = "/".join(str(s["distribution"][str(k)]) for k in range(5))
        lvl_txt = "— 不评级" if d == "求职" else f"**{s['level']} {s['level_name']}**"
        L.append(f"| {d} | {lvl_txt} | {dist} | {s['total']} | {s['practice']} | {s['feynman']} | {s['last_active']} | {s['stale']} |")
    L.append("")
    L.append("## 当前最该补的 3 个短板")
    for i, w in enumerate(weak, 1):
        L.append(f"{i}. **{w['domain']}**（当前 {w['level']} 级）— {w['reason']}")
    L.append("")
    L.append("## 🔺 高频坑点清单（同类卡点≥2）")
    L.extend(("- " + h for h in hotspots) if hotspots else ["- 暂无（用【记录卡点】积累，会自动关联到对应领域）"])
    L.append("")
    L.append("## 领域明细与证据")
    for d in order:
        s = summary[d]
        if d == "求职":
            continue
        L.append(f"\n### {d} — {s['level']} {s['level_name']}")
        L.append(f"- 知识点 {s['total']}｜实践项 {s['practice']}｜费曼输出 {s['feynman']}｜累计约 {s['chars']} 字｜最近 {s['last_active']} {s['stale']}")
        for t in s["evidence_top"]:
            L.append(f"  - [{t['level']}] {t['title']}（{t['date']}）")
    L.append(f"\n---\n_本次扫描 {now.strftime('%Y-%m-%d %H:%M')}，今日新增/改动 {today_n} 篇；求职/简历类材料不参与掌握度评级。_")
    return "\n".join(L) + "\n"


def snapshot_and_growth(summary, weak, now, vault):
    snap_dir = os.path.join(vault, "snapshots")
    os.makedirs(snap_dir, exist_ok=True)
    today = now.strftime("%Y-%m-%d")
    snap_path = os.path.join(snap_dir, f"{today}.json")
    cur = {d: {"level": s["level"], "total": s["total"], "practice": s["practice"]} for d, s in summary.items()}
    # 找上一个快照
    olds = sorted(glob.glob(os.path.join(snap_dir, "*.json")))
    olds = [p for p in olds if os.path.basename(p) != f"{today}.json"]
    diffs = []
    if olds:
        try:
            prev = json.load(open(olds[-1], encoding="utf-8"))
            for d, c in cur.items():
                p = prev.get(d)
                if not p:
                    diffs.append(f"新增领域「{d}」起步于 {c['level']} 级")
                    continue
                if c["level"] > p["level"]:
                    diffs.append(f"「{d}」熟悉度 {p['level']}→{c['level']} ↑")
                elif c["level"] < p["level"]:
                    diffs.append(f"「{d}」熟悉度 {p['level']}→{c['level']} ↓")
                if c["total"] - p["total"]:
                    diffs.append(f"「{d}」知识点 {p['total']}→{c['total']}（{c['total']-p['total']:+d}）")
        except Exception as ex:
            diffs.append(f"(旧快照读取失败: {ex})")
    json.dump({"date": today, "domains": cur}, open(snap_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    # 追加成长轨迹（同一天多次全量不重复追加周报，只更新快照）
    growth = os.path.join(vault, "04_成长轨迹.md")
    existing = open(growth, encoding="utf-8").read() if os.path.exists(growth) else ""
    if f"### {today} 周报" in existing:
        return snap_path, ["(今日周报已存在，仅刷新快照，不重复追加)"]
    block = [f"\n### {today} 周报（全量扫描）"]
    block += ("- " + x for x in diffs) if diffs else ["- 与上周相比等级稳定，持续有笔记/项目新增"]
    block.append("- 当前短板：" + "；".join(f"{w['domain']}({w['level']}级)" for w in weak))
    block.append("")
    with open(growth, "a", encoding="utf-8") as f:
        f.write("\n".join(block))
    return snap_path, diffs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=VAULT)
    ap.add_argument("--root", default=SCAN_ROOT)
    ap.add_argument("--extra", nargs="*", default=DEFAULT_EXTRA)
    ap.add_argument("--full", action="store_true", help="全量：额外存快照+写成长轨迹")
    args = ap.parse_args()
    now = datetime.datetime.now()
    roots = [args.root] + [x for x in (args.extra or []) if os.path.isdir(x)]

    ev, summary, daily, today_new = build(roots, now)
    err_path = os.path.join(args.vault, "03_错题卡点日志.md")
    hotspots = parse_hotspots(open(err_path, encoding="utf-8").read() if os.path.exists(err_path) else "")
    weak = weak_top3(summary)

    data = {"generated": now.isoformat(timespec="seconds"), "roots": roots,
            "file_count": len(ev), "domains": summary, "weak_top3": weak, "hotspots": hotspots}
    with open(os.path.join(args.vault, "mastery_data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    md = render_md(summary, weak, hotspots, now, len(today_new))
    with open(os.path.join(args.vault, "01_能力画像.md"), "w", encoding="utf-8") as f:
        f.write(md)

    print(f"✅ 扫描 {len(ev)} 篇，领域 {len(summary)} 个，今日新增/改动 {len(today_new)} 篇")
    for d in sorted(summary, key=lambda x: -summary[x]['total']):
        print(f"   {d}: {summary[d]['level']}级 {summary[d]['level_name']} | 知识点{summary[d]['total']} 实践{summary[d]['practice']}")
    if args.full:
        snap, diffs = snapshot_and_growth(summary, weak, now, args.vault)
        print(f"📸 快照: {snap}")
        for x in diffs:
            print("   变化:", x)


if __name__ == "__main__":
    main()
