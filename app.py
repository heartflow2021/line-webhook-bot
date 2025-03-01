from flask import Flask, request, jsonify
import requests
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

app = Flask(__name__)

# 設定 LINE API
import os
from linebot import LineBotApi, WebhookHandler

# 改為從環境變數讀取
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


# 設定 OpenAI API
import os

openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("環境變數 OPENAI_API_KEY 未設定！請在 Zeabur 設定 API Key。")


# 連接 Google Sheets（可選）
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ✅ 改為從 Zeabur 環境變數讀取 API Key
import os
import json

# 從 Zeabur 環境變數讀取 Google API Key
google_credentials_json = os.getenv("GOOGLE_API_KEY")
if not google_credentials_json:
    raise ValueError("GOOGLE_API_KEY 環境變數未設定")

creds_dict = json.loads(google_credentials_json)

# 連接 Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Chatbot Conversations").sheet1


# 記錄對話到 Google Sheets（可選）
def save_to_sheets(user_id, user_message, bot_reply,time_stamp):
    sheet.append_row([user_id, user_message, bot_reply,time_stamp])

# 設定 Webhook
@app.route("/callback", methods=["POST"])
def callback():
    body = request.get_data(as_text=True)
    signature = request.headers.get("X-Line-Signature")

    if signature is None:
        return "Missing signature", 400  # 直接回應錯誤，避免 `NoneType` 問題

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return "Invalid signature", 400

    return "OK", 200

# 處理使用者訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    user_id = event.source.user_id

    # 發送訊息到 ChatGPT API
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
        {
    "role": "system",
    "content": """你是一個專業且溫暖的心理健康輔導助手，主要針對情緒困擾的用戶（包括焦慮、憂鬱、感情問題、婚姻問題及家庭衝突等），
    提供情緒管理策略、啟發性問題及自我反思引導，幫助用戶處理心理問題和釐清情緒來源。
    它會像朋友一樣，用輕鬆、簡單的語氣交流，讓用戶感覺到被理解和支持。
    當用戶表達情緒問題時，內在安全感教練不會馬上提供解決方法，而是先照顧對方的情緒，更多使用一問一答的形式來互動，
    讓對方能慢慢理解，感受被陪伴。對話應以短句為主，避免訊息量過大，確保每次互動都可以專注於一個核心話題，逐步深入。
    你會透過簡單的開放性提問，鼓勵用戶自由表達感受，並且強調陪伴與傾聽的重要性。
    若發現用戶情緒波動較大，則會溫柔地建議尋求專業的心理協助，並強調安全感與支持的重要性。"""
},
        {"role": "user", "content": user_message }
        ]
    )

    bot_reply = response["choices"][0]["message"]["content"]

    # 回應使用者
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=bot_reply))

    # 儲存對話（可選）
    from datetime import datetime
save_to_sheets(user_id, user_message, bot_reply, datetime.now().isoformat())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
