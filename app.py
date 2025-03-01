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
LINE_CHANNEL_ACCESS_TOKEN = "7oFRJSVbyKYnP3i2AxSrKUTgBmrdxEIr5pvEfPwueSlhevuCZmsSb3x3JeaXQmqxcq7NQ47oynEy/NmM6VTkcKim6aX3vqJtNcFye4MFR93SUV2lM+gPF6QllzyQ4QJcVqVfvS7T8r5oJny0KNdjWQdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "5aa6642a8ee7d823099df583015eeeef"
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
def save_to_sheets(user_id, user_message, bot_reply,Timestamp):
    sheet.append_row([user_id, user_message, bot_reply,Timestamp])

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
        messages=[{"role": "user", "content": user_message}]
    )

    bot_reply = response["choices"][0]["message"]["content"]

    # 回應使用者
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=bot_reply))

    # 儲存對話（可選）
    save_to_sheets(user_id, user_message, bot_reply)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
