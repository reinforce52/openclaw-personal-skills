#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deep_batch.py - v2 深度版批量处理（下载转写 → web深度搜索 → 两层笔记写入，全自动串联）
对B站合集每个分P依次执行：
  pipeline.py（下载+转写+v2细粒度总结）
  → knowledge_deep_dive.py（必应/web深度搜索扩展）
  → write_obsidian.py（两层笔记：视频总览+知识点9段式笔记+复习清单）
支持断点续传、失败重试、运行锁（与 batch_process.py 一致）。
全部完成后可用 build_knowledge_graph.py 单独生成总谱系。

用法:
  python deep_batch.py --bvid BV1ys411472E --topic "线性代数" --model small
  # 指定分P: --pages "2-16"
  # 重试失败: --retry-failed
  # 强制CPU: --cpu ; 忽略运行锁: --force
  # 省token(只对高重要性知识点搜索): --eco
"""
import os, sys, json, time, argparse, subprocess
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE = os.path.join(SCRIPT_DIR, "pipeline.py")
DEEP = os.path.join(SCRIPT_DIR, "knowledge_deep_dive.py")
WRITE = os.path.join(SCRIPT_DIR, "write_obsidian.py")
PROGRESS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "progress")

# 清空代理的子进程环境（B站/必应/中南API都走直连）
CHILD_ENV = {**os.environ, "HTTP_PROXY": "", "HTTPS_PROXY": "", "http_proxy": "", "https_proxy": ""}


def ensure_dir(p):
    os.makedirs(p, exist_ok=True)


def run(cmd, timeout=3600):
    """运行子脚本，返回 (returncode, stdout+stderr)"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, env=CHILD_ENV)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    except Exception as e:
        return -2, str(e)


def extract_last_json(text):
    """从输出中提取最后一个 JSON 对象"""
    i = text.rfind("\n{")
    if i == -1:
        i = text.rfind("{")
    if i < 0:
        return None
    depth, end = 0, 0
    for j, ch in enumerate(text[i:]):
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + j + 1
                break
    try:
        return json.loads(text[i:end])
    except Exception:
        return None


def get_pages(bvid):
    """通过B站API获取分P列表"""
    import requests
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
               "Referer": f"https://www.bilibili.com/video/{bvid}"}
    r = requests.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
                     headers=headers, timeout=20, proxies={"http": None, "https": None})
    d = r.json()
    if d.get("code") != 0:
        raise RuntimeError(f"B站API错误: {d.get('message')}")
    return [{"page": p["page"], "part": p["part"], "duration": p.get("duration", 0)}
            for p in d["data"]["pages"]]


def parse_pages(spec, total):
    """解析 '1-10' / '1,3,5' → 分P号集合（1-based）"""
    if not spec:
        return list(range(1, total + 1))
    result = []
    for tok in spec.split(","):
        tok = tok.strip()
        if "-" in tok:
            a, b = tok.split("-", 1)
            result.extend(range(int(a), int(b) + 1))
        elif tok:
            result.append(int(tok))
    return sorted(set(result))


