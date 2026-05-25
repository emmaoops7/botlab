#!/usr/bin/env python3
"""
OCR Text Recognition Script (with safety limits)
Usage: python3 ocr.py <file_path> [--output <output_file>] [--max-pages <n>]
Supported: .pdf, .jpg, .jpeg, .png

Safety limits:
  - PDF > 20 pages: refuse
  - File > 20MB: refuse
"""

import sys
import os
import argparse

# 环境变量：跳过模型连通性检查
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'

MAX_FILE_SIZE_MB = 20
MAX_PAGES = 20


def check_file_size(file_path):
    """检查文件大小"""
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        print(f"ERROR: 文件过大 ({size_mb:.1f}MB)，上限 {MAX_FILE_SIZE_MB}MB")
        print(f"请拆分文件后重新发送")
        sys.exit(1)
    return size_mb


def check_pdf_pages(pdf_path):
    """检查 PDF 页数"""
    import fitz
    doc = fitz.open(pdf_path)
    pages = len(doc)
    doc.close()
    if pages > MAX_PAGES:
        print(f"ERROR: PDF 页数过多 ({pages}页)，上限 {MAX_PAGES}页")
        print(f"请拆分文件后重新发送")
        sys.exit(1)
    return pages


def extract_images_from_pdf(pdf_path):
    """Extract images from PDF"""
    import fitz

    images = []
    doc = fitz.open(pdf_path)

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_images = page.get_images()

        for img_index, img in enumerate(page_images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]

            output_path = f"/tmp/pdf_page{page_num+1}_img{img_index}.{image_ext}"
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            images.append(output_path)

    doc.close()
    return images


def ocr_file(file_path, output_path=None):
    """Perform OCR recognition on file"""
    from paddleocr import PaddleOCR

    # 安全检查
    size_mb = check_file_size(file_path)
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.pdf':
        pages = check_pdf_pages(file_path)
        print(f"文件: {file_path} ({size_mb:.1f}MB, {pages}页)")
    else:
        print(f"文件: {file_path} ({size_mb:.1f}MB)")

    # Initialize OCR
    print("正在加载 PaddleOCR 模型...")
    ocr = PaddleOCR(lang='ch', use_angle_cls=True,
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False)

    if ext == '.pdf':
        # PDF: extract images first, then recognize
        images = extract_images_from_pdf(file_path)
        all_texts = []

        for img_path in images:
            print(f"识别中: {img_path}")
            result = ocr.predict(img_path)
            if result:
                texts = result[0].get('rec_texts', [])
                all_texts.extend(texts)

        # Clean up temporary images
        for img_path in images:
            try:
                os.remove(img_path)
            except:
                pass

        final_texts = all_texts
    else:
        # Image: recognize directly
        print(f"识别中: {file_path}")
        result = ocr.predict(file_path)

        if result and len(result) > 0:
            final_texts = result[0].get('rec_texts', [])
        else:
            final_texts = []

    # Output results
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            for text in final_texts:
                f.write(text + '\n')
        print(f"结果已保存到: {output_path}")
    else:
        print("\n=== OCR 识别结果 ===\n")
        for text in final_texts:
            print(text)

    print(f"\n共识别 {len(final_texts)} 行文字")
    return final_texts


def main():
    parser = argparse.ArgumentParser(description='OCR 文字识别工具')
    parser.add_argument('file', help='待识别文件（PDF 或图片）')
    parser.add_argument('--output', '-o', help='输出文件路径（可选）')

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"错误: 文件不存在: {args.file}")
        sys.exit(1)

    try:
        ocr_file(args.file, args.output)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
