#!/usr/bin/env python3
"""探测 PDF：总页数、文本层量、是否扫描版（需走 OCR）。

用法:
    python probe_pdf.py <pdf_path> [--sample N]

返回:
    打印总页数、抽查页文本量、全库平均字符数，并给出"扫描版/文本型"判定。
    判定规则：每页平均字符 < 20 → 扫描版，需走 render + ocr 管线。

依赖: pypdf  (用户系统 Python: C:\\Users\\Lenovo\\AppData\\Local\\Programs\\Python\\Python313\\python.exe)
"""
import sys
import argparse
import pypdf


def main() -> int:
    ap = argparse.ArgumentParser(description="探测 PDF 文本层")
    ap.add_argument("pdf", help="PDF 文件路径")
    ap.add_argument("--sample", type=int, default=3, help="抽查前 N 页文本量（默认 3）")
    args = ap.parse_args()

    reader = pypdf.PdfReader(args.pdf)
    n = len(reader.pages)
    print(f"总页数: {n}")

    for i in range(min(args.sample, n)):
        try:
            t = reader.pages[i].extract_text() or ""
            print(f"page{i}: {len(t)}字符 | 开头: {t[:80]!r}")
        except Exception as e:  # noqa: BLE001
            print(f"page{i}: 提取失败 {e}")

    total = 0
    for p in reader.pages:
        try:
            total += len(p.extract_text() or "")
        except Exception:  # noqa: BLE001
            pass
    avg = round(total / max(n, 1), 1)
    print(f"\n全部页文本总量: {total} 字符 | 每页平均: {avg}")

    if n and avg < 20:
        print("判定: 扫描版/图片型 PDF（文本层不足），需走 OCR 管线（render_pdf.py + ocr_windows.ps1）")
    else:
        print("判定: 文本型 PDF（可直接用 document-extract / 文件读取提取）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
