import requests

API_KEY = "sk-204ed5e8f7c949b2abeea78c88323ac8"

url = "https://api.deepseek.com/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

data = {
    "model": "deepseek-chat",
    "messages": [
        {"role": "user", "content": "test"}
    ],
    "max_tokens": 1
}

try:
    response = requests.post(url, headers=headers, json=data, timeout=10)

    if response.status_code == 200:
        print("✅ API Key 有效（可正常调用模型）")
    elif response.status_code == 401:
        print("❌ API Key 无效或被拒绝")
    else:
        print(f"⚠️ 异常状态码: {response.status_code}")
        print(response.text)

except Exception as e:
    print("❌ 请求失败:", str(e))