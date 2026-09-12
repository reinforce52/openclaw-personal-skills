#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主流程串联脚本 - 视频 → 知识库
一键完成: 下载 → (字幕优先/无字幕转写) → LLM总结 → 输出主题建议
后续由 OpenClaw 确认主题后调用 write_obsidian.py 写入
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path

# 脚本目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_SCRIPT = os.path.join(SCRIPT_DIR, "download.py")
TRANSCRIBE_SCRIPT = os.path.join(SCRIPT_DIR, "transcribe.py")
SUMMARIZE_SCRIPT = os.path.join(SCRIPT_DIR, "summarize.py")

# 临时工作目录
TEMP_BASE = r"E:\openclaw-video-temp"

# 需要自动删除的文件扩展名（大文件）
CLEANUP_VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".flv", ".mov", ".wmv", ".webm", ".m4v", ".ts"}
CLEANUP_AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma"}
CLEANUP_DIRS = {"segments"}  # 转写片段目录


def cleanup_temp_files(output_dir: str, dry_run: bool = False) -> dict:
    """
    自动清理临时大文件，保留元数据、字幕、总结结果
    返回清理统计：{deleted_files, freed_bytes, kept_files}
    """
    if not output_dir or not os.path.exists(output_dir):
        return {"deleted_files": 0, "freed_bytes": 0, "kept_files": 0}

    deleted = 0
    freed = 0
    kept = 0

    for root, dirs, files in os.walk(output_dir, topdown=True):
        # 跳过需要删除的目录（先删目录里的文件）
        for d in list(dirs):
            if d.lower() in CLEANUP_DIRS:
                dir_path = os.path.join(root, d)
                # 统计目录大小
                for r, _, fs in os.walk(dir_path):
                    for f in fs:
                        fp = os.path.join(r, f)
                        try:
                            freed += os.path.getsize(fp)
                            deleted += 1
                        except OSError:
                            pass
                if not dry_run:
                    import shutil
                    shutil.rmtree(dir_path, ignore_errors=True)
                dirs.remove(d)  # 不再递归进入

        for f in files:
            fpath = os.path.join(root, f)
            ext = os.path.splitext(f)[1].lower()
            try:
                size = os.path.getsize(fpath)
            except OSError:
                size = 0

            if ext in CLEANUP_VIDEO_EXTS or ext in CLEANUP_AUDIO_EXTS:
                deleted += 1
                freed += size
                if not dry_run:
                    try:
                        os.remove(fpath)
                    except OSError:
                        pass
            else:
                kept += 1

    return {
        "deleted_files": deleted,
        "freed_bytes": freed,
        "freed_mb": round(freed / (1024 * 1024), 2),
        "kept_files": kept,
    }


def run_python(script: str, args: list, timeout: int = 600) -> tuple:
    """运行 Python 脚本，返回 (returncode, stdout, stderr)"""
    cmd = [sys.executable, script] + args
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return result.returncode, result.stdout, result.stderr


def extract_last_json(text: str):
    """从字符串中提取最后一个完整的 JSON 对象（处理嵌套和日志干扰）"""
    decoder = json.JSONDecoder()
    pos = len(text)
    while pos > 0:
        pos = text.rfind("{", 0, pos)
        if pos == -1:
            return None
        try:
            obj, end = decoder.raw_decode(text[pos:])
            return obj
        except json.JSONDecodeError:
            pos -= 1
            continue
    return None


