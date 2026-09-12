# -*- coding: utf-8 -*-
"""
resplit_textbook.py - 按"## 第X章"重新拆分教材原文大文件
用法: python resplit_textbook.py <大md文件> <输出目录> <书名>
"""
import re, os, sys

def main():
    if len(sys.argv) < 4:
        print("用法: python resplit_textbook.py <大md文件> <输出目录> <书名>")
        sys.exit(1)
    input_file = sys.argv[1]
    out_dir = sys.argv[2]
    book_name = sys.argv[3]

    with open(input_file, "r", encoding="utf-8") as f:
        text = f.read()

    # 找所有"## 第X章"标题
    pattern = re.compile(r'^## (第[一二三四五六七八九十]+章[^\n]*)$', re.MULTILINE)
    matches = list(pattern.finditer(text))

    if not matches:
        print("❌ 未找到章节标题")
        sys.exit(1)

    print(f"📖 {book_name}: 找到 {len(matches)} 章", flush=True)
    os.makedirs(out_dir, exist_ok=True)

    chapters = []
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        # 清理文件名
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)[:60]
        start = m.start()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        content = text[start:end].strip()

        fname = f"{i+1:02d}_{safe_title}.md"
        fpath = os.path.join(out_dir, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(f"---\nbook: \"{book_name}\"\nchapter: \"{title}\"\nsource: MinerU PDF提取\n---\n\n")
            f.write(content)

        chapters.append((title, fname, len(content)))
        print(f"  {i+1}. {title} ({len(content)}字符)", flush=True)

    # 生成目录
    index_path = os.path.join(out_dir, "_目录.md")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(f"# {book_name} - 教材原文目录\n\n")
        f.write(f"> MinerU 结构化提取，共 {len(chapters)} 章\n\n")
        for title, fname, _ in chapters:
            f.write(f"{chapters.index((title,fname,_))+1}. [[{fname[:-3]}|{title}]]\n")
    print(f"\n✅ 拆分完成: {out_dir}", flush=True)

if __name__ == "__main__":
    main()
