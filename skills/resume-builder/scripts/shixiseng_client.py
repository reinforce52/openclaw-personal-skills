#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实习僧爬虫
- 按城市抓取实习岗位列表（内部 API，不需要 Cookie）
- 本地关键词过滤
- 抓取详情页获取完整信息
- 输出结构化 JSON
"""

import os
import sys
import json
import time
import re
import argparse
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.shixiseng.com"
API_URL = f"{BASE_URL}/app/interns"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": f"{BASE_URL}/interns",
}

# 城市编码映射（实习僧用中文名，部分城市可能需要编码）
CITY_NAMES = {
    "全国": "",
    "北京": "北京",
    "上海": "上海",
    "广州": "广州",
    "深圳": "深圳",
    "杭州": "杭州",
    "长沙": "长沙",
    "成都": "成都",
    "武汉": "武汉",
    "南京": "南京",
    "西安": "西安",
    "重庆": "重庆",
    "苏州": "苏州",
    "天津": "天津",
    "郑州": "郑州",
    "青岛": "青岛",
    "宁波": "宁波",
    "厦门": "厦门",
    "合肥": "合肥",
    "福州": "福州",
    "济南": "济南",
    "大连": "大连",
    "沈阳": "沈阳",
    "昆明": "昆明",
    "南昌": "南昌",
    "贵阳": "贵阳",
    "太原": "太原",
    "石家庄": "石家庄",
    "哈尔滨": "哈尔滨",
    "长春": "长春",
    "兰州": "兰州",
    "南宁": "南宁",
    "海口": "海口",
}


def fetch_page(url: str, timeout: int = 30) -> str:
    """获取页面 HTML"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except Exception as e:
        print(f"  ⚠️ 获取页面失败 {url}: {e}", file=sys.stderr)
        return ""


def search_interns(city: str = "长沙", max_pages: int = 5, keyword: str = None) -> list:
    """
    抓取实习岗位列表
    - 按城市抓取（API 不支持关键词搜索，在本地过滤）
    - 多页翻页
    """
    all_jobs = []
    seen_uuids = set()

    city_name = CITY_NAMES.get(city, city)

    for page in range(1, max_pages + 1):
        params = {"city": city_name, "page": page}
        print(f"[实习僧] 抓取第 {page} 页: city={city_name}")

        try:
            resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  ⚠️ API 请求失败: {e}", file=sys.stderr)
            break

        msg = data.get("msg", [])
        if not isinstance(msg, list) or not msg:
            print(f"  → 没有更多岗位")
            break

        new_count = 0
        for job in msg:
            uuid = job.get("uuid", "")
            if uuid and uuid not in seen_uuids:
                seen_uuids.add(uuid)

                # 本地关键词过滤
                if keyword:
                    text = job.get("name", "") + job.get("cname", "")
                    if keyword.lower() not in text.lower():
                        continue

                all_jobs.append({
                    "uuid": uuid,
                    "job_name": job.get("name", ""),
                    "company": job.get("cname", ""),
                    "city": job.get("city", ""),
                    "salary_min": job.get("minsal", 0),
                    "salary_max": job.get("maxsal", 0),
                    "salary": f"{job.get('minsal', 0)}-{job.get('maxsal', 0)}/天" if job.get("minsal", 0) > 0 else "面议",
                    "days_per_week": job.get("day", 0),
                    "publish_date": job.get("refresh", ""),
                    "logo": job.get("url", ""),
                    "job_url": f"{BASE_URL}/intern/{uuid}",
                    "type": "实习",
                    "source": "实习僧",
                })
                new_count += 1

        print(f"  → 新增 {new_count} 个（累计 {len(all_jobs)}）")

        if new_count == 0 and not keyword:
            break

        # 如果本页少于 10 个，说明没有更多了
        if len(msg) < 10:
            break

        time.sleep(1)

    return all_jobs


