# scripts/test_auth.py
import requests
import json

# 確保你的 Flask 伺服器有在執行 (python run.py)
BASE_URL = 'http://127.0.0.1:5000/api/auth'

def test_register():
    print("--- 測試註冊 ---")
    payload = {
        "username": "test_manager_01",
        "email": "manager01@example.com",
        "password": "securepassword123",
        "team_name": "台北富邦勇士"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/register", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"連線失敗，請確認伺服器是否已啟動: {e}")

def test_login():
    print("\n--- 測試登入 ---")
    payload = {
        "username": "test_manager_01",
        "password": "securepassword123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/login", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"連線失敗: {e}")

if __name__ == "__main__":
    # 注意：要執行這個測試，你需要先在另一個終端機執行 `flask run` 或 `python run.py`
    test_register()
    test_login()