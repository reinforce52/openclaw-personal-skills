#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
adaptive_service.py — P2：把"个人镜像"变成其他 skill / Agent 可调用的服务参数。
读 mastery_data.json + 00_我的档案.md，输出：
  --profile  服务参数（每个领域：讲解深度/例子类型/作业方式/风险提示）→ JSON
  --next     下一步学什么（熟悉度低 + 缺实践 + 时间衰减 + 成绩硬证据）→ JSON/Markdown
  （不带参数）两者都输出 Markdown 摘要

用法示例：
  python adaptive_service.py --profile        # 其他 skill 拿参数
  python adaptive_service.py --next           # 生成下一步建议
  python adaptive_service.py                   # 人类可读摘要
"""
import os, re, json, argparse, sys, datetime

VAULT = r"E:\obsidian\rein\_个人镜像"

# 讲解深度映射：熟悉度 0-1 从零讲，2 讲清概念+带练，3 快速过+上强度，4 直接实战/讨论
DEPTH = {
    0: {"depth": "from_zero", "style": "保姆级分步+类比比喻", "pace": "慢，确认每步懂了再走"},
    1: {"depth": "from_zero", "style": "保姆级分步+类比比喻", "pace": "慢，先建立直觉再给术语"},
    2: {"depth": "concept_plus_practice", "style": "结构化表格+正反方对比+例题带练", "pace": "中，概念核对后立即做题"},
    3: {"depth": "fast_practice", "style": "少铺垫、多实战/项目、给高级用法", "pace": "快，以输出验证理解"},
    4: {"depth": "expert_dialogue", "style": "讨论/迁移/教学输出", "pace": "快，直接上难题与综合题"},
}

# 领域 → 例子类型偏好（与用户学习目标对齐）
EXAMPLE_KIND = {
    "机器视觉": "土木/基建场景案例（裂纹检测、结构监测）",
    "控制工程": "土木机械系统类比（如梁的振动控制、桥墩监测），力学+控制交叉案例",
    "英语六级": "真题句子+刘晓艳长难句例句；听力用真题片段",
    "数学": "考研真题+错题复盘；用图形/表格给公式",
    "AI与深度学习": "神经网络可视化+土木数据集例子",
    "求职": "目标岗位JD+简历匹配",
    "土木专业": "本专业课程与工程实例",
    "编程工程化": "他自己的脚本/工作流例子，直接给可跑代码",
}


def load():
    vault = VAULT
    empty = {"domains": {}, "weak_top3": [], "hotspots": []}
    try:
        data = json.load(open(os.path.join(vault, "mastery_data.json"), encoding="utf-8"))
    except Exception:
        return empty, ""  # 画像未生成：返回空结构，调用方按通用方式执行
    profile = ""
    try:
        profile = open(os.path.join(vault, "00_我的档案.md"), encoding="utf-8").read()
    except Exception:
        pass
    return data, profile


def parse_profile(profile_md):
    """从 00 档案抽出关键行（弱项硬证据、时间资源、硬约束）。"""
    facts = {"weak_evidence": [], "constraints": [], "time": "待补充"}
    weak_keys = ["高数", "线代", "概率", "理论力学", "大学物理", "六级", "排名"]
    for ln in profile_md.splitlines():
        s = ln.strip()
        # 弱项硬证据：含关键词 + 数字（成绩/排名/未过）
        if any(k in s for k in weak_keys) and re.search(r"\d", s):
            if any(x in s for x in ["薄弱", "未过", "排名", "66", "67", "63", "61", "70", "363"]):
                facts["weak_evidence"].append(s.lstrip("- ").strip())
        if "不读博" in s or "不走施工" in s or ("考研" in s and ">" in s and "优先级" in s):
            facts["constraints"].append(s.lstrip("- ").strip())
        if "每天可投入" in s and "待补充" not in s:
            facts["time"] = s
    return facts


def build_profile(data, facts):
    domains = data["domains"]
    adapt = {}
    for d, s in domains.items():
        if d == "求职":
            continue
        lvl = s["level"]
        dep = DEPTH.get(lvl, DEPTH[2]).copy()
        dep["current_level"] = lvl
        dep["level_name"] = s["level_name"]
        dep["example_kind"] = EXAMPLE_KIND.get(d, "贴近他专业/目标的例子")
        dep["topics"] = s["total"]
        dep["practice"] = s["practice"]
        if s.get("stale"):
            dep["stale"] = s["stale"]
        if lvl <= 2:
            dep["focus"] = "先把概念讲透+带练基础题，再谈进阶"
        else:
            dep["focus"] = "跳过基础铺垫，直接做项目/真题并复盘"
        adapt[d] = dep
    return {"generated": datetime.datetime.now().isoformat(timespec="seconds"),
            "weak_top3": data["weak_top3"], "hotspots": data.get("hotspots", []),
            "hard_facts": facts, "adaptation": adapt}


def recommend_next(data, facts, limit=4):
    """下一步推荐：熟悉度低→核心领域优先；缺实践→建议输出型动作；成绩硬证据→点名补课。"""
    weak = {w["domain"]: w for w in data["weak_top3"]}
    core = ["英语六级", "控制工程", "数学", "机器视觉", "AI与深度学习"]
    recs = []
    # 成绩硬证据优先（数学/力学是跨考根基）
    for ev in facts["weak_evidence"]:
        if "高数" in ev or "线代" in ev or "概率" in ev:
            recs.append({"area": "数学", "why": ev,
                         "action": "每周≥2次考研数学基础（当前按2级补）：先做章节例题复现，再独立刷题；目标：从'能复述'到'能应用(3)'",
                         "priority": "P0"})
        if "理论力学" in ev or "大学物理" in ev:
            recs.append({"area": "力学基础", "why": ev,
                         "action": "跨考控制工程前补齐理论力学/大物基础，与自控的拉普拉斯/微分方程衔接",
                         "priority": "P0"})
        if "六级" in ev:
            recs.append({"area": "英语六级", "why": ev,
                         "action": "六级未过→每日单词+真题听力精听+每周1篇写作；从'看课'转向'刷题输出'（当前135篇笔记但0实践）",
                         "priority": "P0"})
    # 画像短板补充
    for d in core:
        s = data["domains"].get(d)
        if not s or d in [r["area"] for r in recs]:
            continue
        if s["level"] <= 1 or (s["level"] == 2 and s["practice"] == 0 and d in ("控制工程", "AI与深度学习")):
            recs.append({"area": d,
                         "why": f"当前 {s['level']} 级（{s['level_name']}），实践 {s['practice']}",
                         "action": {"控制工程": "跟课后立即做课后题（胡寿松章节习题），把'能复述'变成'能解题'",
                                    "AI与深度学习": "挑1个土木数据集跑通最小demo（如裂缝分类），产出项目笔记",
                                    "机器视觉": "把现有 crack-detection 项目扩展（新数据集/新指标），写费曼总结升到4级"}.get(d, "加强练习"),
                         "priority": "P1"})
    # 生疏风险提醒
    for d, s in data["domains"].items():
        if s.get("stale") and "⚠️" in s["stale"]:
            recs.append({"area": d, "why": s["stale"],
                         "action": "先复习旧笔记/项目再学新内容，避免遗忘", "priority": "P2"})
    # 去重保序、限量
    seen, out = set(), []
    for r in recs:
        k = r["area"] + r.get("action", "")
        if k not in seen:
            seen.add(k); out.append(r)
    return out[:limit]


def render_md(profile, recs):
    L = ["# personal-twin 自适应服务参数（P2）", ""]
    L.append("## 各领域讲解方式（其他 skill 接入用）")
    L.append("| 领域 | 深度 | 风格 | 例子 | 节奏 |")
    L.append("|---|---|---|---|---|")
    for d, a in profile["adaptation"].items():
        L.append(f"| {d} | {a['depth']}（{a['level_name']}） | {a['style']} | {a['example_kind']} | {a['pace']} |")
    L.append("")
    L.append("## 下一步推荐（按优先级）")
    for i, r in enumerate(recs, 1):
        L.append(f"{i}. **[{r['priority']}] {r['area']}** — {r['why']}")
        L.append(f"   → {r['action']}")
    L.append("")
    L.append("## 高频坑点")
    L.extend(("- " + h for h in profile["hotspots"]) if profile["hotspots"] else ["- 暂无（用【记录卡点】积累）"])
    L.append("")
    L.append("## 硬约束")
    L.extend("- " + c for c in profile["hard_facts"]["constraints"])
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", action="store_true", help="只输出服务参数 JSON")
    ap.add_argument("--next", action="store_true", help="只输出下一步推荐 JSON")
    ap.add_argument("--out", default=None, help="把 Markdown 摘要写到文件")
    args = ap.parse_args()
    data, profile_md = load()
    facts = parse_profile(profile_md)
    prof = build_profile(data, facts)
    recs = recommend_next(data, facts)

    if args.profile:
        print(json.dumps({"service_profile": prof}, ensure_ascii=False, indent=2)); return
    if args.next:
        print(json.dumps({"next_steps": recs}, ensure_ascii=False, indent=2)); return
    md = render_md(prof, recs)
    print(md)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"已写: {args.out}")


if __name__ == "__main__":
    main()
