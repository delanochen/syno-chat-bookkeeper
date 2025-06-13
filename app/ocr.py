import pytesseract
from PIL import Image
import re

# 支持中英文
TESS_LANG = 'eng+chi_sim'

def parse_receipt(image_path):
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image, lang=TESS_LANG)
    # 简单正则提取日期、商家、金额等（可根据实际小票格式优化）
    date = re.search(r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})', text)
    amount = re.search(r'(Total|合计)[^\d]*(\d+[.]\d{2})', text, re.IGNORECASE)
    # 商家名称假设为首行
    lines = text.splitlines()
    merchant = lines[0] if lines else ''
    # 明细行简单提取
    details = '\n'.join(lines[1:]) if len(lines) > 1 else ''
    return {
        'date': date.group(1) if date else '',
        'merchant': merchant,
        'amount': amount.group(2) if amount else '',
        'details': details,
        'raw_text': text
    } 