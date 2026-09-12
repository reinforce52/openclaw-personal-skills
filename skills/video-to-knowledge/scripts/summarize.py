#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 总结模块 - 调用中南大学 deepseek-v3
输入: 转写文本/字幕 + 元数据
输出: 结构化总结 (JSON) + 主题建议
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path

# ============ 中南大学 API 配置 ============
API_BASE = "https://api.chat.csu.edu.cn/v1"
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")  # 从环境变量读取，不要硬编码密钥
MODEL = "deepseek-v3"

# 系统提示词 - 定义总结角色和输出结构（v2 细粒度知识点拆分）
SYSTEM_PROMPT = """你是一个专业的学习内容整理专家，擅长把视频/课程内容整理成结构化的深度学习知识库。

你的任务：根据视频转写文本和元数据，生成高质量的结构化学习笔记。
核心要求：**尽可能细化知识点**，并讲解知识点之间的联系与发展脉络（前置→当前→后续）。

输出要求（严格按以下 JSON 格式输出，不要输出 JSON 以外的任何内容）：
{
  "topic_suggestion": "建议归入的主题名称（2-6个字，如'控制工程'、'机器学习'、'英语长难句'）",
  "topic_reason": "为什么建议这个主题（一句话）",
  "one_sentence_summary": "一句话总结这个视频讲了什么",
  "video_overview": "视频整体内容概述（3-5句话，讲清楚视频的知识脉络和逻辑主线）",
  "knowledge_points": [
    {
      "point": "知识点名称（简洁明确）",
      "detail": "这个知识点的详细解释（4-6句话，讲清楚定义/原理/推导/应用）",
      "timestamp": "这个知识点在视频中出现的时间点，如'05:30'（没有则写'00:00'）",
      "importance": "高/中/低",
      "prerequisites": ["学习这个知识点需要先掌握的前置知识点1", "前置知识点2"],
      "follow_ups": ["学完这个知识点后可以继续学习的后续知识点1", "后续知识点2"],
      "related": ["与这个知识点相关联的其他知识点1", "关联知识点2"],
      "sub_points": ["这个知识点下的细分小知识点1", "细分小知识点2"],
      "key_formulas": ["关键公式1（如果有）", "关键公式2"],
      "examples": ["视频中讲到的典型例题或应用案例1", "案例2"]
    }
  ],
  "knowledge_chain": "知识点之间的逻辑发展脉络（按视频讲解顺序，用'→'连接，如'极限定义→导数定义→求导法则→微分中值定理'）",
  "key_timestamps": [
    {"time": "00:00", "content": "这个时间点的关键内容摘要"}
  ],
  "learning_suggestions": "针对这个主题的后续学习建议（2-3句话，包括推荐学习顺序、拓展方向）"
}

注意事项：
1. knowledge_points 尽可能细化，**至少5个，最多15个**，按视频讲解顺序排列
2. 每个知识点必须包含 prerequisites（前置）、follow_ups（后续）、related（关联），构建知识网络
3. knowledge_chain 必须讲清楚知识点的发展脉络，不是简单罗列
4. key_timestamps 选 8-15 个最关键的时间点
5. 所有内容必须来自转写文本，不要编造；转写文本可能有识别错误，根据上下文合理修正
6. 如果视频是音乐/无实质学习内容，topic_suggestion 写"非学习内容"，knowledge_points 为空数组
7. 公式用 LaTeX 格式，如 $\\frac{dy}{dx}$
"""


def read_transcript(transcript_path: str) -> str:
    """读取转写文本（支持 srt/vtt/txt，自动检测编码）"""
    if not os.path.exists(transcript_path):
        return ""

    # 自动检测编码（UTF-8 → GBK → GB2312 → Big5 → Latin-1）
    content = None
    for encoding in ["utf-8", "gbk", "gb2312", "big5", "latin-1"]:
        try:
            with open(transcript_path, "r", encoding=encoding) as f:
                content = f.read()
            # 检查是否有大量乱码（替换字符）
            if content.count("\ufffd") < len(content) * 0.1:
                break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if content is None:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

    ext = os.path.splitext(transcript_path)[1].lower()
    if ext in (".srt", ".vtt"):
        # 提取纯文本（去掉时间戳和序号）
        lines = []
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            # 跳过序号行
            if line.isdigit():
                continue
            # 跳过时间戳行
            if "-->" in line or line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
                continue
            lines.append(line)
        return " ".join(lines)
    else:
        # txt 格式（可能带时间戳）
        lines = []
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("[") and "]" in line:
                # 去掉时间戳前缀
                line = line.split("]", 1)[1].strip() if "]" in line else line
            if line:
                lines.append(line)
        return " ".join(lines)


