---
name: ocr
description: Optical Character Recognition (OCR) tool, supports Chinese and English text extraction from PDFs and images. Use cases: (1) extract text from scanned PDFs, (2) recognize text from images, (3) extract text content from invoices, contracts, and other documents
---

# OCR Text Recognition

This skill uses PaddleOCR for text recognition, supporting both Chinese and English.

## ⚠️ IMPORTANT: File Size & Page Limits

Before processing, ALWAYS check file size and page count:

| 文件大小 | 页数 | 处理方式 |
|---------|------|---------|
| < 5MB | ≤ 5页 | 直接处理 |
| 5-20MB | 5-20页 | 告知用户"需要几分钟，后台处理"，用 subagent 异步执行 |
| > 20MB | > 20页 | **拒绝处理**，告诉用户拆分后重新发送 |

**绝对不要**在主会话中直接处理大文件，会导致卡死。

## 环境变量

首次使用必须设置（跳过模型连通性检查）：
```bash
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
```

## Quick Start

### 基本用法

```bash
python3 /root/clawd/skills/ocr-python/scripts/ocr.py <文件路径> [--output <输出文件>]
```

支持格式：`.pdf`, `.jpg`, `.jpeg`, `.png`

### PDF 页数检查

```bash
python3 -c "import fitz; print(len(fitz.open('file.pdf')))"
```

### 文件大小检查

```bash
ls -lh <文件路径>
```

## Output Format

Recognition results return text line by line. Use `--output` to save to file.

## Typical Use Cases

1. **图片 OCR**：直接识别图片中的文字
2. **PDF 扫描件**：提取 PDF 内图片 → OCR → 输出文字
3. **发票/合同**：识别后可转为 Word 文档

## Dependency Installation

依赖已安装在系统中：
- paddlepaddle 3.0.0（⚠️ 不要升级到 3.3.x，有 PIR bug）
- paddleocr 3.4.0
- PyMuPDF（PDF 支持）
- python-docx（Word 输出）

## Scripts

- `scripts/ocr.py` — 主 OCR 脚本
