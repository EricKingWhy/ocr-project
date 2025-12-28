import re

def extract_info(words_result):
    # 将列表拼接成字符串
    text = "\n".join([w['words'] for w in words_result])
    print(f"--- 识别原文 ---\n{text}\n----------------")
    
    data = {}
    # 提取日期 (例如 2023年10月1日)
    date = re.search(r'(\d{4}[年-]\d{1,2}[月-]\d{1,2})', text)
    if date: data['日期'] = date.group(1)
    
    # 提取金额 (例如 100.00)
    amount = re.search(r'(\d+\.\d{2})', text)
    if amount: data['金额'] = amount.group(1)
    
    return data