def call_llm(transcript: str, metadata: dict) -> dict:
    """调用 LLM 生成总结"""
    # 构建用户消息
    meta_text = f"""视频元数据：
- 标题: {metadata.get('title', '未知')}
- UP主: {metadata.get('uploader', '未知')}
- 平台: {metadata.get('platform', '未知')}
- 时长: {metadata.get('duration', '0')}秒
- 链接: {metadata.get('url', '')}

转写文本（约{len(transcript)}字）：
{transcript[:12000]}"""  # 限制长度，避免超 token

    if len(transcript) > 12000:
        meta_text += "\n\n（注：转写文本过长，已截断前12000字）"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": meta_text},
        ],
        "temperature": 0.3,
        "max_tokens": 4000,
    }

    print(f"[LLM] 调用 {MODEL} 生成总结...")
    try:
        # 禁用系统代理（国内API不需要代理，避免代理未运行导致连接失败）
        resp = requests.post(
            f"{API_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
            proxies={"http": None, "https": None},
        )
        resp.raise_for_status()
        result = resp.json()
        content = result["choices"][0]["message"]["content"]

        # 解析 JSON（LLM 可能输出 markdown 代码块）
        content = content.strip()
        if content.startswith("```"):
            # 去掉代码块标记
            lines = content.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            content = "\n".join(lines)

        summary = json.loads(content)
        print(f"[LLM] 总结生成成功！")
        print(f"  建议主题: {summary.get('topic_suggestion', '?')}")
        print(f"  细粒度知识点: {len(summary.get('knowledge_points', []))} 个")
        print(f"  知识脉络: {summary.get('knowledge_chain', '?')[:80]}...")
        return summary

    except requests.exceptions.RequestException as e:
        return {"error": f"API 请求失败: {str(e)[:200]}"}
    except (json.JSONDecodeError, KeyError) as e:
        return {"error": f"解析 LLM 输出失败: {str(e)[:200]}\n原始输出: {content[:500] if 'content' in dir() else 'N/A'}"}


def process_summary(metadata_path: str, transcript_path: str = None, output_dir: str = None) -> dict:
    """
    主流程：读取元数据 + 转写 → 调用 LLM → 保存总结
    """
    # 读取元数据
    if not os.path.exists(metadata_path):
        return {"error": f"元数据文件不存在: {metadata_path}"}
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # 确定转写文件路径
    if transcript_path is None:
        # 从 metadata 里找
        transcript_path = metadata.get("subtitle_file") or metadata.get("txt_file") or ""
        if not transcript_path:
            # 在 output_dir 里找
            search_dir = output_dir or metadata.get("output_dir", "")
            if search_dir:
                for f in os.listdir(search_dir):
                    if f.endswith(".srt") or f.endswith(".txt"):
                        transcript_path = os.path.join(search_dir, f)
                        break

    if not transcript_path or not os.path.exists(transcript_path):
        return {"error": f"找不到转写/字幕文件: {transcript_path}"}

    print(f"[总结] 视频: {metadata.get('title', '?')}")
    print(f"[总结] 转写文件: {os.path.basename(transcript_path)}")

    # 读取转写
    transcript = read_transcript(transcript_path)
    if not transcript:
        return {"error": "转写文本为空"}
    print(f"[总结] 转写文本长度: {len(transcript)} 字")

    # 调用 LLM
    summary = call_llm(transcript, metadata)
    if "error" in summary:
        return summary

    # 保存总结（包含 metadata）
    if output_dir is None:
        output_dir = metadata.get("output_dir", os.path.dirname(metadata_path))
    os.makedirs(output_dir, exist_ok=True)

    full_summary = {
        **summary,
        "metadata": metadata,
        "transcript_file": transcript_path,
    }
    summary_path = os.path.join(output_dir, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(full_summary, f, ensure_ascii=False, indent=2)

    result = {
        **summary,
        "metadata": metadata,
        "summary_file": summary_path,
        "transcript_file": transcript_path,
    }
    print(f"[总结] 已保存: {summary_path}")
    return result


def main():
    parser = argparse.ArgumentParser(description="LLM 总结模块")
    parser.add_argument("metadata", help="metadata.json 路径")
    parser.add_argument("--transcript", "-t", help="转写/字幕文件路径（默认从 metadata 读取）", default=None)
    parser.add_argument("--output", "-o", help="输出目录", default=None)
    parser.add_argument("--json", action="store_true", help="只输出 JSON")
    args = parser.parse_args()

    result = process_summary(args.metadata, args.transcript, args.output)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif "error" in result:
        print(f"❌ 错误: {result['error']}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\n✅ 总结完成！建议主题: {result.get('topic_suggestion', '?')}")


if __name__ == "__main__":
    main()