# ============ 运行锁 ============
def pid_alive(pid):
    try:
        os.kill(pid, 0); return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def acquire_lock(bvid, force=False):
    ensure_dir(PROGRESS_DIR)
    lf = os.path.join(PROGRESS_DIR, f".deepbatch_{bvid}.lock")
    if os.path.exists(lf) and not force:
        try:
            info = json.load(open(lf, encoding="utf-8"))
            if pid_alive(int(info.get("pid", -1))):
                return info
        except Exception:
            pass
    json.dump({"pid": os.getpid(), "bvid": bvid,
               "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
              open(lf, "w", encoding="utf-8"), ensure_ascii=False)
    return None


def release_lock(bvid):
    lf = os.path.join(PROGRESS_DIR, f".deepbatch_{bvid}.lock")
    try:
        if os.path.exists(lf):
            info = json.load(open(lf, encoding="utf-8"))
            if int(info.get("pid", -1)) == os.getpid():
                os.remove(lf)
    except Exception:
        try: os.remove(lf)
        except OSError: pass


def load_progress(pf):
    if os.path.exists(pf):
        for enc in ["utf-8-sig", "utf-8"]:
            try:
                return json.load(open(pf, encoding=enc))
            except Exception:
                continue
    return {"processed": [], "failed": []}


def main():
    ap = argparse.ArgumentParser(description="v2深度版批量处理")
    ap.add_argument("--bvid", required=True)
    ap.add_argument("--topic", required=True)
    ap.add_argument("--model", default="small")
    ap.add_argument("--pages", default=None, help="'2-16' 或 '1,3,5'")
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--cpu", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--eco", action="store_true", help="省token：只对高重要性知识点做web搜索")
    args = ap.parse_args()

    lock = acquire_lock(args.bvid, args.force)
    if lock:
        print(f"❌ 已有深度批量实例在运行 PID={lock.get('pid')}，确认无残留可加 --force")
        sys.exit(2)

    try:
        ensure_dir(PROGRESS_DIR)
        pf = os.path.join(PROGRESS_DIR, f"deep_{args.topic}_{args.bvid}.json")
        prog = load_progress(pf)
        processed, failed = set(prog.get("processed", [])), set(prog.get("failed", []))

        pages = get_pages(args.bvid)
        want = set(parse_pages(args.pages, len(pages)))
        todo = [p for p in pages if p["page"] in want]

        print("#" * 70)
        print(f"# 深度批量: {args.topic} | {args.bvid} | 模型 {args.model}{' (省token)' if args.eco else ''}")
        print(f"# 选中 {len(todo)} 集 | 已完成 {len(processed & want)} | 失败 {len(failed & want)}")
        print("#" * 70)

        for idx, pg in enumerate(todo, 1):
            pn = str(pg["page"])
            url = f"https://www.bilibili.com/video/{args.bvid}?p={pg['page']}"
            if pn in processed:
                print(f"\n[{idx}/{len(todo)}] ⏭️ 跳过已完成 P{pn} {pg['part']}")
                continue
            if pn in failed and not args.retry_failed:
                print(f"\n[{idx}/{len(todo)}] ⏭️ 跳过失败 P{pn}（--retry-failed 重试）")
                continue

            t0 = time.time()
            print(f"\n[{idx}/{len(todo)}] ▶ P{pn} {pg['part']} ({pg['duration']//60}分)")

            # 1) pipeline：下载+转写+总结
            cmd = [sys.executable, PIPELINE, url, "--model", args.model, "--json"]
            if args.cpu: cmd.append("--cpu")
            rc, out = run(cmd)
            res = extract_last_json(out)
            if rc != 0 or not res or res.get("error"):
                print(f"  ❌ pipeline失败: {(res or {}).get('error', out[-200:])}")
                failed.add(pn); prog["failed"] = sorted(failed)
                json.dump(prog, open(pf, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
                continue
            summary_file = res.get("summary_file")
            print(f"  ✅ 转写总结完成，知识点 {res.get('knowledge_points_count', '?')} 个")

            # 2) knowledge_deep_dive：web深度搜索
            deep_file = os.path.join(os.path.dirname(summary_file), "deep_dive.json")
            cmd = [sys.executable, DEEP, summary_file, "--output", deep_file]
            if args.eco: cmd.extend(["--max-points", "99"])  # eco逻辑在LLM侧，此处保留接口
            rc, out = run(cmd, timeout=1800)
            if rc != 0 or not os.path.exists(deep_file):
                print(f"  ⚠️ 深度搜索失败，降级用 summary.json 基础写入: {out[-150:]}")
                write_input = summary_file  # 降级
            else:
                print(f"  ✅ web深度搜索完成")
                write_input = deep_file

            # 3) write_obsidian：两层笔记写入
            rc, out = run([sys.executable, WRITE, write_input, "--topic", args.topic], timeout=300)
            if rc != 0:
                print(f"  ❌ 写入失败: {out[-200:]}")
                failed.add(pn); prog["failed"] = sorted(failed)
                json.dump(prog, open(pf, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
                continue

            processed.add(pn); failed.discard(pn)
            prog["processed"], prog["failed"] = sorted(processed), sorted(failed)
            json.dump(prog, open(pf, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"  ✅ 写入完成，用时 {int(time.time()-t0)}秒，累计 {len(processed & want)}/{len(todo)}")

        print("\n" + "=" * 70)
        print(f"✅ 深度批量结束: 成功 {len(processed & want)}/{len(todo)}，失败 {len(failed & want)}")
        if failed & want:
            print(f"   失败分P: {sorted(failed & want)}，可加 --retry-failed 重试")
        print("=" * 70)
    finally:
        release_lock(args.bvid)


if __name__ == "__main__":
    main()
