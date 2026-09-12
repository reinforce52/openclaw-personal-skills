#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频下载模块 - 统一入口
自动识别 YouTube / B站 / 抖音，字幕优先抓取，无字幕则下载音频
输出: metadata.json + 字幕文件 / 音频文件 到临时工作目录
"""

import os
import sys
import json
import re
import time
import subprocess
import argparse
from pathlib import Path

# ============ 配置 ============
PROXY = "http://127.0.0.1:7897"  # YouTube 代理
COOKIE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "douyin-cookies.txt")
TEMP_BASE = r"E:\openclaw-video-temp"
YTDLP = "yt-dlp"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 网络重试配置（实战：B站音频流偶发抖动/限流，单次失败率约10%，重试可基本消除）
MAX_RETRIES = 3
RETRY_BACKOFF = [2, 5, 10]  # 每次失败后的等待秒数

# 平台识别规则
PLATFORM_PATTERNS = {
    "youtube": [r"youtube\.com", r"youtu\.be", r"youtube-nocookie\.com"],
    "bilibili": [r"bilibili\.com", r"b23\.tv", r"bilibili\.cn"],
    "douyin": [r"douyin\.com", r"iesdouyin\.com", r"douyin\.video"],
}


def detect_platform(url: str) -> str:
    """识别视频平台"""
    for platform, patterns in PLATFORM_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, url, re.IGNORECASE):
                return platform
    return "unknown"


def get_video_id(url: str, platform: str) -> str:
    """提取视频 ID（用于目录命名）"""
    if platform == "youtube":
        m = re.search(r"(?:v=|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})", url)
        if m:
            return m.group(1)
    elif platform == "bilibili":
        m = re.search(r"(BV[a-zA-Z0-9]+)", url)
        if m:
            bvid = m.group(1)
            # 检查是否有分P参数，包含分P信息确保每个分P独立目录
            p_match = re.search(r"[?&]p=(\d+)", url)
            if p_match:
                return f"{bvid}_p{p_match.group(1)}"
            return bvid
    elif platform == "douyin":
        m = re.search(r"/video/(\d+)", url)
        if m:
            return m.group(1)
    # fallback: 用 URL hash
    import hashlib
    return hashlib.md5(url.encode()).hexdigest()[:12]


def _build_env(platform: str) -> dict:
    """构造子进程环境：B站直连必须绕过系统失效代理（实战坑：HTTP_PROXY指向未运行的7892会导致下载失败）"""
    env = dict(os.environ)
    if platform == "bilibili":
        for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "all_proxy", "ALL_PROXY"):
            env[k] = ""
    return env


def run_ytdlp(args: list, url: str, platform: str, retries: int = MAX_RETRIES) -> tuple:
    """运行 yt-dlp，返回 (returncode, stdout, stderr)；对网络抖动自动重试+指数退避"""
    cmd = [YTDLP, "--user-agent", USER_AGENT, "--no-check-certificates",
           "--retries", "3", "--fragment-retries", "3", "--socket-timeout", "30"]
    # 平台特定参数
    if platform == "youtube":
        cmd += ["--proxy", PROXY]
    elif platform == "douyin":
        if os.path.exists(COOKIE_FILE):
            cmd += ["--cookies", COOKIE_FILE]
    # B站直连，不需要额外参数
    cmd += args
    cmd += [url]

    env = _build_env(platform)
    last = (1, "", "")
    for attempt in range(1, retries + 1):
        result = subprocess.run(cmd, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", env=env)
        last = (result.returncode, result.stdout, result.stderr)
        if result.returncode == 0:
            return last
        # 失败：判断是否值得重试（网络/限流类）
        err = (result.stderr or "")[-400:]
        transient = any(k in err.lower() for k in
                        ("timed out", "timeout", "connection", "temporar", "429",
                         "reset", "unreachable", "503", "502", "broken pipe", "incomplete"))
        if attempt < retries and transient:
            wait = RETRY_BACKOFF[min(attempt - 1, len(RETRY_BACKOFF) - 1)]
            print(f"      ⚠️ 下载网络抖动(第{attempt}次)，{wait}秒后重试... {err.strip()[-120:]}")
            time.sleep(wait)
            continue
        break
    return last


def fetch_metadata(url: str, platform: str) -> dict:
    """获取视频元数据（不下载）"""
    args = [
        "--skip-download",
        "--print", "%(title)s",
        "--print", "%(uploader)s",
        "--print", "%(duration)s",
        "--print", "%(id)s",
        "--print", "%(webpage_url)s",
        "--print", "%(thumbnail)s",
        "--print", "%(upload_date)s",
    ]
    rc, stdout, stderr = run_ytdlp(args, url, platform)
    if rc != 0:
        return {"error": f"yt-dlp failed: {stderr[-500:]}"}

    lines = [l.strip() for l in stdout.strip().split("\n") if l.strip()]
    # 预期 8 行：title, uploader, duration, id, webpage_url, thumbnail, upload_date
    metadata = {
        "title": lines[0] if len(lines) > 0 else "未知标题",
        "uploader": lines[1] if len(lines) > 1 else "未知UP主",
        "duration": lines[2] if len(lines) > 2 else "0",
        "video_id": lines[3] if len(lines) > 3 else "unknown",
        "url": lines[4] if len(lines) > 4 else url,
        "thumbnail": lines[5] if len(lines) > 5 else "",
        "upload_date": lines[6] if len(lines) > 6 else "",
        "platform": platform,
    }
    return metadata


def list_subtitles(url: str, platform: str) -> list:
    """列出可用字幕"""
    args = ["--skip-download", "--list-subs"]
    rc, stdout, stderr = run_ytdlp(args, url, platform)
    subs = []
    if rc == 0:
        # 解析字幕列表，找中文相关
        for line in stdout.split("\n"):
            line = line.strip()
            if re.match(r"^(zh|zh-Hans|zh-CN|zh-TW|en|en-US)", line, re.IGNORECASE):
                parts = line.split()
                if parts:
                    lang = parts[0]
                    # 优先中文
                    if re.match(r"zh", lang, re.IGNORECASE):
                        subs.insert(0, lang)
                    else:
                        subs.append(lang)
    return subs


def download_subtitle(url: str, platform: str, output_dir: str, lang: str = "zh-Hans") -> str:
    """下载字幕，返回字幕文件路径"""
    args = [
        "--skip-download",
        "--write-subs",
        "--sub-langs", lang,
        "--sub-format", "srt/vtt",
        "--convert-subs", "srt",
        "-o", os.path.join(output_dir, "%(id)s.%(ext)s"),
    ]
    rc, stdout, stderr = run_ytdlp(args, url, platform)
    # 查找下载的字幕文件
    for f in os.listdir(output_dir):
        if f.endswith(".srt") or f.endswith(".vtt"):
            return os.path.join(output_dir, f)
    return ""


def _find_media(output_dir: str, exts: tuple) -> str:
    """在输出目录查找指定扩展名的媒体文件（取最新的非空文件）"""
    found = [os.path.join(output_dir, f) for f in os.listdir(output_dir)
             if f.lower().endswith(exts)]
    found = [f for f in found if os.path.getsize(f) > 0]
    if not found:
        return ""
    return max(found, key=os.path.getmtime)


def download_audio(url: str, platform: str, output_dir: str) -> str:
    """只下载音频（无字幕时用），返回音频文件路径；含应用级重试（rc=0但文件缺失也重试）"""
    args = [
        "-f", "bestaudio/best",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", os.path.join(output_dir, "%(id)s.%(ext)s"),
    ]
    for attempt in range(1, MAX_RETRIES + 1):
        run_ytdlp(args, url, platform)
        audio = _find_media(output_dir, (".mp3", ".m4a", ".wav", ".webm", ".opus"))
        if audio:
            return audio
        if attempt < MAX_RETRIES:
            wait = RETRY_BACKOFF[min(attempt - 1, len(RETRY_BACKOFF) - 1)]
            print(f"      ⚠️ 音频文件未生成(第{attempt}次)，{wait}秒后重试...")
            time.sleep(wait)
    return ""


def process_video(url: str, output_base: str = None) -> dict:
    """
    主流程：识别平台 → 抓元数据 → 优先字幕 → 无字幕下音频
    返回包含所有信息的 dict
    """
    platform = detect_platform(url)
    if platform == "unknown":
        return {"error": f"无法识别平台: {url}"}

    video_id = get_video_id(url, platform)
    if output_base is None:
        output_base = TEMP_BASE
    output_dir = os.path.join(output_base, f"{platform}_{video_id}")
    os.makedirs(output_dir, exist_ok=True)

    print(f"[1/4] 平台识别: {platform}")
    print(f"[2/4] 抓取元数据...")
    metadata = fetch_metadata(url, platform)
    if "error" in metadata:
        return metadata
    print(f"      标题: {metadata['title']}")
    print(f"      UP主: {metadata['uploader']}")
    print(f"      时长: {metadata['duration']}秒")

    result = {
        **metadata,
        "output_dir": output_dir,
        "has_subtitle": False,
        "subtitle_file": "",
        "audio_file": "",
    }

    print(f"[3/4] 检查字幕...")
    subs = list_subtitles(url, platform)
    if subs:
        print(f"      可用字幕: {subs[:5]}")
        # 优先中文
        target_lang = None
        for s in subs:
            if re.match(r"zh", s, re.IGNORECASE):
                target_lang = s
                break
        if target_lang is None:
            target_lang = subs[0]  # 退而求其次

        print(f"      下载字幕: {target_lang}")
        sub_file = download_subtitle(url, platform, output_dir, target_lang)
        if sub_file:
            result["has_subtitle"] = True
            result["subtitle_file"] = sub_file
            print(f"      字幕已保存: {sub_file}")
        else:
            print(f"      字幕下载失败，转音频")

    if not result["has_subtitle"]:
        print(f"[4/4] 无字幕，下载音频...")
        audio_file = download_audio(url, platform, output_dir)
        if audio_file:
            result["audio_file"] = audio_file
            print(f"      音频已保存: {audio_file}")
        else:
            result["error"] = "音频下载失败"
    else:
        print(f"[4/4] 已有字幕，跳过音频下载")

    # 保存 metadata.json
    meta_path = os.path.join(output_dir, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    result["metadata_file"] = meta_path

    print(f"\n✅ 完成！工作目录: {output_dir}")
    print(f"   元数据: {meta_path}")
    if result["has_subtitle"]:
        print(f"   字幕: {result['subtitle_file']}")
    else:
        print(f"   音频: {result['audio_file']}")

    return result


def main():
    parser = argparse.ArgumentParser(description="视频下载模块 - 统一入口")
    parser.add_argument("url", help="视频 URL")
    parser.add_argument("--output", "-o", help="输出根目录（默认临时目录）", default=None)
    parser.add_argument("--json", action="store_true", help="只输出 JSON 结果")
    args = parser.parse_args()

    result = process_video(args.url, args.output)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif "error" in result:
        print(f"❌ 错误: {result['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
