#!/usr/bin/env python3
"""渲染 PDF 指定页为 PNG（供 Windows 自带 OCR 使用）。

用法:
    python render_pdf.py <pdf_path> <out_dir> [--pages 0,20,40] [--dpi 200]

依赖: pymupdf  (用户系统 Python: C:\\Users\\Lenovo\\AppData\\Local\\Programs\\Python\\Python313\\python.exe)
"""
import sys
import os
import argparse
import pymupdf


def main() -> int:
    ap = argparse.ArgumentParser(description="渲染 PDF 页为 PNG")
    ap.add_argument("pdf", help="PDF 文件路径")
    ap.add_argument("out_dir", help="输出目录（自动创建）")
    ap.add_argument("--pages", default="0", help="逗号分隔页码，如 0,20,40（默认第 0 页）")
    ap.add_argument("--dpi", type=int, default=200, help="渲染 DPI（默认 200）")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    doc = pymupdf.open(args.pdf)
    print("总页数:", doc.page_count)

    pages = [int(x) for x in args.pages.split(",") if x.strip()]
    for pno in pages:
        if pno < 0 or pno >= doc.page_count:
            print(f"跳过越界页码 {pno}")
            continue
        page = doc[pno]
        pix = page.get_pixmap(dpi=args.dpi)
        f = os.path.join(args.out_dir, f"page{pno}.png")
        pix.save(f)
        print(f"page{pno}: {pix.width}x{pix.height} -> {f} ({os.path.getsize(f)//1024}KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
