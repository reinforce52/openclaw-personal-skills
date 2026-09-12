#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音转写模块 - faster-whisper GPU/CPU 加速
输入: 音频文件路径
输出: transcript.srt (带时间戳) + transcript.txt (纯文本)

长音频自动分段转写（>15分钟切分为10分钟一段，避免内存不足）
"""

import os
import sys
import argparse
import subprocess
import tempfile
from pathlib import Path

# 国内镜像配置（模型下载用）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


def _setup_cuda_dlls():
    """Windows下自动加载pip安装的nvidia cublas/cudnn DLL，启用GPU加速"""
    if sys.platform != "win32":
        return
    try:
        import glob
        # 在site-packages/nvidia/*/bin下查找CUDA DLL
        for path in sys.path:
            nvidia_root = os.path.join(path, "nvidia")
            if not os.path.isdir(nvidia_root):
                continue
            for bin_dir in glob.glob(os.path.join(nvidia_root, "*", "bin")):
                if os.path.isdir(bin_dir) and glob.glob(os.path.join(bin_dir, "*.dll")):
                    try:
                        os.add_dll_directory(bin_dir)
                    except (OSError, AttributeError):
                        pass
                    os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
    except Exception:
        pass


_setup_cuda_dlls()

# 分段转写阈值（秒）：超过此时长则分段
SEGMENT_THRESHOLD = 900  # 15分钟
# 每段时长（秒）
SEGMENT_DURATION = 480   # 8分钟（减小单段内存，避免超长视频累积崩溃）


def seconds_to_srt_time(seconds: float) -> str:
    """秒数转 SRT 时间格式 HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def get_audio_duration(audio_path: str) -> float:
    """用 ffprobe 获取音频时长（秒）"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True, timeout=30
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def split_audio(audio_path: str, output_dir: str, segment_duration: int = SEGMENT_DURATION) -> list:
    """
    用 ffmpeg 把长音频切分成多段
    返回: [(segment_path, start_offset_seconds), ...]
    """
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    segments_dir = os.path.join(output_dir, f"{base_name}_segments")
    os.makedirs(segments_dir, exist_ok=True)

    # ffmpeg 分段
    output_pattern = os.path.join(segments_dir, f"{base_name}_part%03d.mp3")
    cmd = [
        "ffmpeg", "-y", "-i", audio_path,
        "-f", "segment",
        "-segment_time", str(segment_duration),
        "-c", "copy",
        output_pattern,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        # copy 失败则重新编码
        cmd = [
            "ffmpeg", "-y", "-i", audio_path,
            "-f", "segment",
            "-segment_time", str(segment_duration),
            "-ar", "16000", "-ac", "1",
            output_pattern,
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    # 收集分段文件
    segments = []
    if os.path.exists(segments_dir):
        files = sorted(f for f in os.listdir(segments_dir) if f.endswith(".mp3"))
        for i, fname in enumerate(files):
            seg_path = os.path.join(segments_dir, fname)
            offset = i * segment_duration
            segments.append((seg_path, float(offset)))

    return segments


def transcribe_single(model, audio_path: str, language: str = None, time_offset: float = 0.0) -> tuple:
    """
    转写单个音频文件（VAD优先，失败回退无VAD）
    返回: (segments_list, info) ，segment 的 start/end 已加上 time_offset
    """
    def do_transcribe(use_vad):
        kwargs = dict(language=language, beam_size=5)
        if use_vad:
            kwargs["vad_filter"] = True
            kwargs["vad_parameters"] = dict(min_silence_duration_ms=500)
        return model.transcribe(audio_path, **kwargs)

    segments = None
    info = None
    # VAD 优先
    try:
        segments, info = do_transcribe(use_vad=True)
        seg_list = list(segments)
        if len(seg_list) > 0:
            # 加上时间偏移
            for s in seg_list:
                s.start += time_offset
                s.end += time_offset
            return seg_list, info
    except Exception as e:
        print(f"  [分段] VAD失败: {str(e)[:100]}，回退无VAD")

    # 无 VAD
    segments, info = do_transcribe(use_vad=False)
    seg_list = list(segments)
    for s in seg_list:
        s.start += time_offset
        s.end += time_offset
    return seg_list, info


def transcribe_audio(
    audio_path: str,
    output_dir: str = None,
    model_size: str = "small",
    language: str = None,
    device: str = "cuda",
    compute_type: str = "int8_float16",
) -> dict:
    """
    转写音频文件（长音频自动分段）
    返回: {srt_file, txt_file, segments_count, duration, language}
    """
    from faster_whisper import WhisperModel

    if not os.path.exists(audio_path):
        return {"error": f"音频文件不存在: {audio_path}"}

    if output_dir is None:
        output_dir = os.path.dirname(audio_path)
    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    srt_file = os.path.join(output_dir, f"{base_name}.srt")
    txt_file = os.path.join(output_dir, f"{base_name}.txt")

    # 获取音频时长，决定是否分段
    total_duration = get_audio_duration(audio_path)
    use_segmentation = total_duration > SEGMENT_THRESHOLD
    print(f"[转写] 音频时长: {total_duration:.1f}秒 ({total_duration/60:.1f}分钟)")
    if use_segmentation:
        print(f"[转写] 长音频（>{SEGMENT_THRESHOLD//60}分钟），启用分段转写，每段{SEGMENT_DURATION//60}分钟")

    # 模型加载（带自动回退：指定device → CPU → 更小模型base → tiny）
    model_fallback_chain = [
        (model_size, device, compute_type),
        (model_size, "cpu", "int8"),
        ("base", "cpu", "int8"),
        ("tiny", "cpu", "int8"),
    ]
    model = None
    actual_model = model_size
    for m_size, m_device, m_compute in model_fallback_chain:
        try:
            print(f"[转写] 尝试加载模型: {m_size} (device={m_device}, compute={m_compute})")
            model = WhisperModel(m_size, device=m_device, compute_type=m_compute)
            actual_model = m_size
            print(f"[转写] 模型加载成功: {m_size}")
            break
        except Exception as e:
            print(f"[转写] 加载失败({m_size}/{m_device}): {str(e)[:80]}，尝试下一个方案...")
            # 强制GC释放内存
            import gc
            gc.collect()
            continue
    if model is None:
        return {"error": "所有模型加载方案均失败（内存不足），请关闭其他程序后重试"}

    print(f"[转写] 开始转写: {os.path.basename(audio_path)}")

    all_segments = []
    detected_lang = "zh"
    actual_duration = total_duration

    try:
        if use_segmentation:
            # ===== 分段转写 =====
            print(f"[转写] 切分音频...")
            seg_files = split_audio(audio_path, output_dir)
            print(f"[转写] 共 {len(seg_files)} 段")

            import gc
            for idx, (seg_path, offset) in enumerate(seg_files, 1):
                print(f"[转写] 第 {idx}/{len(seg_files)} 段 (偏移 {offset:.0f}秒 = {offset/60:.1f}分钟)...")
                try:
                    seg_list, seg_info = transcribe_single(model, seg_path, language, offset)
                    all_segments.extend(seg_list)
                    if idx == 1:
                        detected_lang = seg_info.language
                        actual_duration = seg_info.duration
                    print(f"  → 本段 {len(seg_list)} 段，累计 {len(all_segments)} 段")
                    # 显式释放本段对象，防止长视频内存累积
                    del seg_list, seg_info
                except Exception as e:
                    print(f"  ⚠️ 第{idx}段转写失败: {str(e)[:150]}，继续下一段")
                finally:
                    # 转写完立即删除分段音频，释放空间
                    try:
                        os.remove(seg_path)
                    except OSError:
                        pass
                    # 每段后强制GC，释放faster-whisper内部缓存
                    gc.collect()

            # 清理空的分段目录
            seg_dir = os.path.join(output_dir, f"{base_name}_segments")
            try:
                if os.path.exists(seg_dir) and not os.listdir(seg_dir):
                    os.rmdir(seg_dir)
            except OSError:
                pass
        else:
            # ===== 整段转写（短视频） =====
            all_segments, info = transcribe_single(model, audio_path, language, 0.0)
            detected_lang = info.language
            actual_duration = info.duration
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"转写失败: {str(e)[:200]}"}

    count = len(all_segments)
    print(f"[转写] 检测语言: {detected_lang}")
    print(f"[转写] 完成！共 {count} 段")

    if count == 0:
        return {"error": "转写结果为空（0段），请检查音频文件"}

    # 写入 SRT 和 TXT
    srt_lines = []
    txt_lines = []
    for i, segment in enumerate(all_segments, 1):
        srt_lines.append(str(i))
        srt_lines.append(f"{seconds_to_srt_time(segment.start)} --> {seconds_to_srt_time(segment.end)}")
        srt_lines.append(segment.text.strip())
        srt_lines.append("")
        txt_lines.append(f"[{seconds_to_srt_time(segment.start)}] {segment.text.strip()}")

        if i % 50 == 0:
            print(f"[转写] 写入 {i}/{count}...")

    with open(srt_file, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines))

    print(f"[转写] SRT: {srt_file}")
    print(f"[转写] TXT: {txt_file}")

    return {
        "srt_file": srt_file,
        "txt_file": txt_file,
        "segments_count": count,
        "duration": actual_duration,
        "language": detected_lang,
    }


def main():
    parser = argparse.ArgumentParser(description="语音转写模块 - faster-whisper（支持长音频分段）")
    parser.add_argument("audio", help="音频文件路径")
    parser.add_argument("--output", "-o", help="输出目录（默认音频所在目录）", default=None)
    parser.add_argument("--model", "-m", help="模型大小: tiny/base/small/medium/large-v3", default="small")
    parser.add_argument("--language", "-l", help="指定语言 (zh/en/ja等，默认自动检测)", default=None)
    parser.add_argument("--cpu", action="store_true", help="强制使用 CPU")
    parser.add_argument("--json", action="store_true", help="只输出 JSON 结果")
    args = parser.parse_args()

    device = "cpu" if args.cpu else "cuda"
    compute_type = "int8" if args.cpu else "int8_float16"

    result = transcribe_audio(
        args.audio,
        output_dir=args.output,
        model_size=args.model,
        language=args.language,
        device=device,
        compute_type=compute_type,
    )

    if args.json:
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif "error" in result:
        print(f"❌ 错误: {result['error']}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\n✅ 转写完成！{result['segments_count']} 段")


if __name__ == "__main__":
    main()