def process_video(url: str, model_size: str = "small", force_transcribe: bool = False, cleanup: bool = True, use_cpu: bool = False) -> dict:
    """
    主流程：下载 → 转写(如需要) → 总结 → (可选)自动清理临时大文件
    返回包含 summary 和主题建议的 dict
    use_cpu=False时默认GPU加速（RTX 4060），GPU不可用transcribe.py会自动回退CPU
    """
    print("=" * 60)
    print(f"🎬 开始处理: {url}")
    print("=" * 60)

    # ===== 步骤1: 下载 =====
    print("\n[步骤 1/3] 下载视频/抓取字幕...")
    rc, stdout, stderr = run_python(DOWNLOAD_SCRIPT, [url, "--json"])
    if rc != 0:
        return {"error": f"下载失败: {stderr[-500:]}\nstdout: {stdout[-500:]}"}

    # 解析下载结果
    download_result = extract_last_json(stdout)
    if download_result is None:
        return {"error": f"解析下载结果失败\nstdout: {stdout[-1000:]}"}

    if "error" in download_result:
        return download_result

    metadata_path = download_result.get("metadata_file", "")
    output_dir = download_result.get("output_dir", "")
    has_subtitle = download_result.get("has_subtitle", False)
    subtitle_file = download_result.get("subtitle_file", "")
    audio_file = download_result.get("audio_file", "")

    print(f"  ✅ 下载完成")
    print(f"  标题: {download_result.get('title', '?')}")
    print(f"  平台: {download_result.get('platform', '?')}")
    print(f"  有字幕: {has_subtitle}")
    if has_subtitle:
        print(f"  字幕文件: {subtitle_file}")
    else:
        print(f"  音频文件: {audio_file}")

    # ===== 步骤2: 转写（如需要）=====
    transcript_file = subtitle_file
    if not has_subtitle or force_transcribe:
        if not audio_file or not os.path.exists(audio_file):
            return {"error": "无字幕且无音频文件，无法转写"}
        print(f"\n[步骤 2/3] 语音转写（模型: {model_size}, {'CPU' if use_cpu else 'GPU'}）...")
        transcribe_args = [audio_file, "--model", model_size, "--json"]
        if use_cpu:
            transcribe_args.append("--cpu")
        rc, stdout, stderr = run_python(
            TRANSCRIBE_SCRIPT,
            transcribe_args,
            timeout=3600,  # GPU很快，CPU长视频分段需要较长时间
        )
        if rc != 0:
            return {"error": f"转写失败: {stderr[-500:]}\nstdout: {stdout[-500:]}"}
        try:
            transcribe_result = extract_last_json(stdout)
            transcript_file = transcribe_result.get("txt_file", transcribe_result.get("srt_file", ""))
            print(f"  ✅ 转写完成: {transcribe_result.get('segments_count', 0)} 段")
        except (json.JSONDecodeError, ValueError, AttributeError):
            # 即使解析失败，也尝试在 output_dir 找转写文件
            for f in os.listdir(output_dir):
                if f.endswith(".srt") or f.endswith(".txt"):
                    transcript_file = os.path.join(output_dir, f)
                    break
            print(f"  ⚠️ 转写结果解析异常，使用找到的文件: {transcript_file}")
    else:
        print(f"\n[步骤 2/3] 已有字幕，跳过转写")

    # ===== 步骤3: LLM 总结 =====
    print(f"\n[步骤 3/3] LLM 总结分析...")
    rc, stdout, stderr = run_python(SUMMARIZE_SCRIPT, [metadata_path, "--transcript", transcript_file, "--json"])
    if rc != 0:
        return {"error": f"总结失败: {stderr[-500:]}\nstdout: {stdout[-500:]}"}

    # 优先直接读取 summary.json 文件（比解析stdout更可靠）
    summary_file_path = os.path.join(output_dir, "summary.json")
    summary_result = None
    if os.path.exists(summary_file_path):
        try:
            # 自动检测编码读取
            for enc in ["utf-8", "gbk", "gb2312"]:
                try:
                    with open(summary_file_path, "r", encoding=enc) as f:
                        summary_result = json.load(f)
                    break
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
        except Exception as e:
            print(f"  ⚠️ 读取summary.json失败: {e}，尝试解析stdout")

    # 如果读取文件失败，回退到解析stdout
    if summary_result is None:
        try:
            summary_result = extract_last_json(stdout)
            if summary_result is None:
                return {"error": f"解析总结结果失败\nstdout: {stdout[-1000:]}"}
        except Exception as e:
            return {"error": f"解析总结结果失败: {e}\nstdout: {stdout[-1000:]}"}

    if "error" in summary_result:
        return summary_result

    # 确保 summary_file 字段正确
    if not summary_result.get("summary_file"):
        summary_result["summary_file"] = summary_file_path if os.path.exists(summary_file_path) else ""

    # ===== 完成 =====
    topic = summary_result.get("topic_suggestion", "未分类")
    print("\n" + "=" * 60)
    print("✅ 处理完成！")
    print("=" * 60)
    print(f"  建议主题: {topic}")
    print(f"  一句话总结: {summary_result.get('one_sentence_summary', '')[:80]}...")
    # 兼容 v2(knowledge_points) 和 v1(core_knowledge_points)
    _kp = summary_result.get('knowledge_points', summary_result.get('core_knowledge_points', []))
    print(f"  细粒度知识点: {len(_kp)} 个")
    print(f"  summary 文件: {summary_result.get('summary_file', '')}")
    print(f"  工作目录: {output_dir}")

    # ===== 自动清理临时大文件 =====
    cleanup_result = None
    if cleanup:
        print("\n[清理] 自动删除临时视频/音频文件（保留字幕、元数据、总结）...")
        cleanup_result = cleanup_temp_files(output_dir)
        print(f"  ✅ 已删除 {cleanup_result['deleted_files']} 个文件，释放 {cleanup_result['freed_mb']} MB")
        print(f"  📁 保留 {cleanup_result['kept_files']} 个文件（字幕/元数据/总结）")
        print(f"  🔗 视频链接已保存在 metadata.json 中，可随时回看")
    else:
        print("\n[清理] 已跳过（--no-cleanup），临时文件保留在工作目录")

    print("\n👉 下一步: 确认主题后，调用 write_obsidian.py 写入 Obsidian")

    return {
        "success": True,
        "url": url,
        "topic_suggestion": topic,
        "topic_reason": summary_result.get("topic_reason", ""),
        "one_sentence_summary": summary_result.get("one_sentence_summary", ""),
        "knowledge_points_count": len(summary_result.get('knowledge_points', summary_result.get('core_knowledge_points', []))),
        "summary_file": summary_result.get("summary_file", ""),
        "output_dir": output_dir,
        "metadata_file": metadata_path,
        "transcript_file": transcript_file,
        "cleanup": cleanup_result,
    }


def main():
    parser = argparse.ArgumentParser(description="视频知识库主流程 - 下载→转写→总结→自动清理")
    parser.add_argument("url", help="视频 URL (YouTube/B站/抖音)")
    parser.add_argument("--model", "-m", help="转写模型大小 (tiny/base/small/medium)", default="small")
    parser.add_argument("--force-transcribe", action="store_true", help="强制转写（即使有字幕）")
    parser.add_argument("--no-cleanup", action="store_true", help="不自动清理临时文件（调试用）")
    parser.add_argument("--cpu", action="store_true", help="强制CPU转写（默认GPU加速，GPU不可用自动回退CPU）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 结果")
    args = parser.parse_args()

    result = process_video(
        args.url,
        args.model,
        args.force_transcribe,
        cleanup=not args.no_cleanup,
        use_cpu=args.cpu,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif "error" in result:
        print(f"\n❌ 错误: {result['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
