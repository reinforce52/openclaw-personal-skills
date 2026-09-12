#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOSS直聘 API 客户端
- 基于真实浏览器 Cookie + requests 直接调用 BOSS 内部 API
- 绕过字体反爬（API 返回明文薪资）
- 自动处理风控（code=37 时提示重新登录）
"""

import os
import sys
import json
import time
import requests
from urllib.parse import quote

# ============================================================
# 城市编码映射（常用城市）
# ============================================================
CITY_CODES = {
    "全国": "100010000",
    "北京": "101010100",
    "上海": "101020100",
    "广州": "101280100",
    "深圳": "101280600",
    "杭州": "101210100",
    "长沙": "101250100",
    "成都": "101270100",
    "武汉": "101200100",
    "南京": "101190100",
    "西安": "101110100",
    "重庆": "101040100",
    "苏州": "101190400",
    "天津": "101030100",
    "郑州": "101180100",
    "青岛": "101120200",
    "宁波": "101210400",
    "厦门": "101230200",
    "合肥": "101220100",
    "福州": "101230100",
    "济南": "101120100",
    "大连": "101070200",
    "沈阳": "101070100",
    "昆明": "101290100",
    "南昌": "101240100",
    "贵阳": "101260100",
    "太原": "101100100",
    "石家庄": "101090100",
    "哈尔滨": "101050100",
    "长春": "101060100",
    "兰州": "101160100",
    "南宁": "101300100",
    "海口": "101310100",
    "呼和浩特": "101080100",
    "乌鲁木齐": "101130100",
    "银川": "101170100",
    "西宁": "101150100",
    "拉萨": "101140100",
}

# ============================================================
# BOSS API 端点
# ============================================================
BASE_URL = "https://www.zhipin.com"
SEARCH_API = f"{BASE_URL}/wapi/zpgeek/search/joblist.json"
JOB_DETAIL_API = f"{BASE_URL}/wapi/zpgeek/job/detail.json"

# 请求头（模拟浏览器）
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.zhipin.com/web/geek/job",
    "Origin": "https://www.zhipin.com",
    "Connection": "keep-alive",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
}


# ============================================================
# Cookie 管理
# ============================================================
class CookieManager:
    """BOSS直聘 Cookie 管理器"""

    def __init__(self, cookie_file: str = None):
        self.cookie_file = cookie_file or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "boss_cookies.json"
        )
        self.cookies = {}
        self._ensure_dir()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)

    def load_from_file(self) -> bool:
        """从文件加载 Cookie"""
        if not os.path.exists(self.cookie_file):
            return False
        try:
            with open(self.cookie_file, "r", encoding="utf-8") as f:
                self.cookies = json.load(f)
            return bool(self.cookies)
        except Exception as e:
            print(f"⚠️ 加载 Cookie 文件失败: {e}", file=sys.stderr)
            return False

    def save_to_file(self):
        """保存 Cookie 到文件"""
        try:
            with open(self.cookie_file, "w", encoding="utf-8") as f:
                json.dump(self.cookies, f, ensure_ascii=False, indent=2)
            print(f"✅ Cookie 已保存: {self.cookie_file}")
        except Exception as e:
            print(f"⚠️ 保存 Cookie 失败: {e}", file=sys.stderr)

    def load_from_browser(self, browser: str = "chrome") -> bool:
        """
        从浏览器自动读取 BOSS直聘 Cookie
        browser: chrome / edge / firefox
        """
        try:
            import browser_cookie3
            if browser == "chrome":
                cj = browser_cookie3.chrome(domain_name="zhipin.com")
            elif browser == "edge":
                cj = browser_cookie3.edge(domain_name="zhipin.com")
            elif browser == "firefox":
                cj = browser_cookie3.firefox(domain_name="zhipin.com")
            else:
                print(f"❌ 不支持的浏览器: {browser}", file=sys.stderr)
                return False

            self.cookies = {}
            for cookie in cj:
                self.cookies[cookie.name] = cookie.value

            if self.cookies.get("__zp_stoken__"):
                print(f"✅ 从 {browser} 读取 Cookie 成功（{len(self.cookies)} 个）")
                self.save_to_file()
                return True
            else:
                print(f"⚠️ 从 {browser} 读取到 Cookie，但未找到 __zp_stoken__，请确认已登录 BOSS直聘", file=sys.stderr)
                return False
        except ImportError:
            print("❌ 未安装 browser_cookie3，请运行: pip install browser_cookie3", file=sys.stderr)
            return False
        except Exception as e:
            print(f"⚠️ 从浏览器读取 Cookie 失败: {e}", file=sys.stderr)
            print("   提示：请确保浏览器已关闭，或使用手动导入方式", file=sys.stderr)
            return False

    def load_from_string(self, cookie_string: str) -> bool:
        """
        从 Cookie 字符串导入（从浏览器开发者工具复制）
        格式: name1=value1; name2=value2; ...
        """
        try:
            self.cookies = {}
            for pair in cookie_string.split(";"):
                pair = pair.strip()
                if "=" in pair:
                    name, value = pair.split("=", 1)
                    self.cookies[name.strip()] = value.strip()
            if self.cookies.get("__zp_stoken__"):
                print(f"✅ Cookie 字符串导入成功（{len(self.cookies)} 个）")
                self.save_to_file()
                return True
            else:
                print("⚠️ Cookie 字符串中未找到 __zp_stoken__，请确认已登录", file=sys.stderr)
                return False
        except Exception as e:
            print(f"❌ Cookie 字符串解析失败: {e}", file=sys.stderr)
            return False

    def get_cookie_header(self) -> str:
        """获取 Cookie 请求头字符串"""
        return "; ".join(f"{k}={v}" for k, v in self.cookies.items())

    def is_valid(self) -> bool:
        """检查 Cookie 是否有效（至少包含 __zp_stoken__）"""
        return bool(self.cookies.get("__zp_stoken__"))


# ============================================================
# BOSS 直聘 API 客户端
# ============================================================
class BossClient:
    """BOSS直聘 API 客户端"""

    def __init__(self, cookie_manager: CookieManager = None):
        self.cookie_manager = cookie_manager or CookieManager()
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self._last_request_time = 0
        self._request_interval = 2.0  # 请求间隔（秒），避免触发风控

    def _rate_limit(self):
        """请求限流"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._request_interval:
            time.sleep(self._request_interval - elapsed)
        self._last_request_time = time.time()

    def _request(self, method: str, url: str, **kwargs) -> dict:
        """发送请求，处理风控"""
        self._rate_limit()

        # 确保 Cookie 在请求头中
        headers = kwargs.pop("headers", {})
        headers["Cookie"] = self.cookie_manager.get_cookie_header()
        kwargs["headers"] = headers

        try:
            resp = self.session.request(method, url, timeout=30, **kwargs)
            resp.raise_for_status()
            data = resp.json()

            # 处理风控
            code = data.get("code", 0)
            if code == 37:
                print("\n⚠️ BOSS直聘风控触发（code=37），Cookie 可能已失效", file=sys.stderr)
                print("   请重新登录 BOSS直聘后更新 Cookie", file=sys.stderr)
                print("   方式1: 关闭浏览器后运行 --from-browser chrome", file=sys.stderr)
                print("   方式2: 从浏览器复制 Cookie 字符串后运行 --from-string", file=sys.stderr)
                return {"error": "风控触发，请重新登录", "code": 37}

            if code != 0:
                message = data.get("message", "未知错误")
                print(f"⚠️ API 返回错误: code={code}, message={message}", file=sys.stderr)
                return {"error": message, "code": code}

            return data

        except requests.exceptions.RequestException as e:
            print(f"❌ 请求失败: {e}", file=sys.stderr)
            return {"error": str(e), "code": -1}
        except json.JSONDecodeError:
            print("❌ 响应不是有效的 JSON", file=sys.stderr)
            return {"error": "响应解析失败", "code": -2}

    def search_jobs(
        self,
        keyword: str,
        city: str = "全国",
        page: int = 1,
        page_size: int = 30,
        salary: str = None,
        experience: str = None,
        degree: str = None,
    ) -> list:
        """
        搜索岗位
        :param keyword: 搜索关键词（如"机器视觉工程师"）
        :param city: 城市名称（如"长沙"）或城市编码
        :param page: 页码（从1开始）
        :param page_size: 每页数量（最大30）
        :param salary: 薪资筛选（如"404"=3-5K, "405"=5-10K, "406"=10-15K, "407"=15-20K, "408"=20-30K, "409"=30-50K, "410"=50K以上）
        :param experience: 经验筛选（如"101"=应届生, "102"=1年以下, "103"=1-3年, "104"=3-5年, "105"=5-10年, "106"=10年以上）
        :param degree: 学历筛选（如"209"=大专, "203"=本科, "204"=硕士, "205"=博士）
        :return: 岗位列表
        """
        # 解析城市编码
        city_code = CITY_CODES.get(city, city) if not city.isdigit() else city

        # 构建请求参数
        params = {
            "scene": 1,
            "query": keyword,
            "city": city_code,
            "page": page,
            "pageSize": min(page_size, 30),
        }

        # 可选筛选条件
        if salary:
            params["salary"] = salary
        if experience:
            params["experience"] = experience
        if degree:
            params["degree"] = degree

        print(f"[BOSS搜索] 关键词='{keyword}', 城市='{city}'({city_code}), 第{page}页")

        data = self._request("GET", SEARCH_API, params=params)

        if data.get("error"):
            return []

        # 解析岗位列表
        job_list = data.get("zpData", {}).get("jobList", [])
        jobs = []
        for job in job_list:
            jobs.append(self._parse_job(job))

        print(f"  → 获取到 {len(jobs)} 个岗位")
        return jobs

    def _parse_job(self, job: dict) -> dict:
        """解析单个岗位数据"""
        return {
            "job_id": job.get("encryptJobId", ""),
            "job_name": job.get("jobName", ""),
            "salary": job.get("salaryDesc", ""),
            "city": job.get("cityName", ""),
            "district": job.get("areaDistrict", ""),
            "experience": job.get("jobExperience", ""),
            "degree": job.get("jobDegree", ""),
            "company_name": job.get("brandName", ""),
            "company_industry": job.get("brandIndustry", ""),
            "company_scale": job.get("brandScaleName", ""),
            "company_stage": job.get("brandStageName", ""),
            "hr_name": job.get("bossName", ""),
            "hr_title": job.get("bossTitle", ""),
            "hr_online": job.get("bossOnline", False),
            "job_labels": job.get("jobLabels", []),
            "job_description": job.get("postDescription", ""),
            "job_url": f"{BASE_URL}/job_detail/{job.get('encryptJobId', '')}.html",
            "publish_time": job.get("lastModifyTime", ""),
            "source": "BOSS直聘",
        }

    def get_job_detail(self, job_id: str) -> dict:
        """获取岗位详情"""
        params = {"jobId": job_id}
        data = self._request("GET", JOB_DETAIL_API, params=params)
        if data.get("error"):
            return {}
        return data.get("zpData", {})

    def search_jobs_multi_page(
        self,
        keyword: str,
        city: str = "全国",
        max_pages: int = 3,
        **kwargs,
    ) -> list:
        """
        多页搜索岗位
        :param max_pages: 最大页数
        """
        all_jobs = []
        seen_ids = set()

        for page in range(1, max_pages + 1):
            jobs = self.search_jobs(keyword, city=city, page=page, **kwargs)
            if not jobs:
                break

            new_jobs = 0
            for job in jobs:
                job_id = job.get("job_id", "")
                if job_id and job_id not in seen_ids:
                    seen_ids.add(job_id)
                    all_jobs.append(job)
                    new_jobs += 1

            if new_jobs == 0:
                print("  → 没有新岗位，停止翻页")
                break

            # 如果本页数量少于 page_size，说明没有更多了
            if len(jobs) < kwargs.get("page_size", 30):
                break

        print(f"\n✅ 多页搜索完成：共 {len(all_jobs)} 个岗位（去重后）")
        return all_jobs


