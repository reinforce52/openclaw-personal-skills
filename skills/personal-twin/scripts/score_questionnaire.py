#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
personal-twin 量表计分：BFI-10 大五人格 + VARK 学习风格
用法:
  python score_questionnaire.py --bfi "4,3,5,2,4,2,4,3,2,4" --vark "V,A,RK,..."
  # BFI: 10 个 1-5 分，顺序 Q1..Q10
  # VARK: 16 题，每题一个由 V/A/R/K 组成的字符串（单选如 "V"，多选如 "VK"）
输出: JSON（含人读摘要）
"""
import argparse, json, sys

# BFI-10：正向/反向题与维度归属（0-based 索引）
# 反向题: Q1 Q3 Q4 Q5 Q7 -> idx 0,2,3,4,6
REVERSE = {0, 2, 3, 4, 6}
# 维度: (正向idx, 反向idx)
DIMS = {
    "外向性 E": (5, 0),
    "宜人性 A": (1, 6),
    "尽责性 C": (7, 2),
    "神经质 N": (8, 3),
    "开放性 O": (9, 4),
}
DIM_INTERP = {
    "外向性 E": ("偏外向、好讨论、通过说出来学习", "偏内敛、偏好安静独立地学"),
    "宜人性 A": ("在意和谐与肯定，反馈宜先鼓励", "接受直接、重效率，可硬核指出问题"),
    "尽责性 C": ("自律重计划，适合清单与里程碑", "易拖延，需拆小块+外部提醒"),
    "神经质 N": ("易焦虑受挫，遇错先给确定性解法", "情绪稳定，可直接上强度"),
    "开放性 O": ("喜原理类比与多方案发散", "偏好明确步骤与确定主线"),
}


def score_bfi(raw):
    if len(raw) != 10:
        raise ValueError(f"BFI 需要 10 个分，得到 {len(raw)}")
    vals = []
    for i, x in enumerate(raw):
        x = int(x)
        if not 1 <= x <= 5:
            raise ValueError(f"Q{i+1} 分数须在 1-5，得到 {x}")
        vals.append(6 - x if i in REVERSE else x)  # 反向题翻转
    result = {}
    for name, (pos, rev) in DIMS.items():
        s = vals[pos] + vals[rev]  # 2-10
        level = "高" if s >= 7 else ("低" if s <= 4 else "中")
        hi, lo = DIM_INTERP[name]
        result[name] = {"score": s, "level": level,
                        "hint": hi if level == "高" else (lo if level == "低" else "居中，两种方式可灵活切换")}
    return result


def score_vark(answers):
    cnt = {"V": 0, "A": 0, "R": 0, "K": 0}
    for i, a in enumerate(answers):
        a = a.upper().replace(" ", "")
        hit = [c for c in "VARK" if c in a]
        if not hit:
            raise ValueError(f"VARK 第{i+1}题没有有效 V/A/R/K 选项: {a!r}")
        for c in hit:
            cnt[c] += 1
    order = sorted(cnt, key=lambda k: cnt[k], reverse=True)
    top = cnt[order[0]]
    leaders = [k for k in "VARK" if cnt[k] == top]  # 并列主导
    names = {"V": "视觉(图/表/空间)", "A": "听觉(听/说/讨论)",
             "R": "读写(文字/清单/文档)", "K": "动觉(动手/实操)"}
    return {"counts": cnt, "order": order,
            "dominant": leaders,
            "dominant_name": [names[k] for k in leaders],
            "names": names}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bfi", default=None, help="10个1-5分，逗号分隔")
    ap.add_argument("--vark", default=None, help="16题答案，逗号分隔，每题V/A/R/K组合")
    ap.add_argument("--out", default=None, help="可选：把JSON写入文件")
    args = ap.parse_args()

    out = {}
    if args.bfi:
        out["bfi"] = score_bfi([x for x in args.bfi.replace(" ", "").split(",") if x])
    if args.vark:
        out["vark"] = score_vark([x for x in args.vark.split(",") if x.strip()])
    if not out:
        ap.error("至少提供 --bfi 或 --vark")

    # 人读摘要
    print("=" * 50)
    if "bfi" in out:
        print("【大五人格 BFI-10】(2-10分)")
        for k, v in out["bfi"].items():
            print(f"  {k}: {v['score']} ({v['level']}) — {v['hint']}")
    if "vark" in out:
        v = out["vark"]
        print("【VARK 学习风格】计数:", v["counts"])
        print("  主导:", " + ".join(v["dominant_name"]), "| 排序:", " > ".join(v["order"]))
    print("=" * 50)

    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print("已写入:", args.out)
    print(text)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("❌ 计分失败:", e, file=sys.stderr)
        sys.exit(1)
