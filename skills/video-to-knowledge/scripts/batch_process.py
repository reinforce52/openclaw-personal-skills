#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量视频处理脚本 - 支持断点续传
逐个处理B站分P视频：下载→转写→总结→写入Obsidian→自动清理
"""

import os
import sys
import json
import time
import argparse
import subprocess
from datetime import datetime

# 配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE_SCRIPT = os.path.join(SCRIPT_DIR, "pipeline.py")
WRITE_OBSIDIAN_SCRIPT = os.path.join(SCRIPT_DIR, "write_obsidian.py")
PROGRESS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "progress")


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def load_progress(progress_file):
    """加载进度（已处理的视频ID集合）"""
    if os.path.exists(progress_file):
        # 用 utf-8-sig 兼容 BOM
        for enc in ["utf-8-sig", "utf-8", "gbk"]:
            try:
                with open(progress_file, "r", encoding=enc) as f:
                    return json.load(f)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
    return {"processed": [], "failed": [], "current": None}


def save_progress(progress_file, progress):
    """保存进度"""
    ensure_dir(os.path.dirname(progress_file))
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


# ============ 运行锁：防止同一合集被多个批量实例同时处理（实战曾因此产生重复笔记）============
def pid_alive(pid: int) -> bool:
    """检测某 PID 进程是否仍在运行（跨平台）"""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def acquire_lock(bvid: str):
    """获取该合集的运行锁；若已有存活实例则返回其信息，否则创建锁并返回 None"""
    ensure_dir(PROGRESS_DIR)
    lock_file = os.path.join(PROGRESS_DIR, f".batch_{bvid}.lock")
    if os.path.exists(lock_file):
        try:
            with open(lock_file, "r", encoding="utf-8") as f:
                info = json.load(f)
            if pid_alive(int(info.get("pid", -1))):
                return info  # 已有实例在跑
        except Exception:
            pass  # 锁文件损坏，视为过期
        # 旧锁对应进程已死，清理过期锁
        try:
            os.remove(lock_file)
        except OSError:
            pass
    with open(lock_file, "w", encoding="utf-8") as f:
        json.dump({"pid": os.getpid(), "bvid": bvid,
                   "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f,
                  ensure_ascii=False, indent=2)
    return None


def release_lock(bvid: str):
    """释放运行锁（仅当锁属于当前进程时删除）"""
    lock_file = os.path.join(PROGRESS_DIR, f".batch_{bvid}.lock")
    try:
        if os.path.exists(lock_file):
            with open(lock_file, "r", encoding="utf-8") as f:
                info = json.load(f)
            if int(info.get("pid", -1)) == os.getpid():
                os.remove(lock_file)
    except Exception:
        try:
            os.remove(lock_file)
        except OSError:
            pass


def run_pipeline(url, model="medium", use_cpu=False):
    """运行 pipeline.py，返回结果"""
    cmd = [sys.executable, PIPELINE_SCRIPT, url, "--model", model, "--json"]
    if use_cpu:
        cmd.append("--cpu")
    print(f"\n{'='*60}")
    print(f"▶ 处理: {url}")
    print(f"  命令: python pipeline.py {url} --model {model} --json{' --cpu' if use_cpu else '（GPU加速）'}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=3600,  # 60分钟超时（超长视频分段转写需要更多时间）
            env={**os.environ, "HTTP_PROXY": "", "HTTPS_PROXY": "", "http_proxy": "", "https_proxy": ""}
        )
        # 从输出中提取最后一个JSON
        output = result.stdout + result.stderr
        # 找最后一个 { 开始的JSON
        json_start = output.rfind("\n{")
        if json_start == -1:
            json_start = output.rfind("{")
        if json_start >= 0:
            try:
                json_str = output[json_start:]
                # 找到JSON结束位置
                brace_count = 0
                end_pos = 0
                for i, ch in enumerate(json_str):
                    if ch == '{':
                        brace_count += 1
                    elif ch == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i + 1
                            break
                return json.loads(json_str[:end_pos])
            except (json.JSONDecodeError, ValueError):
                pass
        return {"error": f"无法解析输出，returncode={result.returncode}\nstdout末尾: {result.stdout[-500:]}\nstderr: {result.stderr[-500:]}"}
    except subprocess.TimeoutExpired:
        return {"error": "处理超时（30分钟）"}
    except Exception as e:
        return {"error": f"运行失败: {e}"}


def write_to_obsidian(summary_file, topic):
    """写入 Obsidian"""
    if not summary_file or not os.path.exists(summary_file):
        print(f"  ⚠️ summary文件不存在，跳过写入: {summary_file}")
        return False

    cmd = [sys.executable, WRITE_OBSIDIAN_SCRIPT, summary_file, "--topic", topic]
    print(f"  📝 写入Obsidian: 主题={topic}")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=120,
            env={**os.environ, "HTTP_PROXY": "", "HTTPS_PROXY": "", "http_proxy": "", "https_proxy": ""}
        )
        if result.returncode == 0:
            print(f"  ✅ 写入成功")
            return True
        else:
            print(f"  ❌ 写入失败: {result.stderr[-300:]}")
            return False
    except Exception as e:
        print(f"  ❌ 写入异常: {e}")
        return False


def select_model_by_duration(duration_str, default_model="medium"):
    """
    混合模式：根据视频时长自动选择转写模型
    - 短视频（<20分钟）：medium（质量优先）
    - 长视频（>=20分钟）：small（速度优先）
    duration_str: 时长字符串，如 "1761.91" 或 "1:23:45"
    """
    try:
        # 尝试解析为秒数
        if ":" in str(duration_str):
            # 格式 HH:MM:SS 或 MM:SS
            parts = str(duration_str).split(":")
            if len(parts) == 3:
                seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                seconds = int(parts[0]) * 60 + int(parts[1])
            else:
                seconds = 0
        else:
            seconds = float(duration_str)

        if seconds >= 1200:  # 20分钟 = 1200秒
            return "small"
        else:
            return "medium"
    except (ValueError, TypeError):
        return default_model


def process_batch(bvid, pages, topic, model="medium", progress_file=None, hybrid=True, use_cpu=False):
    """批量处理一个合集的所有分P
    hybrid: True=混合模式（根据时长自动选模型），False=统一用model参数
    """
    if progress_file is None:
        progress_file = os.path.join(PROGRESS_DIR, f"{topic}_{bvid}.json")

    progress = load_progress(progress_file)
    processed_ids = set(progress.get("processed", []))
    failed_ids = set(progress.get("failed", []))

    total = len(pages)
    success_count = len([p for p in processed_ids if p in [str(p["page"]) for p in pages]])
    print(f"\n{'#'*70}")
    print(f"# 批量处理: {topic}")
    print(f"# BV号: {bvid}")
    print(f"# 总视频数: {total}")
    print(f"# 已完成: {success_count}")
    print(f"# 失败: {len(failed_ids)}")
    print(f"# 待处理: {total - success_count - len(failed_ids)}")
    if hybrid:
        print(f"# 模式: 混合（短视频medium / 长视频small，阈值20分钟）")
    else:
        print(f"# 模型: {model}")
    print(f"{'#'*70}")

    for i, page in enumerate(pages, 1):
        page_num = str(page["page"])
        page_title = page.get("part", f"P{page_num}")
        duration = page.get("duration", "0")
        video_url = f"https://www.bilibili.com/video/{bvid}?p={page['page']}"

        # 跳过已处理
        if page_num in processed_ids:
            print(f"\n[{i}/{total}] ⏭️ 跳过已处理: P{page_num} {page_title}")
            continue

        # 跳过之前失败的（可以用 --retry-failed 重试）
        if page_num in failed_ids and "--retry-failed" not in sys.argv:
            print(f"\n[{i}/{total}] ⏭️ 跳过之前失败: P{page_num} {page_title}")
            continue

        # 混合模式：根据时长选择模型
        current_model = model
        if hybrid:
            current_model = select_model_by_duration(duration, model)
            model_note = f" [混合模式: {current_model}]"
        else:
            model_note = ""

        print(f"\n[{i}/{total}] ▶ 处理: P{page_num} {page_title} (时长: {duration}){model_note}")
        start_time = time.time()

        # 运行 pipeline
        result = run_pipeline(video_url, current_model, use_cpu=use_cpu)

        elapsed = time.time() - start_time
        print(f"  ⏱️ 耗时: {int(elapsed//60)}分{int(elapsed%60)}秒")

        if "error" in result:
            print(f"  ❌ 处理失败: {result['error'][:200]}")
            progress["failed"].append(page_num)
            progress["failed"] = list(set(progress["failed"]))
            save_progress(progress_file, progress)
            continue

        # 写入 Obsidian
        summary_file = result.get("summary_file", "")
        if summary_file:
            write_to_obsidian(summary_file, topic)
        else:
            print(f"  ⚠️ 无summary文件，跳过写入")

        # 记录成功
        progress["processed"].append(page_num)
        progress["processed"] = list(set(progress["processed"]))
        if page_num in failed_ids:
            progress["failed"].remove(page_num)
        save_progress(progress_file, progress)

        success_count += 1
        print(f"  ✅ 完成！进度: {success_count}/{total} ({success_count*100//total}%)")

    print(f"\n{'='*70}")
    print(f"✅ 批量处理完成: {topic}")
    print(f"   成功: {len([p for p in progress['processed'] if p in [str(p['page']) for p in pages]])}/{total}")
    print(f"   失败: {len(progress['failed'])}")
    print(f"   进度文件: {progress_file}")
    print(f"{'='*70}")

    return progress


def main():
    parser = argparse.ArgumentParser(description="批量视频处理（支持断点续传）")
    parser.add_argument("--bvid", required=True, help="B站BV号")
    parser.add_argument("--topic", required=True, help="Obsidian主题名称")
    parser.add_argument("--model", default="medium", help="转写模型 (tiny/base/small/medium)")
    parser.add_argument("--pages", default=None, help="指定分P范围，如 '1-10' 或 '1,3,5'")
    parser.add_argument("--retry-failed", action="store_true", help="重试之前失败的视频")
    parser.add_argument("--no-hybrid", action="store_true", help="关闭混合模式（统一用--model指定的模型）")
    parser.add_argument("--cpu", action="store_true", help="强制CPU转写（默认GPU加速）")
    parser.add_argument("--force", action="store_true", help="忽略运行锁强制启动（确认无其他实例时用）")
    args = parser.parse_args()

    # 运行锁：防止同一合集多实例重叠（曾因此产生重复笔记）
    if not args.force:
        existing = acquire_lock(args.bvid)
        if existing:
            print(f"❌ 检测到合集 {args.bvid} 已有批量实例在运行：")
            print(f"   PID={existing.get('pid')}, 启动于 {existing.get('started')}")
            print(f"   如确认是残留（进程已死仍报错），可加 --force 强制启动，或删除 progress/.batch_{args.bvid}.lock")
            sys.exit(2)
    try:
        _run_batch(args)
    finally:
        release_lock(args.bvid)


def _run_batch(args):
    # 获取分P列表
    print(f"获取分P列表: {args.bvid}")
    import requests
    api_url = f"https://api.bilibili.com/x/player/pagelist?bvid={args.bvid}&jsonp=jsonp"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://www.bilibili.com/video/{args.bvid}",
    }
    try:
        resp = requests.get(api_url, headers=headers, timeout=15, proxies={"http": None, "https": None})
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"❌ 获取分P列表失败: {e}")
        print(f"   响应内容: {resp.text[:500] if 'resp' in dir() else '无'}")
        sys.exit(1)

    if data.get("code") != 0:
        print(f"❌ 获取分P列表失败: {data.get('message', '未知错误')}")
        sys.exit(1)

    pages = data["data"]
    print(f"共 {len(pages)} 个分P")

    # 筛选分P范围
    if args.pages:
        selected = set()
        for part in args.pages.split(","):
            if "-" in part:
                start, end = map(int, part.split("-"))
                selected.update(range(start, end + 1))
            else:
                selected.add(int(part))
        pages = [p for p in pages if p["page"] in selected]
        print(f"筛选后: {len(pages)} 个分P")

    # 处理（默认开启混合模式）
    process_batch(args.bvid, pages, args.topic, args.model, hybrid=not args.no_hybrid, use_cpu=args.cpu)


if __name__ == "__main__":
    main()
