#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键求职流程 v2：多渠道搜索 → AI匹配 → 交互式选岗 → 生成定制简历
- 多渠道搜索：BOSS直聘 + 中南大学就业网 + 实习僧（可配置）
- BOSS岗位详情抓取：获取完整JD（非列表页简短描述）
- 交互式选岗：搜索匹配后暂停，展示清单让用户勾选
- 双Agent简历生成 + JD预分析 + PDF/Word导出
"""

import os
import sys
import json
import time
import argparse
import subprocess
from datetime import datetime

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")
DATA_DIR = os.path.join(SKILL_DIR, "data")
DEFAULT_OUTPUT_BASE = r"E:\obsidian\rein\简历库"

# 默认路径
DEFAULT_SCAN = os.path.join(SKILL_DIR, "scan_result.json")
DEFAULT_PERSONAL = os.path.join(SKILL_DIR, "config", "personal_info.json")
DEFAULT_BOSS_COOKIES = os.path.join(DATA_DIR, "boss_cookies.json")

# 把 scripts 目录加入 path，方便直接 import
sys.path.insert(0, SCRIPTS_DIR)


def run_script(script_name: str, args: list, desc: str = "", timeout: int = 600) -> bool:
    """运行子脚本，返回是否成功"""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    cmd = [sys.executable, script_path] + args
    print(f"\n{'='*60}")
    print(f"▶ {desc or script_name}")
    print(f"  命令: python {script_name} {' '.join(args)}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        if result.stdout:
            print(result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
        if result.stderr:
            print(f"[stderr] {result.stderr[-1000:]}", file=sys.stderr)
        if result.returncode != 0:
            print(f"⚠️ 脚本返回非零退出码: {result.returncode}", file=sys.stderr)
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"❌ 脚本超时（{timeout//60}分钟）", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ 脚本运行失败: {e}", file=sys.stderr)
        return False


# ============================================================
# 统一格式转换
# ============================================================
def normalize_job(job: dict, source: str) -> dict:
    """把不同渠道的岗位转换成统一格式"""
    normalized = {
        "job_id": job.get("job_id", job.get("uuid", job.get("id", ""))),
        "job_name": job.get("job_name", job.get("jobName", job.get("name", job.get("position", "")))),
        "salary": job.get("salary", job.get("salaryDesc", "")),
        "city": job.get("city", job.get("cityName", "")),
        "district": job.get("district", job.get("areaDistrict", job.get("location", ""))),
        "experience": job.get("experience", job.get("jobExperience", "")),
        "degree": job.get("degree", job.get("jobDegree", "")),
        "company_name": job.get("company_name", job.get("company", job.get("cname", job.get("brandName", "")))),
        "company_industry": job.get("company_industry", job.get("brandIndustry", job.get("industry", ""))),
        "company_scale": job.get("company_scale", job.get("brandScaleName", job.get("scale", ""))),
        "job_labels": job.get("job_labels", job.get("jobLabels", job.get("tags", []))),
        "job_description": job.get("job_description", job.get("postDescription", job.get("description", ""))),
        "job_url": job.get("job_url", job.get("url", "")),
        "source": source,
        "type": job.get("type", "社招"),
    }
    return normalized


# ============================================================
# 多渠道搜索
# ============================================================
def search_boss(keyword: str, city: str, pages: int, output_path: str) -> list:
    """搜索 BOSS 直聘岗位"""
    args = [
        keyword,
        "--city", city,
        "--pages", str(pages),
        "--output", output_path,
    ]
    success = run_script("boss_client.py", args, f"BOSS直聘搜索: {keyword} @ {city}")
    if success and os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            jobs = json.load(f)
        return [normalize_job(j, "BOSS直聘") for j in jobs]
    return []


def search_csu(keyword: str, pages: int, output_path: str) -> list:
    """搜索中南大学就业网（宣讲会+招聘公告）"""
    args = [
        "--type", "all",
        "--pages", str(pages),
        "--keyword", keyword,
        "--output", output_path,
    ]
    success = run_script("csu_career.py", args, f"中南大学就业网搜索: {keyword}")
    if success and os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # csu_career 可能返回 dict（含 teachin 和 campus）或 list
        jobs = []
        if isinstance(data, dict):
            for key in ["teachin", "campus", "jobs", "all"]:
                if key in data and isinstance(data[key], list):
                    jobs.extend(data[key])
        elif isinstance(data, list):
            jobs = data
        return [normalize_job(j, "中南大学就业网") for j in jobs]
    return []


def search_shixiseng(keyword: str, city: str, pages: int, output_path: str) -> list:
    """搜索实习僧"""
    args = [
        "--city", city,
        "--pages", str(pages),
        "--keyword", keyword,
        "--output", output_path,
    ]
    success = run_script("shixiseng_client.py", args, f"实习僧搜索: {keyword} @ {city}")
    if success and os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            jobs = json.load(f)
        return [normalize_job(j, "实习僧") for j in jobs]
    return []


def search_all_channels(keyword: str, city: str, pages: int, channels: list, output_dir: str) -> list:
    """多渠道合并搜索"""
    all_jobs = []
    channel_stats = {}

    if "boss" in channels:
        boss_path = os.path.join(output_dir, "jobs_boss.json")
        boss_jobs = search_boss(keyword, city, pages, boss_path)
        channel_stats["BOSS直聘"] = len(boss_jobs)
        all_jobs.extend(boss_jobs)

    if "csu" in channels:
        csu_path = os.path.join(output_dir, "jobs_csu.json")
        csu_jobs = search_csu(keyword, min(pages, 3), csu_path)
        channel_stats["中南大学就业网"] = len(csu_jobs)
        all_jobs.extend(csu_jobs)

    if "shixiseng" in channels:
        sxs_path = os.path.join(output_dir, "jobs_shixiseng.json")
        sxs_jobs = search_shixiseng(keyword, city, min(pages * 5, 10), sxs_path)
        channel_stats["实习僧"] = len(sxs_jobs)
        all_jobs.extend(sxs_jobs)

    # 去重（按 job_name + company_name）
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        key = f"{job.get('job_name','')}|{job.get('company_name','')}"
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)

    # 保存合并结果
    merged_path = os.path.join(output_dir, "jobs_all.json")
    with open(merged_path, "w", encoding="utf-8") as f:
        json.dump(unique_jobs, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"📊 多渠道搜索统计")
    print(f"{'='*60}")
    for ch, count in channel_stats.items():
        print(f"  {ch}: {count} 个")
    print(f"  合计（去重前）: {len(all_jobs)} 个")
    print(f"  合计（去重后）: {len(unique_jobs)} 个")
    print(f"  合并结果: {merged_path}")

    return unique_jobs


# ============================================================
# AI匹配打分
# ============================================================
def match_jobs(jobs_path: str, output_path: str, top: int = 10, max_jobs: int = 15) -> list:
    """AI 匹配打分"""
    args = [
        "--jobs", jobs_path,
        "--scan", DEFAULT_SCAN,
        "--personal", DEFAULT_PERSONAL,
        "--output", output_path,
        "--top", str(top),
        "--max-jobs", str(max_jobs),
    ]
    success = run_script("job_matcher.py", args, "AI匹配打分")
    if success and os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


# ============================================================
# BOSS岗位详情抓取
# ============================================================
def fetch_boss_job_detail(job: dict) -> str:
    """抓取 BOSS 岗位详情，返回完整 JD 文本"""
    job_id = job.get("job_id", "")
    if not job_id or job.get("source") != "BOSS直聘":
        return ""

    try:
        from boss_client import BossClient, CookieManager
        cookie_mgr = CookieManager(DEFAULT_BOSS_COOKIES)
        if not cookie_mgr.load_from_file():
            print("  ⚠️ 无法加载 BOSS Cookie，跳过详情抓取")
            return ""
        client = BossClient(cookie_mgr)
        detail = client.get_job_detail(job_id)

        if not detail:
            return ""

        # 从详情中提取完整 JD
        job_info = detail.get("jobInfo", {})
        description = job_info.get("postDescription", "")
        if not description:
            description = detail.get("postDescription", "")

        # 提取更多信息
        job_name = job_info.get("jobName", job.get("job_name", ""))
        salary = job_info.get("salaryDesc", job.get("salary", ""))
        city = job_info.get("cityName", job.get("city", ""))
        experience = job_info.get("jobExperience", job.get("experience", ""))
        degree = job_info.get("jobDegree", job.get("degree", ""))
        job_labels = job_info.get("jobLabels", job.get("job_labels", []))

        # 公司信息
        brand_info = detail.get("brandComInfo", {})
        company_name = brand_info.get("brandName", job.get("company_name", ""))
        company_industry = brand_info.get("brandIndustry", "")
        company_scale = brand_info.get("brandScaleName", "")

        lines = []
        lines.append(f"岗位名称: {job_name}")
        lines.append(f"公司: {company_name}")
        if company_industry:
            lines.append(f"行业: {company_industry}")
        if company_scale:
            lines.append(f"规模: {company_scale}")
        lines.append(f"薪资: {salary}")
        lines.append(f"地点: {city}")
        lines.append(f"经验要求: {experience}")
        lines.append(f"学历要求: {degree}")
        if job_labels:
            lines.append(f"岗位标签: {', '.join(job_labels) if isinstance(job_labels, list) else job_labels}")
        if description:
            lines.append(f"\n岗位描述:\n{description}")
        lines.append(f"\n岗位链接: {job.get('job_url', '')}")

        print(f"  ✅ 抓取到完整 JD（{len(description)} 字）")
        return "\n".join(lines)

    except Exception as e:
        print(f"  ⚠️ 抓取岗位详情失败: {e}")
        return ""


# ============================================================
# JD提取
# ============================================================
def extract_jd(job: dict, fetch_detail: bool = True) -> str:
    """从岗位数据中提取 JD 文本（优先抓取详情）"""
    # 优先抓取 BOSS 详情
    if fetch_detail and job.get("source") == "BOSS直聘":
        detail_jd = fetch_boss_job_detail(job)
        if detail_jd:
            return detail_jd

    # 回退到列表页数据
    lines = []
    lines.append(f"岗位名称: {job.get('job_name', '')}")
    lines.append(f"公司: {job.get('company_name', '')}")
    if job.get("company_industry"):
        lines.append(f"行业: {job['company_industry']}")
    if job.get("company_scale"):
        lines.append(f"规模: {job['company_scale']}")
    lines.append(f"薪资: {job.get('salary', '')}")
    lines.append(f"地点: {job.get('city', '')} {job.get('district', '')}")
    lines.append(f"经验要求: {job.get('experience', '')}")
    lines.append(f"学历要求: {job.get('degree', '')}")
    if job.get("job_labels"):
        labels = job["job_labels"]
        lines.append(f"岗位标签: {', '.join(labels) if isinstance(labels, list) else labels}")
    if job.get("job_description"):
        lines.append(f"\n岗位描述:\n{job['job_description']}")
    lines.append(f"\n岗位链接: {job.get('job_url', '')}")
    lines.append(f"来源: {job.get('source', '')}")
    return "\n".join(lines)


# ============================================================
# 生成单份简历
# ============================================================
def generate_resume_for_job(job: dict, output_dir: str, index: int, fetch_detail: bool = True) -> dict:
    """为单个岗位生成定制简历"""
    job_name = job.get("job_name", job.get("name", f"岗位{index}"))
    company = job.get("company_name", job.get("company", job.get("cname", "")))
    source = job.get("source", "")
    safe_name = f"{index:02d}_{company}_{job_name}".replace("/", "_").replace("\\", "_").replace(":", "_")[:60]
    job_dir = os.path.join(output_dir, safe_name)
    os.makedirs(job_dir, exist_ok=True)

    # 1. 提取并保存 JD（优先抓取详情）
    print(f"\n  📄 提取 JD（来源: {source}）...")
    jd_text = extract_jd(job, fetch_detail=fetch_detail)
    jd_path = os.path.join(job_dir, "JD.txt")
    with open(jd_path, "w", encoding="utf-8") as f:
        f.write(jd_text)

    # 2. 生成简历（含 JD 分析 + 双 Agent 循环）
    resume_md = os.path.join(job_dir, f"简历_{job_name}.md")
    jd_analysis = os.path.join(job_dir, "JD分析报告.md")
    review_history = os.path.join(job_dir, "评审历史.json")

    args = [
        "--scan", DEFAULT_SCAN,
        "--personal", DEFAULT_PERSONAL,
        "--role", job_name,
        "--jd", jd_path,
        "--output", resume_md,
        "--analyze-output", jd_analysis,
        "--review-output", review_history,
    ]
    success = run_script("generate_resume.py", args, f"生成简历: {job_name} @ {company}", timeout=900)
    if not success:
        return {"job": job_name, "company": company, "source": source, "status": "生成失败", "dir": job_dir}

    # 3. 导出 PDF
    pdf_path = os.path.join(job_dir, f"简历_{job_name}.pdf")
    if os.path.exists(resume_md):
        run_script("export_pdf.py", [resume_md, "--output", pdf_path], f"导出PDF: {job_name}")

    # 4. 导出 Word
    docx_path = os.path.join(job_dir, f"简历_{job_name}.docx")
    if os.path.exists(resume_md):
        run_script("export_docx.py", [resume_md, "--output", docx_path], f"导出Word: {job_name}")

    # 统计文件
    files = []
    for f in os.listdir(job_dir):
        fpath = os.path.join(job_dir, f)
        if os.path.isfile(fpath):
            size = os.path.getsize(fpath) / 1024
            files.append({"name": f, "size_kb": round(size, 1)})

    return {
        "job": job_name,
        "company": company,
        "source": source,
        "salary": job.get("salary", ""),
        "match_score": job.get("overall_score", ""),
        "status": "成功",
        "dir": job_dir,
        "files": files,
    }


# ============================================================
# 交互式选岗展示
# ============================================================
def print_job_list(jobs: list, top_n: int = 15):
    """打印岗位清单，供用户选择"""
    print(f"\n{'='*80}")
    print(f"📋 岗位匹配清单（Top {min(top_n, len(jobs))}）")
    print(f"{'='*80}")
    print(f"{'编号':<4} {'匹配度':<7} {'岗位':<25} {'公司':<20} {'薪资':<12} {'来源':<10}")
    print(f"{'-'*4} {'-'*7} {'-'*25} {'-'*20} {'-'*12} {'-'*10}")

    for i, job in enumerate(jobs[:top_n], 1):
        score = job.get("overall_score", job.get("match_score", "?"))
        name = job.get("job_name", "")[:24]
        company = job.get("company_name", job.get("company", ""))[:19]
        salary = job.get("salary", "")[:11]
        source = job.get("source", "")[:9]
        print(f"{i:<4} {str(score):<7} {name:<25} {company:<20} {salary:<12} {source:<10}")

    print(f"\n💡 选择方式：")
    print(f"  - 输入编号（多个用逗号分隔）: 1,3,5")
    print(f"  - 输入范围: 1-5")
    print(f"  - 输入 all: 全部生成")
    print(f"  - 输入 top3 / top5 / top10: 自动选前N个")
    print(f"  - 输入 exit: 退出不生成")
    print(f"{'='*80}")


def parse_selection(selection: str, total: int) -> list:
    """解析用户选择，返回岗位索引列表（0-based）"""
    selection = selection.strip().lower()

    if selection in ["exit", "quit", "q", "取消"]:
        return []

    if selection in ["all", "全部"]:
        return list(range(total))

    if selection.startswith("top"):
        try:
            n = int(selection.replace("top", ""))
            return list(range(min(n, total)))
        except ValueError:
            return list(range(min(3, total)))

    # 解析编号和范围
    indices = set()
    parts = selection.split(",")
    for part in parts:
        part = part.strip()
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                start = int(start.strip()) - 1
                end = int(end.strip()) - 1
                for i in range(max(0, start), min(end + 1, total)):
                    indices.add(i)
            except ValueError:
                continue
        else:
            try:
                idx = int(part) - 1
                if 0 <= idx < total:
                    indices.add(idx)
            except ValueError:
                continue

    return sorted(indices)


# ============================================================
# 汇总报告
# ============================================================
def generate_report(args, jobs, matched, results, output_dir, channels):
    """生成汇总报告"""
    report_path = os.path.join(output_dir, "流程汇总报告.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# 一键求职流程汇总报告\n\n")
        f.write(f"**关键词**: {args.keyword}  \n")
        f.write(f"**城市**: {args.city}  \n")
        f.write(f"**搜索渠道**: {', '.join(channels)}  \n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**搜索岗位数**: {len(jobs)}  \n")
        f.write(f"**匹配评估数**: {len(matched)}  \n")
        f.write(f"**生成简历数**: {len(results)}  \n\n")

        f.write("## 岗位匹配排名\n\n")
        f.write("| 排名 | 匹配度 | 岗位 | 公司 | 薪资 | 来源 | 状态 |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for i, r in enumerate(results, 1):
            f.write(f"| {i} | {r.get('match_score', '')} | {r.get('job', '')} | {r.get('company', '')} | {r.get('salary', '')} | {r.get('source', '')} | {r.get('status', '')} |\n")

        f.write("\n## 生成文件清单\n\n")
        for i, r in enumerate(results, 1):
            f.write(f"### {i}. {r.get('job', '')} @ {r.get('company', '')}（{r.get('source', '')}）\n\n")
            f.write(f"- 目录: `{r.get('dir', '')}`\n")
            f.write(f"- 状态: {r.get('status', '')}\n")
            if r.get("files"):
                f.write("- 文件:\n")
                for f_info in r["files"]:
                    f.write(f"  - {f_info['name']} ({f_info['size_kb']} KB)\n")
            f.write("\n")

        f.write("## 使用说明\n\n")
        f.write("1. 打开 `定制简历/` 目录，查看每个岗位的定制简历\n")
        f.write("2. `JD分析报告.md` 包含岗位要求分析、匹配度、技能差距、面试准备建议\n")
        f.write("3. `评审历史.json` 包含双Agent评审过程\n")
        f.write("4. PDF 用于投递，Word 用于手动调整\n")
        f.write("5. `jobs_all.json` 包含所有搜索到的岗位（多渠道合并去重）\n")

    return report_path


# ============================================================
# 主流程
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="一键求职流程 v2：多渠道搜索→AI匹配→交互式选岗→生成定制简历")
    parser.add_argument("--keyword", "-k", required=True, help="搜索关键词（如'机器视觉工程师'）")
    parser.add_argument("--city", "-c", default="长沙", help="城市（默认：长沙）")
    parser.add_argument("--pages", "-p", type=int, default=2, help="搜索页数（默认2）")
    parser.add_argument("--top", "-t", type=int, default=3, help="非交互模式下生成前N个岗位的简历（默认3）")
    parser.add_argument("--max-match", type=int, default=15, help="最多评估多少个岗位（默认15）")
    parser.add_argument("--output", "-o", default=None, help="输出目录")
    parser.add_argument("--channels", default="boss,csu,shixiseng", help="搜索渠道，逗号分隔（boss,csu,shixiseng），默认全部")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互式选岗（搜索匹配后暂停，展示清单让用户选择）")
    parser.add_argument("--select", default=None, help="指定岗位编号（如'1,3,5'或'1-5'或'top3'），非交互模式下覆盖--top")
    parser.add_argument("--skip-search", action="store_true", help="跳过搜索，使用已有的 jobs_all.json")
    parser.add_argument("--skip-match", action="store_true", help="跳过匹配，使用已有的 match_result.json")
    parser.add_argument("--skip-generate", action="store_true", help="只搜索+匹配，不生成简历（用于交互式选岗的第一阶段）")
    parser.add_argument("--no-detail", action="store_true", help="不抓取 BOSS 岗位详情（默认抓取）")
    parser.add_argument("--jobs-file", default=None, help="指定已有的岗位JSON文件")
    parser.add_argument("--match-file", default=None, help="指定已有的匹配结果JSON文件")
    args = parser.parse_args()

    # 解析渠道
    channels = [ch.strip() for ch in args.channels.split(",") if ch.strip()]

    # 输出目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not args.output:
        args.output = os.path.join(DEFAULT_OUTPUT_BASE, f"{args.keyword}_{timestamp}")
    os.makedirs(args.output, exist_ok=True)

    print(f"{'='*70}")
    print(f"🚀 一键求职流程 v2 启动")
    print(f"{'='*70}")
    print(f"关键词: {args.keyword}")
    print(f"城市: {args.city}")
    print(f"搜索渠道: {', '.join(channels)}")
    print(f"搜索页数: {args.pages}")
    print(f"交互模式: {'是' if args.interactive else '否'}")
    print(f"抓取BOSS详情: {'否' if args.no_detail else '是'}")
    print(f"输出目录: {args.output}")
    print(f"{'='*70}")

    # 步骤1：多渠道搜索岗位
    jobs_path = args.jobs_file or os.path.join(args.output, "jobs_all.json")
    if args.skip_search and os.path.exists(jobs_path):
        print(f"\n⏭️ 跳过搜索，加载已有岗位: {jobs_path}")
        with open(jobs_path, "r", encoding="utf-8") as f:
            jobs = json.load(f)
    else:
        jobs = search_all_channels(args.keyword, args.city, args.pages, channels, args.output)

    if not jobs:
        print("❌ 未搜索到岗位，流程终止", file=sys.stderr)
        sys.exit(1)
    print(f"\n✅ 搜索到 {len(jobs)} 个岗位（多渠道合并去重）")

    # 步骤2：AI匹配打分
    match_path = args.match_file or os.path.join(args.output, "match_result.json")
    if args.skip_match and os.path.exists(match_path):
        print(f"\n⏭️ 跳过匹配，加载已有结果: {match_path}")
        with open(match_path, "r", encoding="utf-8") as f:
            matched = json.load(f)
    else:
        matched = match_jobs(jobs_path, match_path, top=args.max_match, max_jobs=args.max_match)

    if not matched:
        print("❌ 匹配失败，流程终止", file=sys.stderr)
        sys.exit(1)
    print(f"\n✅ 匹配完成，共 {len(matched)} 个岗位评估结果")

    # 如果只搜索+匹配，不生成简历，到此结束
    if args.skip_generate:
        print(f"\n{'='*70}")
        print(f"✅ 搜索+匹配完成（未生成简历）")
        print(f"{'='*70}")
        print(f"岗位文件: {jobs_path}")
        print(f"匹配结果: {match_path}")
        print(f"\n💡 下一步：")
        print(f"  查看岗位清单后，运行以下命令生成简历：")
        print(f"  python job_pipeline.py -k '{args.keyword}' --skip-search --skip-match --select '1,3,5'")
        print(f"  或使用交互模式：python job_pipeline.py -k '{args.keyword}' --skip-search --skip-match --interactive")
        print_job_list(matched, top_n=min(15, len(matched)))
        return

    # 步骤3：选岗
    if args.interactive:
        # 交互模式：展示清单，等待用户输入
        print_job_list(matched, top_n=min(20, len(matched)))
        try:
            selection = input("\n请选择要生成简历的岗位编号: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n⚠️ 未选择，退出")
            return

        selected_indices = parse_selection(selection, len(matched))
        if not selected_indices:
            print("⚠️ 未选择有效岗位，退出")
            return
        top_jobs = [matched[i] for i in selected_indices]
        print(f"\n✅ 已选择 {len(top_jobs)} 个岗位")

    elif args.select:
        # 命令行指定选择
        selected_indices = parse_selection(args.select, len(matched))
        if not selected_indices:
            print(f"⚠️ 无法解析选择 '{args.select}'，使用默认 Top {args.top}")
            top_jobs = matched[:args.top]
        else:
            top_jobs = [matched[i] for i in selected_indices]
        print(f"\n✅ 已选择 {len(top_jobs)} 个岗位（--select {args.select}）")

    else:
        # 默认 Top N
        top_jobs = matched[:args.top]
        print(f"\n🎯 自动选择 Top {len(top_jobs)} 岗位生成简历:")

    for i, job in enumerate(top_jobs, 1):
        score = job.get("overall_score", job.get("match_score", "?"))
        print(f"  {i}. [{score}/100] {job.get('job_name', '')} @ {job.get('company_name', job.get('company', ''))} ({job.get('salary', '')}) [{job.get('source', '')}]")

    # 步骤4：为每个岗位生成简历
    results = []
    resume_dir = os.path.join(args.output, "定制简历")
    os.makedirs(resume_dir, exist_ok=True)

    for i, job in enumerate(top_jobs, 1):
        print(f"\n\n{'#'*70}")
        print(f"# 处理第 {i}/{len(top_jobs)} 个岗位")
        print(f"{'#'*70}")
        result = generate_resume_for_job(job, resume_dir, i, fetch_detail=not args.no_detail)
        results.append(result)
        print(f"\n📊 第 {i} 个岗位结果: {result['status']}")
        if result["status"] == "成功":
            for f in result.get("files", []):
                print(f"   - {f['name']} ({f['size_kb']} KB)")

    # 步骤5：输出汇总报告
    report_path = generate_report(args, jobs, matched, results, args.output, channels)

    print(f"\n\n{'='*70}")
    print(f"✅ 一键求职流程完成！")
    print(f"{'='*70}")
    print(f"输出目录: {args.output}")
    print(f"汇总报告: {report_path}")
    print(f"定制简历: {resume_dir}")
    print(f"\n生成结果:")
    for i, r in enumerate(results, 1):
        print(f"  {i}. [{r.get('match_score', '')}/100] {r.get('job', '')} @ {r.get('company', '')} [{r.get('source', '')}] → {r.get('status', '')}")


if __name__ == "__main__":
    main()
