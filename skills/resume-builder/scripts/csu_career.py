#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中南大学就业信息网爬虫
- 抓取宣讲会列表 + 详情
- 抓取招聘公告列表 + 详情
- 按关键词筛选
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
from datetime import datetime

BASE_URL = "https://career.csu.edu.cn"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": BASE_URL,
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


def parse_teachin_list(html: str) -> list:
    """解析宣讲会列表页"""
    soup = BeautifulSoup(html, "html.parser")
    events = []

    # 宣讲会列表项
    items = soup.select(".infoList li, .listBox li, .teachin-list li, .news-list li")
    if not items:
        # 尝试更通用的选择器
        items = soup.select("ul li")

    for item in items:
        try:
            # 提取链接
            link = item.select_one("a[href*='teachin/view']")
            if not link:
                continue

            href = link.get("href", "")
            if href.startswith("/"):
                href = BASE_URL + href
            elif not href.startswith("http"):
                href = BASE_URL + "/" + href

            # 提取 ID
            id_match = re.search(r"/id/(\d+)", href)
            event_id = id_match.group(1) if id_match else ""

            # 提取公司名称
            company = link.get_text(strip=True)

            # 提取时间和地点（通常在 li 的其他子元素中）
            time_text = ""
            location = ""
            spans = item.select("span, .time, .location, .addr")
            for span in spans:
                text = span.get_text(strip=True)
                if re.search(r"\d{4}-\d{2}-\d{2}", text):
                    time_text = text
                elif "校区" in text or "楼" in text or "厅" in text:
                    location = text

            # 如果没找到时间，尝试从整个 li 文本中提取
            if not time_text:
                full_text = item.get_text(" ", strip=True)
                time_match = re.search(r"(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2}[^\s]*)", full_text)
                if time_match:
                    time_text = time_match.group(1)

            events.append({
                "id": event_id,
                "company": company,
                "time": time_text,
                "location": location,
                "url": href,
                "type": "宣讲会",
                "source": "中南大学就业网",
            })
        except Exception as e:
            continue

    return events


def parse_campus_list(html: str) -> list:
    """解析招聘公告列表页"""
    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    items = soup.select(".infoList li, .listBox li, .campus-list li, .news-list li")
    if not items:
        items = soup.select("ul li")

    for item in items:
        try:
            link = item.select_one("a[href*='campus/view']")
            if not link:
                continue

            href = link.get("href", "")
            if href.startswith("/"):
                href = BASE_URL + href
            elif not href.startswith("http"):
                href = BASE_URL + "/" + href

            id_match = re.search(r"/id/(\d+)", href)
            job_id = id_match.group(1) if id_match else ""

            title = link.get_text(strip=True)

            # 提取发布时间和工作城市
            publish_time = ""
            city = ""
            full_text = item.get_text(" ", strip=True)

            time_match = re.search(r"(\d{4}-\d{2}-\d{2})", full_text)
            if time_match:
                publish_time = time_match.group(1)

            city_match = re.search(r"工作城市[：:]\s*([^\s]+)", full_text)
            if city_match:
                city = city_match.group(1)

            jobs.append({
                "id": job_id,
                "title": title,
                "company": title,  # 招聘公告标题通常是公司名
                "publish_time": publish_time,
                "city": city,
                "url": href,
                "type": "招聘公告",
                "source": "中南大学就业网",
            })
        except Exception as e:
            continue

    return jobs


