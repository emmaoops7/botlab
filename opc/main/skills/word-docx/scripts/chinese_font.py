#!/usr/bin/env python3
"""
Word 文档中文字体工具
用法：在创建 Word 文档时调用 set_run_font 设置中文字体
"""
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.oxml import OxmlElement


def set_run_font(run, font_name='宋体'):
    """
    设置 run 的中文字体（西文 + 东亚）
    
    Args:
        run: docx.text.run.Run 对象
        font_name: 字体名，如 '宋体'、'微软雅黑'、'仿宋'、'黑体'、'楷体'
    """
    run.font.name = font_name
    # 确保 rPr 元素存在
    rPr = run._element.rPr
    if rPr is None:
        rPr = OxmlElement('w:rPr')
        run._element.insert(0, rPr)
    rPr.rFonts.set(qn('w:eastAsia'), font_name)


def set_default_chinese_font(doc, font_name='宋体', size=14):
    """
    设置整个文档的默认中文字体
    
    Args:
        doc: Document 对象
        font_name: 默认中文字体
        size: 默认字号
    """
    style = doc.styles['Normal']
    style.font.name = font_name
    style.font.size = Pt(size)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
