import re


def extract_info(words_result):
    text = "\n".join([w["words"] for w in words_result])
    print(f"--- OCR TEXT ---\n{text}\n----------------")

    data = {}
    date = re.search(r"(\d{4}[年/-]\d{1,2}[月/-]\d{1,2})", text)
    if date:
        data["date"] = date.group(1)

    amount = re.search(r"(\d+\.\d{2})", text)
    if amount:
        data["amount"] = amount.group(1)

    return data