def parse_teachin_detail(html: str, url: str) -> dict:
    """解析宣讲会详情页（从 .container 提取）"""
    soup = BeautifulSoup(html, "html.parser")
    detail = {"url": url, "type": "宣讲会"}

    # 公司名称
    title_elem = soup.select_one("h1")
    if title_elem:
        detail["company"] = title_elem.get_text(strip=True)

    # 从 .container 提取信息
    container = soup.select_one(".container")
    if container:
        text = container.get_text("\n", strip=True)

        # 单位性质/行业/规模
        for label, key in [("单位性质", "company_type"), ("单位行业", "company_industry"), ("单位规模", "company_scale")]:
            match = re.search(rf"{label}[：:]\s*\n?([^\n]+)", text)
            if match:
                detail[key] = match.group(1).strip()

        # 宣讲时间
        match = re.search(r"宣讲时间[：:]\s*\n?([^\n]+)", text)
        if match:
            detail["time"] = match.group(1).strip()

        # 宣讲地址
        match = re.search(r"宣讲地址[：:]\s*\n?([^\n]+)", text)
        if match:
            detail["location"] = match.group(1).strip()

        # 招聘部门电话
        match = re.search(r"招聘部门电话[：:]\s*\n?([^\n]+)", text)
        if match:
            detail["contact_phone"] = match.group(1).strip()

        # 职位列表表格
        positions = []
        tables = container.select("table")
        for table in tables:
            rows = table.select("tr")
            for row in rows[1:]:  # 跳过表头
                cols = row.select("td")
                if len(cols) >= 4:
                    pos = {
                        "id": cols[0].get_text(strip=True),
                        "name": cols[1].get_text(strip=True),
                        "salary": cols[2].get_text(strip=True),
                        "work_type": cols[3].get_text(strip=True),
                        "majors": cols[4].get_text(strip=True) if len(cols) > 4 else "",
                        "count": cols[5].get_text(strip=True) if len(cols) > 5 else "",
                    }
                    if pos["name"] and len(pos["name"]) < 100:
                        positions.append(pos)
        if positions:
            detail["positions"] = positions

        # 宣讲会详情正文
        detail_idx = text.find("宣讲会详情")
        if detail_idx >= 0:
            detail["content"] = text[detail_idx:detail_idx + 2000]

    return detail


def parse_campus_detail(html: str, url: str) -> dict:
    """解析招聘公告详情页"""
    soup = BeautifulSoup(html, "html.parser")
    detail = {"url": url, "type": "招聘公告"}

    # 标题
    title_elem = soup.select_one("h1, .title, h2")
    if title_elem:
        detail["title"] = title_elem.get_text(strip=True)
        detail["company"] = title_elem.get_text(strip=True)

    # 工作城市
    full_text = soup.get_text(" ", strip=True)
    city_match = re.search(r"工作城市[：:]\s*([^\s]+)", full_text)
    if city_match:
        detail["city"] = city_match.group(1)

    # 发布时间
    time_match = re.search(r"发布时间[：:]\s*(\d{4}-\d{2}-\d{2})", full_text)
    if time_match:
        detail["publish_time"] = time_match.group(1)

    # 职位表格
    positions = []
    tables = soup.select("table")
    for table in tables:
        rows = table.select("tr")
        for row in rows[1:]:  # 跳过表头
            cols = row.select("td")
            if len(cols) >= 2:
                pos_name = cols[0].get_text(strip=True)
                pos_count = cols[1].get_text(strip=True) if len(cols) > 1 else ""
                if pos_name and len(pos_name) < 100:
                    positions.append({"name": pos_name, "count": pos_count})
    if positions:
        detail["positions"] = positions

    # 详情内容
    content_elem = soup.select_one(".content, .detail-content, .vT_detail_content")
    if content_elem:
        detail["content"] = content_elem.get_text("\n", strip=True)[:3000]
    else:
        main = soup.select_one("main, .main, #main, .container")
        if main:
            detail["content"] = main.get_text("\n", strip=True)[:3000]

    # 需求专业
    major_match = re.findall(r"【[^】]*】([^，,。\s]+)", full_text)
    if major_match:
        detail["majors"] = list(set(major_match))[:20]

    return detail


def crawl_teachin(max_pages: int = 3, keyword: str = None) -> list:
    """抓取宣讲会列表"""
    all_events = []
    seen_ids = set()

    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}/teachin/index?page={page}"
        print(f"[宣讲会] 抓取第 {page} 页: {url}")

        html = fetch_page(url)
        if not html:
            break

        events = parse_teachin_list(html)
        if not events:
            print(f"  → 未解析到宣讲会，可能页面结构变化")
            break

        new_count = 0
        for event in events:
            eid = event.get("id", "")
            if eid and eid not in seen_ids:
                seen_ids.add(eid)
                # 关键词筛选
                if keyword:
                    text = event.get("company", "") + event.get("location", "")
                    if keyword.lower() not in text.lower():
                        continue
                all_events.append(event)
                new_count += 1

        print(f"  → 新增 {new_count} 个宣讲会（累计 {len(all_events)}）")

        if new_count == 0 and not keyword:
            break

        time.sleep(1)

    return all_events


