#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
knowledge_deep_dive.py - 对每个知识点做4-6路web深度搜索，生成扩展理解
输入: summary.json（含 knowledge_points）
输出: deep_dive.json（每个知识点的扩展内容：定义补充、应用场景、易错点、拓展知识、参考链接）
搜索: 必应中国（国内直连，主用）+ DuckDuckGo（VPN开启时备选）+ LLM 总结
"""

import os
import sys
import re
import json
import argparse
import requests
from urllib.parse import quote_plus
from pathlib import Path

# ============ LLM 配置（中南大学 deepseek-v3）============
API_BASE = "https://api.chat.csu.edu.cn/v1"
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")  # 从环境变量读取，不要硬编码密钥
MODEL = "deepseek-v3"

# ============ 搜索引擎配置 ============
# 主用必应中国（国内直连，不需要VPN）；DuckDuckGo 作为VPN开启时的备选
BING_URL = "https://cn.bing.com/search"
DDG_URL = "https://html.duckduckgo.com/html/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def bing_search(query: str, max_results: int = 5) -> list:
    """必应中国搜索（国内直连，主用）。返回标题+链接+摘要"""
    try:
        resp = requests.get(
            BING_URL,
            params={"q": query, "setlang": "zh-CN", "count": "10"},
            headers=HEADERS,
            timeout=12,
            proxies={"http": None, "https": None},
        )
        resp.raise_for_status()
        html = resp.text
        results = []
        # 按 b_algo 分割（不依赖 </li> 闭合，避免嵌套匹配失败）
        parts = re.split(r'<li class="b_algo"', html)[1:]
        for block in parts:
            block = block[:3000]  # 限制块大小，避免跨块
            m = re.search(r'<h2[^>]*>\s*<a[^>]*href="(http[^"]+)"[^>]*>(.*?)</a>', block, re.DOTALL)
            if not m:
                continue
            link = m.group(1)
            title = re.sub(r'<[^>]+>', '', m.group(2)).strip()
            # 摘要
            snippet = ""
            sm = re.search(r'<p[^>]*class="[^"]*b_lineclamp[^"]*"[^>]*>(.*?)</p>', block, re.DOTALL)
            if not sm:
                sm = re.search(r'<div class="b_caption">.*?<p[^>]*>(.*?)</p>', block, re.DOTALL)
            if not sm:
                sm = re.search(r'<p[^>]*>(.*?)</p>', block, re.DOTALL)
            if sm:
                snippet = re.sub(r'<[^>]+>', '', sm.group(1)).strip()
                snippet = snippet.replace('&ensp;', ' ').replace('&#0183;', '·').replace('&nbsp;', ' ')
            # 过滤必应自身链接
            if 'bing.com' in link or 'microsoft.com' in link:
                continue
            if title and link:
                results.append({"title": title, "url": link, "snippet": snippet})
            if len(results) >= max_results:
                break
        return results
    except Exception as e:
        print(f"  [必应搜索失败] {query}: {str(e)[:70]}")
        return []


def ddg_search(query: str, max_results: int = 5, proxy: str = None) -> list:
    """DuckDuckGo HTML 搜索（VPN开启时的备选，需要代理）"""
    proxies = {"http": proxy, "https": proxy} if proxy else {"http": None, "https": None}
    try:
        resp = requests.post(
            DDG_URL, data={"q": query, "b": ""}, headers=HEADERS,
            timeout=10, proxies=proxies,
        )
        resp.raise_for_status()
        html = resp.text
        results = []
        result_blocks = re.findall(r'<div class="result__body">(.*?)</div>\s*</div>', html, re.DOTALL)
        for block in result_blocks[:max_results]:
            title_m = re.search(r'<a[^>]*class="result__a"[^>]*>(.*?)</a>', block, re.DOTALL)
            link_m = re.search(r'<a[^>]*class="result__a"[^>]*href="([^"]*)"', block)
            snippet_m = re.search(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', block, re.DOTALL)
            title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip() if title_m else ""
            link = link_m.group(1) if link_m else ""
            snippet = re.sub(r'<[^>]+>', '', snippet_m.group(1)).strip() if snippet_m else ""
            if link.startswith("//duckduckgo.com/l/"):
                link = "https:" + link
            if title and link:
                results.append({"title": title, "url": link, "snippet": snippet})
        return results
    except Exception:
        return []


def web_search(query: str, max_results: int = 5) -> list:
    """统一搜索入口：先必应中国直连，结果不足再用DDG（若VPN可用）"""
    results = bing_search(query, max_results)
    if len(results) >= 2:
        return results
    # 必应结果太少，尝试常见VPN代理端口的DDG
    for port in [7897, 7890, 7892]:
        ddg = ddg_search(query, max_results, proxy=f"http://127.0.0.1:{port}")
        if ddg:
            seen = {r["url"] for r in results}
            for r in ddg:
                if r["url"] not in seen:
                    results.append(r)
            break
    return results[:max_results]


def generate_search_queries(point: str, video_topic: str) -> list:
    """为每个知识点生成4-6路搜索查询"""
    return [
        f"{point} 定义 原理",
        f"{point} 应用场景 实例",
        f"{point} 易错点 常见错误",
        f"{point} 与 {video_topic} 关系",
        f"{point} 拓展知识 进阶",
    ]


def call_llm_deep_dive(point: str, point_detail: str, search_results: list, video_topic: str) -> dict:
    """调用 LLM 基于搜索结果生成知识点扩展内容"""
    # 整理搜索结果
    search_text = ""
    for i, r in enumerate(search_results, 1):
        search_text += f"[{i}] {r['title']}\n    摘要: {r['snippet'][:200]}\n    链接: {r['url']}\n\n"

    system_prompt = """你是一个专业的学习内容扩展专家。你的任务是基于视频知识点和web搜索结果，生成深度扩展内容。

