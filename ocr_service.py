import base64
import requests
import config


def get_text_from_image(file_path, token):
    url = f"{config.OCR_URL}?access_token={token}"
    with open(file_path, "rb") as f:
        img_b64 = base64.b64encode(f.read())

    headers = {"content-type": "application/x-www-form-urlencoded"}
    response = requests.post(url, data={"image": img_b64}, headers=headers)
    return response.json().get("words_result", [])
