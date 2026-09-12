# -*- coding: utf-8 -*-
"""
compress_pdf.py - 用 PyMuPDF 压缩 PDF（garbage+deflate+图片重采样）
用法: python compress_pdf.py <输入pdf> <输出pdf> [dpi=150]
"""
import pymupdf as fitz
import sys, os

def compress(input_path, output_path, target_dpi=150):
    doc = fitz.open(input_path)
    total_pages = doc.page_count
    print(f"📖 {os.path.basename(input_path)}: {total_pages}页, {os.path.getsize(input_path)/1024/1024:.1f}MB")

    # 第一遍：遍历页面，降低图片 DPI（如果有 Pillow）
    try:
        from PIL import Image
        import io
        has_pillow = True
        print("  🖼️  使用 Pillow 重采样图片到 {} DPI".format(target_dpi))
    except ImportError:
        has_pillow = False
        print("  ⚠️  无 Pillow，仅用 deflate 压缩")

    img_replaced = 0
    for page_num in range(total_pages):
        page = doc[page_num]
        if has_pillow:
            # 获取页面图片列表
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    w, h = base_image["width"], base_image["height"]
                    # 只压缩大图（>500px 边或 >100KB）
                    if max(w, h) > 800 or len(image_bytes) > 100000:
                        pil_img = Image.open(io.BytesIO(image_bytes))
                        # 计算新尺寸（按 target_dpi 缩放，假设原图 300dpi）
                        scale = target_dpi / 300.0
                        new_w = max(1, int(w * scale))
                        new_h = max(1, int(h * scale))
                        if new_w < w and new_h < h:
                            pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
                            buf = io.BytesIO()
                            pil_img.save(buf, format="JPEG", quality=75)
                            new_bytes = buf.getvalue()
                            # 替换图片
                            doc.update_stream(xref, new_bytes)
                            img_replaced += 1
                except Exception:
                    continue
        if (page_num + 1) % 50 == 0:
            print(f"  处理中... {page_num+1}/{total_pages}页", flush=True)

    if has_pillow:
        print(f"  ✅ 重采样了 {img_replaced} 张图片")

    # 第二遍：保存时开启所有压缩
    doc.save(output_path, garbage=4, deflate=True,
             deflate_images=True, deflate_fonts=True, clean=True)
    doc.close()

    orig = os.path.getsize(input_path) / 1024 / 1024
    new = os.path.getsize(output_path) / 1024 / 1024
    ratio = (1 - new / orig) * 100
    print(f"  ✅ 压缩完成: {orig:.1f}MB → {new:.1f}MB (节省 {ratio:.0f}%)")
    return new

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python compress_pdf.py <输入pdf> <输出pdf> [dpi]")
        sys.exit(1)
    inp = sys.argv[1]
    out = sys.argv[2]
    dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 150
    compress(inp, out, dpi)
