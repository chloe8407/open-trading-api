"""모의투자 토큰 발급 테스트 - 가장 작은 단위 확인용"""
import os
import requests

APPKEY = os.getenv("GH_APPKEY")
APPSECRET = os.getenv("GH_APPSECRET")
BASE_URL = "https://openapivts.koreainvestment.com:29443"  # 모의투자 URL

def get_token():
    url = f"{BASE_URL}/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": APPKEY,
        "appsecret": APPSECRET,
    }
    res = requests.post(url, headers=headers, json=body, timeout=10)
    print("상태 코드:", res.status_code)
    print("응답:", res.json())
    return res.json()

if __name__ == "__main__":
    print(f"APPKEY 길이: {len(APPKEY) if APPKEY else 'None'}")
    print(f"APPSECRET 길이: {len(APPSECRET) if APPSECRET else 'None'}")
    print("---")
    get_token()