def crawl_campus(max_pages: int = 3, keyword: str = None) -> list:
    """抓取招聘公告列表"""
    all_jobs = []
    seen_ids = set()

    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}/campus/index?page={page}"
        print(f"[招聘公告] 抓取第 {page} 页: {url}")

        html = fetch_page(url)
        if not html:
            break

        jobs = parse_campus_list(html)
        if not jobs:
            print(f"  → 未解析到招聘公告，可能页面结构变化")
            break

        new_count = 0
        for job in jobs:
            jid = job.get("id", "")
            if jid and jid not in seen_ids:
                seen_ids.add(jid)
                if keyword:
                    text = job.get("title", "") + job.get("city", "")
                    if keyword.lower() not in text.lower():
                        continue
                all_jobs.append(job)
                new_count += 1

        print(f"  → 新增 {new_count} 个招聘公告（累计 {len(all_jobs)}）")

        if new_count == 0 and not keyword:
            break

        time.sleep(1)

    return all_jobs


def fetch_details(items: list, max_details: int = None) -> list:
    """批量抓取详情页"""
    if max_details:
        items = items[:max_details]

    total = len(items)
    for i, item in enumerate(items, 1):
        url = item.get("url", "")
        if not url:
            continue

        print(f"[{i}/{total}] 抓取详情: {item.get('company', item.get('title', ''))}")
        html = fetch_page(url)
        if not html:
            continue

        if item.get("type") == "宣讲会":
            detail = parse_teachin_detail(html, url)
        else:
            detail = parse_campus_detail(html, url)

        # 合并详情到列表项
        item.update(detail)
        time.sleep(0.5)

    return items


def main():
    parser = argparse.ArgumentParser(description="中南大学就业信息网爬虫")
    parser.add_argument("--type", "-t", choices=["teachin", "campus", "all"], default="all",
                        help="抓取类型：teachin=宣讲会, campus=招聘公告, all=全部")
    parser.add_argument("--pages", "-p", type=int, default=3, help="抓取页数（默认3）")
    parser.add_argument("--keyword", "-k", default=None, help="关键词筛选（如'计算机''软件''AI'）")
    parser.add_argument("--detail", action="store_true", help="是否抓取详情页")
    parser.add_argument("--max-detail", type=int, default=None, help="最多抓取多少个详情")
    parser.add_argument("--output", "-o", default=None, help="输出 JSON 文件路径")
    args = parser.parse_args()

    all_results = []

    if args.type in ("teachin", "all"):
        events = crawl_teachin(max_pages=args.pages, keyword=args.keyword)
        if args.detail and events:
            events = fetch_details(events, max_details=args.max_detail)
        all_results.extend(events)

    if args.type in ("campus", "all"):
        jobs = crawl_campus(max_pages=args.pages, keyword=args.keyword)
        if args.detail and jobs:
            jobs = fetch_details(jobs, max_details=args.max_detail)
        all_results.extend(jobs)

    # 打印结果
    print("\n" + "=" * 80)
    print(f"抓取完成：共 {len(all_results)} 条")
    print("=" * 80)

    teachin_count = sum(1 for r in all_results if r.get("type") == "宣讲会")
    campus_count = sum(1 for r in all_results if r.get("type") == "招聘公告")
    print(f"宣讲会: {teachin_count} 个 | 招聘公告: {campus_count} 个")

    for i, item in enumerate(all_results[:20], 1):
        if item.get("type") == "宣讲会":
            print(f"\n{i}. [宣讲会] {item.get('company', '')}")
            print(f"   时间: {item.get('time', '未知')} | 地点: {item.get('location', '未知')}")
        else:
            print(f"\n{i}. [招聘公告] {item.get('title', item.get('company', ''))}")
            print(f"   发布: {item.get('publish_time', '未知')} | 城市: {item.get('city', '未知')}")
        print(f"   链接: {item.get('url', '')}")

    if len(all_results) > 20:
        print(f"\n... 还有 {len(all_results) - 20} 条，详见输出文件")

    # 保存
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 结果已保存: {args.output}")


if __name__ == "__main__":
    main()