def fetch_job_detail(uuid: str) -> dict:
    """抓取岗位详情页"""
    url = f"{BASE_URL}/intern/{uuid}"
    html = fetch_page(url)
    if not html:
        return {}

    detail = {"url": url}
    soup = BeautifulSoup(html, "html.parser")

    # 从 __NUXT__ 中提取数据
    nuxt_match = re.search(r'window\.__NUXT__\s*=\s*(.+?)</script>', html, re.DOTALL)
    if nuxt_match:
        nuxt_text = nuxt_match.group(1)
        # 提取岗位详情（简单的文本提取）
        # 岗位描述通常在 detail 或 content 字段中
        desc_match = re.search(r'detail["\']?\s*:\s*["\'](.+?)["\']', nuxt_text)
        if desc_match:
            detail["description"] = desc_match.group(1)

    # 如果 __NUXT__ 提取失败，从页面文本中提取
    if "description" not in detail:
        # 尝试找岗位描述区域
        content = soup.select_one(".job-detail, .intern-detail, .detail-content, .content")
        if content:
            detail["description"] = content.get_text("\n", strip=True)[:3000]
        else:
            # 从整个页面提取主要文本
            main = soup.select_one("main, .main, #app, .container")
            if main:
                detail["description"] = main.get_text("\n", strip=True)[:3000]

    # 提取公司信息
    company_elem = soup.select_one(".company-name, .cname, .company-info h3")
    if company_elem:
        detail["company_full"] = company_elem.get_text(strip=True)

    # 提取职位标签
    tags = []
    for tag in soup.select(".job-tags span, .tags span, .label"):
        tag_text = tag.get_text(strip=True)
        if tag_text and len(tag_text) < 20:
            tags.append(tag_text)
    if tags:
        detail["tags"] = list(set(tags))[:15]

    return detail


def fetch_details(jobs: list, max_details: int = None) -> list:
    """批量抓取详情页"""
    if max_details:
        jobs = jobs[:max_details]

    total = len(jobs)
    for i, job in enumerate(jobs, 1):
        uuid = job.get("uuid", "")
        if not uuid:
            continue

        print(f"[{i}/{total}] 抓取详情: {job.get('job_name', '')} @ {job.get('company', '')}")
        detail = fetch_job_detail(uuid)
        job.update(detail)
        time.sleep(0.5)

    return jobs


def main():
    parser = argparse.ArgumentParser(description="实习僧爬虫")
    parser.add_argument("--city", "-c", default="长沙", help="城市（默认：长沙）")
    parser.add_argument("--keyword", "-k", default=None, help="关键词过滤（本地过滤）")
    parser.add_argument("--pages", "-p", type=int, default=5, help="抓取页数（默认5，每页10个）")
    parser.add_argument("--detail", action="store_true", help="是否抓取详情页")
    parser.add_argument("--max-detail", type=int, default=None, help="最多抓取多少个详情")
    parser.add_argument("--output", "-o", default=None, help="输出 JSON 文件路径")
    args = parser.parse_args()

    # 抓取列表
    jobs = search_interns(city=args.city, max_pages=args.pages, keyword=args.keyword)

    # 抓取详情
    if args.detail and jobs:
        jobs = fetch_details(jobs, max_details=args.max_detail)

    # 打印结果
    print("\n" + "=" * 80)
    print(f"抓取完成：共 {len(jobs)} 个实习岗位")
    print("=" * 80)

    for i, job in enumerate(jobs[:20], 1):
        print(f"\n{i}. {job.get('job_name', '')} | {job.get('salary', '')}")
        print(f"   公司: {job.get('company', '')}")
        print(f"   城市: {job.get('city', '')} | 每周: {job.get('days_per_week', 0)}天 | 发布: {job.get('publish_date', '')}")
        print(f"   链接: {job.get('job_url', '')}")

    if len(jobs) > 20:
        print(f"\n... 还有 {len(jobs) - 20} 个，详见输出文件")

    # 保存
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 结果已保存: {args.output}")


if __name__ == "__main__":
    main()
