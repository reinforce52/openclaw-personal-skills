# -*- coding: utf-8 -*-
"""
split_pdf.py - 拆分超190页PDF为分卷（MinerU单文件限制200页）
用法: python split_pdf.py <pdf路径> [输出目录]
输出: 输出目录/<原名>_partN.pdf + manifest.json
"""
import fitz, os, sys, json

MAX_PAGES = 190

def main():
    if len(sys.argv) < 2:
        print("用法: python split_pdf.py <pdf路径> [输出目录]")
        sys.exit(1)
    pdf = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(pdf), "split")
    os.makedirs(out_dir, exist_ok=True)

    doc = fitz.open(pdf)
    total = doc.page_count
    base = os.path.splitext(os.path.basename(pdf))[0]
    print(f"📖 {base}: {total}页")

    manifest = []
    if total <= MAX_PAGES:
        manifest.append({"name": os.path.basename(pdf), "pages": total, "path": pdf})
        print("✅ 无需拆分")
    else:
        parts = (total + MAX_PAGES - 1) // MAX_PAGES
        for i in range(parts):
            start = i * MAX_PAGES
            end = min((i + 1) * MAX_PAGES, total)
            out_name = f"{base}_part{i+1}.pdf"
            out_path = os.path.join(out_dir, out_name)
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=start, to_page=end - 1)
            new_doc.save(out_path)
            new_doc.close()
            size_mb = round(os.path.getsize(out_path) / 1024 / 1024, 1)
            print(f"  ✂️   {out_name}: 第{start+1}-{end}页 ({end-start}页, {size_mb}MB)")
            manifest.append({"name": out_name, "pages": end - start, "path": out_path})
    doc.close()

    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"✅ 完成，清单: {os.path.join(out_dir, 'manifest.json')}")

if __name__ == "__main__":
    main()