输出严格按以下JSON格式：
{
  "definition_enhanced": "对知识点定义的补充和深化（2-3句话，视频没讲透的部分）",
  "application_scenarios": ["应用场景1（具体实例）", "应用场景2"],
  "common_mistakes": ["常见错误1（错误做法+正确做法）", "常见错误2"],
  "extended_knowledge": "拓展知识（2-3句话，相关的进阶概念或跨学科联系）",
  "learning_path": "学习建议（1-2句话，这个知识点应该怎么学、学到什么程度）",
  "references": [{"title": "参考资料标题", "url": "链接"}]
}

要求：
1. 所有内容必须基于搜索结果，不要编造
2. 重点补充视频没讲透的部分
3. 应用场景要具体，不要空泛
4. 常见错误要讲清楚错误做法和正确做法
"""

    user_prompt = f"""视频主题: {video_topic}
知识点: {point}
视频中的讲解: {point_detail[:500]}

Web搜索结果:
{search_text}

请基于以上信息，生成这个知识点的深度扩展内容。"""

    try:
        resp = requests.post(
            f"{API_BASE}/chat/completions",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 2000,
            },
            timeout=60,
            proxies={"http": None, "https": None},
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()

        # 解析 JSON
        if content.startswith("```"):
            lines = content.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            content = "\n".join(lines)

        return json.loads(content)
    except Exception as e:
        print(f"  [LLM扩展失败] {point}: {str(e)[:80]}")
        return {
            "definition_enhanced": "",
            "application_scenarios": [],
            "common_mistakes": [],
            "extended_knowledge": "",
            "learning_path": "",
            "references": [],
        }


def deep_dive_topic(summary_path: str, output_path: str = None, max_points: int = None):
    """
    主流程：读取 summary.json → 对每个知识点web搜索 → LLM扩展 → 保存 deep_dive.json
    """
    if not os.path.exists(summary_path):
        return {"error": f"summary.json 不存在: {summary_path}"}

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    video_topic = summary.get("topic_suggestion", "未知主题")
    knowledge_points = summary.get("knowledge_points", [])

    if max_points:
        knowledge_points = knowledge_points[:max_points]

    print(f"[深度扩展] 主题: {video_topic}")
    print(f"[深度扩展] 知识点数量: {len(knowledge_points)}")
    print(f"[深度扩展] 开始 web 搜索 + LLM 扩展...\n")

    deep_dive_results = []
    for i, kp in enumerate(knowledge_points, 1):
        point = kp.get("point", "")
        detail = kp.get("detail", "")
        print(f"[{i}/{len(knowledge_points)}] {point}")

        # 1. 生成搜索查询
        queries = generate_search_queries(point, video_topic)

        # 2. 执行搜索（必应中国主用 + DDG备选，合并去重）
        all_results = []
        seen_urls = set()
        for q in queries:
            results = web_search(q, max_results=3)
            for r in results:
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    all_results.append(r)
            if len(all_results) >= 10:
                break

        print(f"  搜索结果: {len(all_results)} 条")

        # 3. LLM 扩展
        enhanced = call_llm_deep_dive(point, detail, all_results[:10], video_topic)

        # 4. 合并结果
        deep_dive_results.append({
            "point": point,
            "detail": detail,
            "timestamp": kp.get("timestamp", "00:00"),
            "importance": kp.get("importance", "中"),
            "prerequisites": kp.get("prerequisites", []),
            "follow_ups": kp.get("follow_ups", []),
            "related": kp.get("related", []),
            "sub_points": kp.get("sub_points", []),
            "key_formulas": kp.get("key_formulas", []),
            "examples": kp.get("examples", []),
            "enhanced": enhanced,
            "search_results": all_results[:10],
        })
        print(f"  扩展完成: {len(enhanced.get('application_scenarios', []))} 个应用场景, {len(enhanced.get('common_mistakes', []))} 个易错点\n")

    # 保存
    if output_path is None:
        output_path = os.path.join(os.path.dirname(summary_path), "deep_dive.json")

    output = {
        "topic": video_topic,
        "topic_suggestion": video_topic,
        "topic_reason": summary.get("topic_reason", ""),
        "video_overview": summary.get("video_overview", ""),
        "knowledge_chain": summary.get("knowledge_chain", ""),
        "one_sentence_summary": summary.get("one_sentence_summary", ""),
        "key_timestamps": summary.get("key_timestamps", []),
        "learning_suggestions": summary.get("learning_suggestions", ""),
        "metadata": summary.get("metadata", {}),  # 保留视频元数据（标题/平台/URL/video_id）
        "knowledge_points": deep_dive_results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[深度扩展] 完成！保存到: {output_path}")
    print(f"[深度扩展] 总计 {len(deep_dive_results)} 个知识点已扩展")
    return output


def main():
    parser = argparse.ArgumentParser(description="知识点web深度搜索扩展")
    parser.add_argument("summary_path", help="summary.json 路径")
    parser.add_argument("--output", "-o", default=None, help="输出 deep_dive.json 路径")
    parser.add_argument("--max-points", type=int, default=None, help="最多处理的知识点数量（调试用）")
    args = parser.parse_args()

    result = deep_dive_topic(args.summary_path, args.output, args.max_points)
    if "error" in result:
        print(f"错误: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
