import requests
import config

def get_access_token():
    # 拼装请求参数
    params = {
        "grant_type": "client_credentials",
        "client_id": config.API_KEY,
        "client_secret": config.SECRET_KEY
    }
    # 发送请求
    response = requests.post(config.TOKEN_URL, params=params)
    # 返回 Access Token
    return response.json().get("access_token")

if __name__ == "__main__":
    print(get_access_token())