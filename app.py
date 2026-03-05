# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
import hmac
import hashlib
import time
import requests

app = Flask(__name__)

# ==========================================
# 邏輯註解：中繼站核心配置
# ==========================================
# 1. Bybit 全球主線入口，API 請求將從此處發出。
# 2. 由於部署在亞洲，將可避開 403 區域封鎖。
# ==========================================
BYBIT_HOST = "https://api.bybit.com"

@app.route('/proxy', methods=['POST'])
def proxy():
    """
    接收 Google Apps Script 傳來的請求並轉發給 Bybit
    """
    try:
        # 1. 解析 Google 傳過來的 JSON 資料
        data = request.json
        api_key = data.get('api_key')
        api_secret = data.get('api_secret')
        endpoint = data.get('endpoint')  # 例如: /v5/account/wallet-balance
        params = data.get('params')      # 例如: accountType=UNIFIED&coin=USDT

        # 2. 生成 Bybit V5 規格的時間戳與簽名
        # 使用中繼站本地時間，確保不會與 Bybit 伺服器時間落差過大
        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"
        
        # 簽名公式：timestamp + api_key + recv_window + params
        raw_str = timestamp + api_key + recv_window + params
        signature = hmac.new(
            bytes(api_secret, "utf-8"), 
            bytes(raw_str, "utf-8"), 
            hashlib.sha256
        ).hexdigest()

        # 3. 封裝 Headers (這身分現在是亞洲 IP 了！)
        headers = {
            "X-BAPI-API-KEY": api_key,
            "X-BAPI-SIGN": signature,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": recv_window,
            "Content-Type": "application/json"
        }

        # 4. 正式向 Bybit 發起請求
        url = f"{BYBIT_HOST}{endpoint}?{params}"
        response = requests.get(url, headers=headers, timeout=10)
        
        # 5. 將 Bybit 回傳的原封不動傳回給 Google Apps Script
        return jsonify(response.json())

    except Exception as e:
        # 萬一程式出錯，回傳錯誤訊息給試算表方便偵錯
        return jsonify({"retCode": -1, "retMsg": str(e)}), 500

# 啟動伺服器 (Zeabur 等平台會自動偵測 8080 端口)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)