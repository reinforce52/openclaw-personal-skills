#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_refresh.py — personal-twin 一键刷新入口（供定时任务调用）。
顺序：update_mastery（扫描→0-4评级→能力画像/快照）→ build_injection（注入摘要）
    → adaptive_service（P2 服务参数 + 05 落盘）。

用法:
  python run_refresh.py            # 每日：重算画像 + 刷新注入摘要 + 服务参数
  python run_refresh.py --full     # 每周：额外存快照、追加成长轨迹
"""
import os, sys, subprocess, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
VAULT = r"E:\obsidian\rein\_个人镜像"


def run(script, *args):
    p = subprocess.run([PY, os.path.join(HERE, script), *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(p.stdout or "", end="")
    if p.returncode != 0:
        print(f"[run_refresh] ❌ {script} 失败:\n{p.stderr}", file=sys.stderr)
    return p.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="周度全量：快照+成长轨迹")
    args = ap.parse_args()

    print("=== [1/3] 扫描四库并更新能力画像 ===")
    rc1 = run("update_mastery.py", *(["--full"] if args.full else []))
    print("\n=== [2/3] 重生成对话注入摘要 ===")
    rc2 = run("build_injection.py")
    print("\n=== [3/3] 生成 P2 自适应服务参数 ===")
    rc3 = run("adaptive_service.py", "--out", os.path.join(VAULT, "05_自适应服务参数.md"))

    if rc1 == 0 and rc2 == 0 and rc3 == 0:
        print("\n✅ personal-twin 刷新完成：01_能力画像 / mastery_data.json / _注入摘要 / 05_服务参数 已更新")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
