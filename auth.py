import requests
import config


def get_access_token():
    params = {
        "grant_type": "client_credentials",
        "client_id": config.API_KEY,
        "client_secret": config.SECRET_KEY,
    }
    response = requests.post(config.TOKEN_URL, params=params)
    return response.json().get("access_token")


if __name__ == "__main__":
    print(get_access_token())