# ============================================================
# 命令行入口
# ============================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="BOSS直聘岗位搜索工具")
    parser.add_argument("keyword", nargs="?", help="搜索关键词（如'机器视觉工程师'）")
    parser.add_argument("--city", "-c", default="全国", help="城市（默认：全国）")
    parser.add_argument("--pages", "-p", type=int, default=1, help="搜索页数（默认：1）")
    parser.add_argument("--output", "-o", help="输出 JSON 文件路径")
    parser.add_argument("--from-browser", choices=["chrome", "edge", "firefox"], help="从浏览器读取 Cookie")
    parser.add_argument("--from-string", help="从 Cookie 字符串导入")
    parser.add_argument("--salary", help="薪资筛选（404=3-5K, 406=10-15K, 408=20-30K）")
    parser.add_argument("--experience", help="经验筛选（101=应届生, 103=1-3年, 104=3-5年）")
    parser.add_argument("--degree", help="学历筛选（203=本科, 204=硕士）")
    args = parser.parse_args()

    cookie_mgr = CookieManager()

    # Cookie 获取方式
    if args.from_browser:
        cookie_mgr.load_from_browser(args.from_browser)
    elif args.from_string:
        cookie_mgr.load_from_string(args.from_string)
    else:
        # 默认从文件加载
        if not cookie_mgr.load_from_file():
            print("❌ 未找到有效的 Cookie，请先登录 BOSS直聘")
            print("   方式1: 关闭浏览器后运行 --from-browser chrome")
            print("   方式2: 从浏览器复制 Cookie 字符串后运行 --from-string 'xxx'")
            sys.exit(1)

    if not cookie_mgr.is_valid():
        print("❌ Cookie 无效（缺少 __zp_stoken__），请重新登录")
        sys.exit(1)

    # 如果没有关键词，只验证 Cookie
    if not args.keyword:
        print("✅ Cookie 有效，可以开始搜索岗位")
        print(f"   使用方式: python boss_client.py '机器视觉工程师' --city 长沙 --pages 3")
        sys.exit(0)

    # 搜索岗位
    client = BossClient(cookie_mgr)
    jobs = client.search_jobs_multi_page(
        args.keyword,
        city=args.city,
        max_pages=args.pages,
        salary=args.salary,
        experience=args.experience,
        degree=args.degree,
    )

    if not jobs:
        print("⚠️ 未搜索到岗位")
        sys.exit(0)

    # 输出结果
    print("\n" + "=" * 80)
    print(f"搜索结果：共 {len(jobs)} 个岗位")
    print("=" * 80)
    for i, job in enumerate(jobs, 1):
        print(f"\n{i}. {job['job_name']} | {job['salary']}")
        print(f"   公司: {job['company_name']} ({job['company_industry']}, {job['company_scale']})")
        print(f"   地点: {job['city']}·{job['district']} | 经验: {job['experience']} | 学历: {job['degree']}")
        print(f"   HR: {job['hr_name']} ({job['hr_title']}) {'在线' if job['hr_online'] else '离线'}")
        print(f"   链接: {job['job_url']}")

    # 保存到文件
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 结果已保存: {args.output}")


if __name__ == "__main__":
    main()
