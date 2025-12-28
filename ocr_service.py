import requests
import base64
import config

def get_text_from_image(file_path, token):
    url = f"{config.OCR_URL}?access_token={token}"
    
    # 二进制读取图片并进行base64编码
    with open(file_path, 'rb') as f:
        img_data = f.read()
        img_b64 = base64.b64encode(img_data)
        
    # 发送请求
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    response = requests.post(url, data={"image": img_b64}, headers=headers)
    
    # 返回文字结果列表
    return response.json().get("words_result", [])