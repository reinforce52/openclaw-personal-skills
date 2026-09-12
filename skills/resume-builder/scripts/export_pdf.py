#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 导出模块 - Markdown 简历 → ATS 友好的 PDF（带头像）
使用 Chrome headless 打印 HTML 为 PDF，纯文字可选中，通过 ATS 解析
"""

import os
import sys
import re
import argparse
import tempfile
import subprocess
import markdown


# Chrome 路径（按优先级查找）
CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

# 默认头像路径
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_AVATAR = os.path.join(SKILL_DIR, "assets", "avatar.jpg")

RESUME_CSS = """
@page {
    size: A4;
    margin: 1.5cm 1.8cm;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: "Microsoft YaHei", "PingFang SC", "SimSun", sans-serif;
    font-size: 10.5pt;
    line-height: 1.5;
    color: #1a1a1a;
}

/* 简历头部：左右布局 */
.resume-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 10pt;
    padding-bottom: 8pt;
    border-bottom: 2pt solid #333;
}
.header-left {
    flex: 1;
    padding-right: 20pt;
}
.header-left h1 {
    font-size: 22pt;
    text-align: left;
    margin: 0 0 4pt 0;
    color: #1a1a1a;
    border: none;
}
.header-left .contact {
    font-size: 9.5pt;
    color: #555;
    margin: 0;
    line-height: 1.6;
}
.header-right {
    flex-shrink: 0;
}
.header-avatar {
    width: 95px;
    height: 125px;
    object-fit: cover;
    border-radius: 6px;
    border: 1px solid #ddd;
}

/* 正文样式 */
h2 {
    font-size: 12pt;
    color: #1a1a1a;
    border-bottom: 1.5pt solid #333;
    padding-bottom: 2pt;
    margin: 12pt 0 6pt 0;
}
h3 {
    font-size: 11pt;
    color: #1a1a1a;
    margin: 8pt 0 2pt 0;
}
h3 + p {
    font-size: 9pt;
    color: #666;
    margin: 0 0 4pt 0;
}
p { margin: 3pt 0; }
ul {
    margin: 3pt 0;
    padding-left: 18pt;
}
li { margin: 2pt 0; }
strong { color: #1a1a1a; }
hr {
    border: none;
    border-top: 0.5pt solid #ccc;
    margin: 6pt 0;
}
"""


def find_browser() -> str:
    """查找 Chrome/Edge 可执行文件"""
    for path in CHROME_PATHS:
        if os.path.exists(path):
            return path
    return None


def build_header_html(avatar_path: str = None) -> str:
    """构建头部 HTML 占位符（后续替换真实内容）"""
    avatar_html = ""
    if avatar_path and os.path.exists(avatar_path):
        # 用 file:// 协议引用本地图片
        avatar_url = "file:///" + avatar_path.replace("\\", "/")
        avatar_html = f'<div class="header-right"><img src="{avatar_url}" class="header-avatar" alt="头像"></div>'
    return avatar_html


def md_to_pdf(md_path: str, pdf_path: str, avatar_path: str = None) -> bool:
    """Markdown → PDF（通过 Chrome headless）"""
    if not os.path.exists(md_path):
        print(f"❌ 文件不存在: {md_path}", file=sys.stderr)
        return False

    browser = find_browser()
    if not browser:
        print("❌ 未找到 Chrome/Edge 浏览器", file=sys.stderr)
        return False

    # 默认头像
    if avatar_path is None:
        avatar_path = DEFAULT_AVATAR

    # 读取 Markdown
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    # Markdown → HTML
    html_body = markdown.markdown(md_content, extensions=["extra", "sane_lists"])

    # 处理头部：把 h1 和后面的联系方式 p 包裹到 resume-header 里
    avatar_html = build_header_html(avatar_path)

    # 找到第一个 <h1> 和它后面的第一个 <p>，包裹到 header 里
    h1_match = re.search(r'<h1>(.*?)</h1>', html_body, re.DOTALL)
    if h1_match:
        name = h1_match.group(1)
        # 找到 h1 后面的第一个 <p>（联系方式）
        after_h1 = html_body[h1_match.end():]
        p_match = re.search(r'<p>(.*?)</p>', after_h1, re.DOTALL)

        contact_html = ""
        if p_match:
            contact = p_match.group(1)
            contact_html = f'<p class="contact">{contact}</p>'
            # 移除原来的 h1 和第一个 p
            html_body = html_body[:h1_match.start()] + after_h1[p_match.end():]
        else:
            html_body = html_body[:h1_match.start()] + after_h1

        # 插入新的 header
        header_html = f'''<div class="resume-header">
    <div class="header-left">
        <h1>{name}</h1>
        {contact_html}
    </div>
    {avatar_html}
</div>
'''
        html_body = header_html + html_body

    # 包裹完整 HTML
    full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>{RESUME_CSS}</style>
</head>
<body>
{html_body}
</body>
</html>"""

    # 保存临时 HTML
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
        html_path = f.name
        f.write(full_html)

    try:
        # Chrome headless 打印 PDF
        os.makedirs(os.path.dirname(pdf_path) or ".", exist_ok=True)
        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            html_path,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=60)

        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            print(f"✅ PDF 已生成: {pdf_path}")
            print(f"   大小: {os.path.getsize(pdf_path) / 1024:.1f} KB")
            print(f"   浏览器: {os.path.basename(browser)}")
            if avatar_path and os.path.exists(avatar_path):
                print(f"   头像: {os.path.basename(avatar_path)}")
            return True
        else:
            # 尝试旧版 headless 模式
            cmd[1] = "--headless"
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                print(f"✅ PDF 已生成: {pdf_path}")
                print(f"   大小: {os.path.getsize(pdf_path) / 1024:.1f} KB")
                return True
            print(f"❌ PDF 生成失败: {result.stderr.decode('utf-8', errors='replace')[-500:]}", file=sys.stderr)
            return False
    finally:
        try:
            os.unlink(html_path)
        except:
            pass


def main():
    parser = argparse.ArgumentParser(description="Markdown 简历 → PDF（Chrome headless，带头像）")
    parser.add_argument("input", help="输入 Markdown 文件路径")
    parser.add_argument("--output", "-o", help="输出 PDF 路径（默认同目录同名）", default=None)
    parser.add_argument("--avatar", "-a", help="头像图片路径（默认使用 skill/assets/avatar.jpg）", default=None)
    parser.add_argument("--no-avatar", action="store_true", help="不包含头像")
    args = parser.parse_args()

    if args.output:
        pdf_path = args.output
    else:
        pdf_path = os.path.splitext(args.input)[0] + ".pdf"

    avatar_path = None if args.no_avatar else args.avatar
    success = md_to_pdf(args.input, pdf_path, avatar_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
