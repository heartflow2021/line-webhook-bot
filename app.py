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
LINE_CHANNEL_ACCESS_TOKEN = "你的_LINE_ACCESS_TOKEN"
LINE_CHANNEL_SECRET = "你的_LINE_SECRET"
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 設定 OpenAI API
openai.api_key = "你的_OPENAI_API_KEY"

# 連接 Google Sheets（可選）
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("你的_Google_API_憑證.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Chatbot Conversations").sheet1

# 記錄對話到 Google Sheets（可選）
def save_to_sheets(user_id, user_message, bot_reply):
    sheet.append_row([user_id, user_message, bot_reply])

# 設定 Webhook
@app.route("/callback", methods=["POST"])
def callback():
    body = request.get_data(as_text=True)
    signature = request.headers.get("X-Line-Signature")

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
